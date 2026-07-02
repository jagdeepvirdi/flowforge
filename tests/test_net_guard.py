"""Unit tests for flowforge.net_guard — SSRF protection for editor-configured URLs.

Uses literal IP addresses wherever possible so these tests never perform a real
DNS lookup. Hostname-based resolution is exercised with socket.getaddrinfo mocked.
"""
from unittest.mock import patch

import pytest

from flowforge.net_guard import UnsafeUrlError, assert_public_url


class TestSchemeValidation:
    def test_rejects_non_http_scheme(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('ftp://8.8.8.8/x')

    def test_rejects_file_scheme(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('file:///etc/passwd')

    def test_rejects_missing_hostname(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('https://')


class TestLiteralIpBlocking:
    def test_blocks_loopback(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('http://127.0.0.1/')

    def test_blocks_cloud_metadata_ip(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('http://169.254.169.254/latest/meta-data')

    def test_blocks_rfc1918_10(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('http://10.1.2.3/webhook')

    def test_blocks_rfc1918_172(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('http://172.16.0.5/webhook')

    def test_blocks_rfc1918_192(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('http://192.168.1.1/webhook')

    def test_blocks_ipv6_loopback(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('http://[::1]/')

    def test_blocks_unspecified(self):
        with pytest.raises(UnsafeUrlError):
            assert_public_url('http://0.0.0.0/')

    def test_allows_public_ip(self):
        assert_public_url('http://8.8.8.8/webhook')  # should not raise


class TestHostnameResolution:
    def test_blocks_hostname_resolving_to_private_ip(self):
        with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('10.0.0.1', 0))]):
            with pytest.raises(UnsafeUrlError):
                assert_public_url('http://internal.example.com/webhook')

    def test_allows_hostname_resolving_to_public_ip(self):
        with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('8.8.8.8', 0))]):
            assert_public_url('http://hooks.example.com/webhook')  # should not raise

    def test_raises_on_dns_failure(self):
        import socket
        with patch('socket.getaddrinfo', side_effect=socket.gaierror('no such host')):
            with pytest.raises(UnsafeUrlError):
                assert_public_url('http://does-not-resolve.invalid/webhook')
