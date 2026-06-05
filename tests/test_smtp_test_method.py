"""Unit tests for SMTPProvider.test() — smtplib is mocked so no real server needed.

Covers the previously-uncovered test() method (lines 79-93 of smtp.py):
  - SSL path (SMTP_SSL)
  - plain SMTP + STARTTLS path
  - plain SMTP without TLS
  - no-username (skip login)
  - exception path
"""
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from flowforge.email_providers.smtp import SMTPProvider


def _provider(use_ssl=False, use_tls=True, username='user@example.com', password='secret'):
    return SMTPProvider(
        host='smtp.example.com',
        port=587,
        username=username,
        password=password,
        use_ssl=use_ssl,
        use_tls=use_tls,
    )


class TestSMTPProviderTest:

    def test_ssl_path_returns_true(self):
        mock_server = MagicMock()
        with patch('smtplib.SMTP_SSL', return_value=mock_server):
            ok, msg = _provider(use_ssl=True).test()
        assert ok is True
        assert 'smtp.example.com' in msg
        mock_server.login.assert_called_once()
        mock_server.quit.assert_called_once()

    def test_starttls_path_returns_true(self):
        mock_server = MagicMock()
        with patch('smtplib.SMTP', return_value=mock_server):
            ok, msg = _provider(use_ssl=False, use_tls=True).test()
        assert ok is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()

    def test_plain_smtp_no_tls_returns_true(self):
        mock_server = MagicMock()
        with patch('smtplib.SMTP', return_value=mock_server):
            ok, msg = _provider(use_ssl=False, use_tls=False).test()
        assert ok is True
        mock_server.starttls.assert_not_called()
        mock_server.login.assert_called_once()

    def test_no_username_skips_login(self):
        mock_server = MagicMock()
        with patch('smtplib.SMTP', return_value=mock_server):
            ok, msg = _provider(username='').test()
        assert ok is True
        mock_server.login.assert_not_called()
        mock_server.quit.assert_called_once()

    def test_exception_returns_false(self):
        with patch('smtplib.SMTP', side_effect=ConnectionRefusedError('refused')):
            ok, msg = _provider().test()
        assert ok is False
        assert 'refused' in msg

    def test_ssl_login_failure_returns_false(self):
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Auth failed')
        with patch('smtplib.SMTP_SSL', return_value=mock_server):
            ok, msg = _provider(use_ssl=True).test()
        assert ok is False

    def test_send_ssl_path_uses_smtp_ssl(self, tmp_path):
        mock_server = MagicMock()
        with patch('smtplib.SMTP_SSL', return_value=mock_server):
            result = _provider(use_ssl=True).send(
                ['a@b.com'], [], [], 'Subject', '<p>body</p>', []
            )
        assert result.success is True
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

    def test_send_starttls_path(self, tmp_path):
        mock_server = MagicMock()
        with patch('smtplib.SMTP', return_value=mock_server):
            result = _provider(use_ssl=False, use_tls=True).send(
                ['a@b.com'], ['cc@b.com'], [], 'Subject', '<p>body</p>', []
            )
        assert result.success is True
        mock_server.starttls.assert_called_once()

    def test_send_exception_returns_error_result(self):
        with patch('smtplib.SMTP', side_effect=OSError('network error')):
            result = _provider().send(['a@b.com'], [], [], 'S', 'b', [])
        assert result.success is False
        assert 'network error' in result.error
