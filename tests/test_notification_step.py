"""Unit tests for NotificationStep — all HTTP calls are mocked via urllib.request.urlopen."""
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from flowforge.steps.notification import NotificationStep


def _step(config):
    return NotificationStep(name='notify', config=config)


def _mock_urlopen_ok():
    """Context-manager mock that simulates a successful HTTP response."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=MagicMock())
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ── Slack ──────────────────────────────────────────────────────────────────────

class TestSlackNotification:

    def test_send_success(self):
        step = _step({'platform': 'slack', 'message': 'Hello', 'webhook_url': 'https://hooks.slack.com/T/X'})
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({})
        assert result.success is True
        assert 'Slack' in result.logs

    def test_missing_webhook_url(self):
        step = _step({'platform': 'slack', 'message': 'Hello'})
        result = step.run({})
        assert result.success is False
        assert 'webhook_url' in result.error

    def test_empty_webhook_url(self):
        step = _step({'platform': 'slack', 'message': 'Hello', 'webhook_url': '   '})
        result = step.run({})
        assert result.success is False
        assert 'webhook_url' in result.error

    def test_http_error(self):
        step = _step({'platform': 'slack', 'message': 'Hello', 'webhook_url': 'https://hooks.slack.com/T/X'})
        err = urllib.error.HTTPError(url='', code=400, msg='Bad', hdrs=None, fp=BytesIO(b'invalid_token'))
        with patch('urllib.request.urlopen', side_effect=err):
            result = step.run({})
        assert result.success is False
        assert '400' in result.error

    def test_message_truncated_in_logs(self):
        long_msg = 'A' * 200
        step = _step({'platform': 'slack', 'message': long_msg, 'webhook_url': 'https://hooks.slack.com/T/X'})
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({})
        assert result.success is True


# ── Teams ──────────────────────────────────────────────────────────────────────

class TestTeamsNotification:

    def test_send_success_no_title(self):
        step = _step({'platform': 'teams', 'message': 'Ping', 'webhook_url': 'https://example.webhook.office.com/X'})
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({})
        assert result.success is True
        assert 'Teams' in result.logs

    def test_send_success_with_title(self):
        step = _step({
            'platform': 'teams',
            'message':  'Pipeline finished',
            'title':    'Alert',
            'webhook_url': 'https://example.webhook.office.com/X',
        })
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({})
        assert result.success is True

    def test_missing_webhook_url(self):
        step = _step({'platform': 'teams', 'message': 'Hello'})
        result = step.run({})
        assert result.success is False
        assert 'webhook_url' in result.error

    def test_http_error(self):
        step = _step({'platform': 'teams', 'message': 'Ping', 'webhook_url': 'https://example.webhook.office.com/X'})
        err = urllib.error.HTTPError(url='', code=500, msg='Err', hdrs=None, fp=BytesIO(b'server error'))
        with patch('urllib.request.urlopen', side_effect=err):
            result = step.run({})
        assert result.success is False
        assert '500' in result.error


# ── Telegram ───────────────────────────────────────────────────────────────────

class TestTelegramNotification:

    def test_missing_bot_token(self):
        step = _step({'platform': 'telegram', 'message': 'Hello', 'chat_id': '12345'})
        result = step.run({})
        assert result.success is False
        assert 'bot_token' in result.error

    def test_missing_chat_id(self):
        step = _step({'platform': 'telegram', 'message': 'Hello', 'bot_token': 'tok123'})
        result = step.run({})
        assert result.success is False
        assert 'chat_id' in result.error

    def test_send_success_html_no_title(self):
        step = _step({
            'platform':   'telegram',
            'message':    'Hello',
            'bot_token':  'tok123',
            'chat_id':    '999',
            'parse_mode': 'HTML',
        })
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({})
        assert result.success is True
        assert '999' in result.logs

    def test_send_success_html_with_title(self):
        step = _step({
            'platform':   'telegram',
            'message':    'Body text',
            'title':      'Pipeline Alert',
            'bot_token':  'tok123',
            'chat_id':    '999',
            'parse_mode': 'HTML',
        })
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({})
        assert result.success is True

    def test_send_success_markdown_with_title(self):
        step = _step({
            'platform':   'telegram',
            'message':    'Body',
            'title':      'Update',
            'bot_token':  'tok123',
            'chat_id':    '999',
            'parse_mode': 'Markdown',
        })
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({})
        assert result.success is True

    def test_send_success_no_title_default_parse_mode(self):
        step = _step({
            'platform':  'telegram',
            'message':   'Hello',
            'bot_token': 'tok123',
            'chat_id':   '42',
        })
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({})
        assert result.success is True

    def test_http_error(self):
        step = _step({'platform': 'telegram', 'message': 'Hello', 'bot_token': 'tok123', 'chat_id': '999'})
        err = urllib.error.HTTPError(url='', code=401, msg='Unauthorized', hdrs=None, fp=BytesIO(b'unauthorized'))
        with patch('urllib.request.urlopen', side_effect=err):
            result = step.run({})
        assert result.success is False
        assert '401' in result.error


# ── Edge cases ─────────────────────────────────────────────────────────────────

class TestNotificationEdgeCases:

    def test_unknown_platform_returns_error(self):
        step = _step({'platform': 'discord', 'message': 'Hello'})
        result = step.run({})
        assert result.success is False
        assert 'discord' in result.error

    def test_message_rendered_from_context(self):
        step = _step({
            'platform':    'slack',
            'message':     'Hello {{ name }}',
            'webhook_url': 'https://hooks.slack.com/T/X',
        })
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({'name': 'World'})
        assert result.success is True

    def test_title_rendered_from_context(self):
        step = _step({
            'platform':    'teams',
            'message':     'Done',
            'title':       '{{ pipeline_name }} finished',
            'webhook_url': 'https://example.webhook.office.com/X',
        })
        with patch('urllib.request.urlopen', return_value=_mock_urlopen_ok()):
            result = step.run({'pipeline_name': 'Monthly Report'})
        assert result.success is True

    def test_generic_exception_wrapped_in_step_result(self):
        step = _step({'platform': 'slack', 'message': 'Hello', 'webhook_url': 'https://hooks.slack.com/T/X'})
        with patch('urllib.request.urlopen', side_effect=Exception('connection refused')):
            result = step.run({})
        assert result.success is False
        assert 'connection refused' in result.error
