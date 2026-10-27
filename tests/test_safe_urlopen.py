"""SSRF hardening for editor-configurable outbound URLs (failure webhook, notification step).

Covers net_guard.safe_urlopen (no redirects, connection pinned to the validated IP),
net_guard.check_url_syntax (DNS-free save-time check), the failure-webhook sender, and the
pipeline API rejecting unsafe on_failure_webhook_url values at save time.

safe_urlopen is exercised against a real local HTTP server. The server is on loopback, which
the guard rightly refuses, so resolve_public_ips is patched to return 127.0.0.1 as if it were a
validated public address — everything else (redirect refusal, IP pinning) is the real code.
"""
import logging
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

import pytest

from flowforge.api.validators import validate_pipeline, validate_webhook_url
from flowforge.net_guard import (
    UnsafeUrlError,
    check_url_syntax,
    resolve_public_ips,
    safe_urlopen,
)


@pytest.fixture
def server():
    seen: list[tuple[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def _record(self):
            seen.append((self.path, self.headers.get('Host', '')))

        def do_POST(self):
            self._record()
            length = int(self.headers.get('Content-Length') or 0)
            self.rfile.read(length)
            if self.path == '/redirect':
                self.send_response(302)
                self.send_header('Location', 'http://169.254.169.254/latest/meta-data/')
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')

        do_GET = do_POST

        def log_message(self, *args):  # silence test output
            pass

    httpd = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1], seen
    finally:
        httpd.shutdown()
        httpd.server_close()


def _post(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, data=b'{}', headers={'Content-Type': 'application/json'}, method='POST')


# ── safe_urlopen ─────────────────────────────────────────────────────────────

class TestSafeUrlopen:
    def test_refuses_private_literal_without_connecting(self):
        with patch('socket.create_connection', side_effect=AssertionError('must not connect')):
            with pytest.raises(UnsafeUrlError):
                safe_urlopen(_post('http://169.254.169.254/latest/meta-data/'))

    def test_refuses_non_http_scheme(self):
        with pytest.raises(UnsafeUrlError):
            safe_urlopen('file:///etc/passwd')

    def test_hostname_resolving_to_private_ip_refused(self):
        with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('10.0.0.5', 0))]):
            with pytest.raises(UnsafeUrlError):
                safe_urlopen(_post('http://internal.example.com/hook'))

    def test_success_returns_body(self, server):
        port, _ = server
        with patch('flowforge.net_guard.resolve_public_ips', return_value=['127.0.0.1']):
            with safe_urlopen(_post(f'http://localhost:{port}/ok'), timeout=5) as resp:
                assert resp.read() == b'ok'

    def test_redirect_is_not_followed(self, server):
        """A public URL must not be able to bounce the request to an internal address."""
        port, seen = server
        with patch('flowforge.net_guard.resolve_public_ips', return_value=['127.0.0.1']):
            with pytest.raises(urllib.error.HTTPError) as exc:
                safe_urlopen(_post(f'http://localhost:{port}/redirect'), timeout=5)
        assert exc.value.code == 302
        assert [p for p, _ in seen] == ['/redirect'], 'redirect target must never be requested'

    def test_connection_is_pinned_to_validated_ip(self, server):
        """The hostname does not resolve at all; success proves we connected to the pinned IP
        (a DNS-rebinding answer arriving after validation therefore cannot redirect us)."""
        port, seen = server
        host = 'rebind.invalid'
        with patch('flowforge.net_guard.resolve_public_ips', return_value=['127.0.0.1']):
            with safe_urlopen(_post(f'http://{host}:{port}/ok'), timeout=5) as resp:
                assert resp.read() == b'ok'
        assert seen == [('/ok', f'{host}:{port}')]  # Host header keeps the original name

    def test_redirects_still_refused_in_proxy_mode(self, server):
        port, seen = server
        with patch('flowforge.net_guard.resolve_public_ips', return_value=['127.0.0.1']), \
                patch('flowforge.net_guard._uses_proxy', return_value=True):
            with pytest.raises(urllib.error.HTTPError) as exc:
                safe_urlopen(_post(f'http://localhost:{port}/redirect'), timeout=5)
        assert exc.value.code == 302
        assert [p for p, _ in seen] == ['/redirect']

    def test_resolve_public_ips_returns_addresses(self):
        with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('8.8.8.8', 0))]):
            assert resolve_public_ips('https://example.com/x') == ['8.8.8.8']

    def test_resolve_public_ips_rejects_if_any_address_private(self):
        infos = [(2, 1, 6, '', ('8.8.8.8', 0)), (2, 1, 6, '', ('192.168.1.5', 0))]
        with patch('socket.getaddrinfo', return_value=infos):
            with pytest.raises(UnsafeUrlError):
                resolve_public_ips('https://mixed.example.com/x')


# ── check_url_syntax (save-time) ─────────────────────────────────────────────

class TestCheckUrlSyntax:
    @pytest.mark.parametrize('url', [
        'https://hooks.slack.com/services/T/B/X',
        'http://example.com/hook',
        'https://8.8.8.8/hook',
    ])
    def test_accepts(self, url):
        check_url_syntax(url)

    @pytest.mark.parametrize('url', [
        'file:///etc/passwd',
        'ftp://example.com/x',
        'gopher://example.com/',
        'http://',
        'not a url',
        'http://169.254.169.254/latest/meta-data/',
        'http://10.0.0.5/hook',
        'http://127.0.0.1:8080/',
        'http://[::1]/',
    ])
    def test_rejects(self, url):
        with pytest.raises(UnsafeUrlError):
            check_url_syntax(url)

    def test_does_not_resolve_hostnames(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError('no DNS at save time')):
            check_url_syntax('http://internal.corp.example/hook')


# ── failure webhook sender ───────────────────────────────────────────────────

class TestFailureWebhook:
    def test_internal_literal_is_blocked_and_logged(self, caplog):
        from flowforge.engine.notifications import _fire_failure_webhook
        with patch('socket.create_connection', side_effect=AssertionError('must not connect')), \
                caplog.at_level(logging.WARNING):
            _fire_failure_webhook('http://169.254.169.254/latest/meta-data/', {'x': 1})  # must not raise
        assert 'blocked by SSRF guard' in caplog.text

    def test_hostname_resolving_internal_is_blocked(self, caplog):
        from flowforge.engine.notifications import _fire_failure_webhook
        with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('10.1.2.3', 0))]), \
                patch('socket.create_connection', side_effect=AssertionError('must not connect')), \
                caplog.at_level(logging.WARNING):
            _fire_failure_webhook('https://hooks.internal.example/abc', {})
        assert 'blocked by SSRF guard' in caplog.text

    def test_secret_path_is_not_logged(self, caplog):
        from flowforge.engine.notifications import _fire_failure_webhook
        with patch('flowforge.net_guard.safe_urlopen', side_effect=Exception('boom')), \
                caplog.at_level(logging.WARNING):
            _fire_failure_webhook('https://hooks.example.com/services/SECRET-TOKEN', {})
        assert 'SECRET-TOKEN' not in caplog.text
        assert 'hooks.example.com' in caplog.text


# ── validators + API ─────────────────────────────────────────────────────────

class TestValidators:
    def test_none_and_empty_ok(self):
        assert validate_webhook_url(None) is None
        assert validate_webhook_url('') is None

    def test_unsafe_url_message_names_field(self):
        err = validate_webhook_url('http://169.254.169.254/x')
        assert err and 'on_failure_webhook_url' in err

    def test_validate_pipeline_includes_webhook_check(self):
        assert validate_pipeline({'name': 'p', 'on_failure_webhook_url': 'file:///etc/passwd'})
        assert validate_pipeline({'name': 'p', 'on_failure_webhook_url': 'https://hooks.slack.com/x'}) is None


class TestPipelineApiRejectsUnsafeWebhook:
    BAD = 'http://169.254.169.254/latest/meta-data/'

    def test_create_rejected(self, client, headers):
        resp = client.post('/api/pipelines', json={'name': 'ssrf-create', 'on_failure_webhook_url': self.BAD},
                           headers=headers)
        assert resp.status_code == 400
        assert 'on_failure_webhook_url' in resp.get_json()['error']

    def test_update_rejected(self, client, headers):
        created = client.post('/api/pipelines', json={'name': 'ssrf-update'}, headers=headers)
        assert created.status_code == 201
        pid = created.get_json()['id']
        try:
            resp = client.put(f'/api/pipelines/{pid}', json={'on_failure_webhook_url': 'file:///etc/passwd'},
                              headers=headers)
            assert resp.status_code == 400
        finally:
            client.delete(f'/api/pipelines/{pid}', headers=headers)

    def test_yaml_import_rejected(self, client, headers):
        yaml_content = f"name: ssrf-import\non_failure_webhook_url: {self.BAD}\n"
        resp = client.post('/api/pipelines/import', json={'yaml_content': yaml_content}, headers=headers)
        assert resp.status_code == 400

    def test_valid_public_url_accepted(self, client, headers):
        resp = client.post('/api/pipelines',
                           json={'name': 'ssrf-ok', 'on_failure_webhook_url': 'https://hooks.slack.com/services/T/B/X'},
                           headers=headers)
        assert resp.status_code == 201
        client.delete(f"/api/pipelines/{resp.get_json()['id']}", headers=headers)
