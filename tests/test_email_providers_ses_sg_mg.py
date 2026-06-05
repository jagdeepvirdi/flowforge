"""Unit tests for SendGridProvider, SESProvider, and MailgunProvider.

All external I/O (requests, boto3) is mocked — no cloud credentials required.
Also tests the factory._build_provider paths for these three provider types.
"""
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


# ── SendGrid ───────────────────────────────────────────────────────────────────

class TestSendGridProvider:

    def _provider(self):
        from flowforge.email_providers.sendgrid import SendGridProvider
        return SendGridProvider(api_key='SG.testkey', from_email='bot@example.com', from_name='Bot')

    def _mock_requests(self, status_code=202, text='', json_data=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.text = text
        mock_resp.json.return_value = json_data or {}
        m = ModuleType('requests')
        m.post = MagicMock(return_value=mock_resp)
        m.get  = MagicMock(return_value=mock_resp)
        return m

    def test_send_success_202(self):
        mock_req = self._mock_requests(202)
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], [], [], 'Subj', '<p>hi</p>', [])
        assert result.success is True
        assert result.recipients == ['a@b.com']

    def test_send_success_200(self):
        mock_req = self._mock_requests(200)
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], [], [], 'Subj', 'body', [])
        assert result.success is True

    def test_send_with_cc_and_bcc(self):
        mock_req = self._mock_requests(202)
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], ['cc@b.com'], ['bcc@b.com'], 'S', 'b', [])
        assert result.success is True
        assert len(result.recipients) == 3

    def test_send_with_attachment(self, tmp_path):
        att = tmp_path / 'report.pdf'
        att.write_bytes(b'%PDF data')
        mock_req = self._mock_requests(202)
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], [], [], 'S', 'b', [att])
        assert result.success is True
        payload = mock_req.post.call_args.kwargs['json']
        assert 'attachments' in payload

    def test_send_failure_non_2xx(self):
        mock_req = self._mock_requests(400, 'Bad request')
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], [], [], 'S', 'b', [])
        assert result.success is False
        assert '400' in result.error

    def test_send_requests_not_installed(self):
        with patch.dict(sys.modules, {'requests': None}):
            result = self._provider().send(['a@b.com'], [], [], 'S', 'b', [])
        assert result.success is False
        assert 'requests' in result.error

    def test_test_method_success(self):
        mock_req = self._mock_requests(200, json_data={'username': 'myaccount'})
        with patch.dict(sys.modules, {'requests': mock_req}):
            ok, msg = self._provider().test()
        assert ok is True
        assert 'myaccount' in msg

    def test_test_method_failure_non_200(self):
        mock_req = self._mock_requests(401, 'Unauthorized')
        with patch.dict(sys.modules, {'requests': mock_req}):
            ok, msg = self._provider().test()
        assert ok is False
        assert '401' in msg

    def test_test_method_exception(self):
        m = ModuleType('requests')
        m.get = MagicMock(side_effect=Exception('network timeout'))
        with patch.dict(sys.modules, {'requests': m}):
            ok, msg = self._provider().test()
        assert ok is False
        assert 'network timeout' in msg

    def test_from_name_same_as_email(self):
        mock_req = self._mock_requests(202)
        with patch.dict(sys.modules, {'requests': mock_req}):
            from flowforge.email_providers.sendgrid import SendGridProvider
            p = SendGridProvider(api_key='SG.x', from_email='a@b.com')  # no from_name
            result = p.send(['x@b.com'], [], [], 'S', 'b', [])
        assert result.success is True


# ── SES ────────────────────────────────────────────────────────────────────────

class TestSESProvider:

    def _provider(self, from_name='Sender'):
        from flowforge.email_providers.ses import SESProvider
        return SESProvider(
            aws_access_key_id='AKIA',
            aws_secret_access_key='secret',
            aws_region='us-east-1',
            from_email='sender@example.com',
            from_name=from_name,
        )

    def _mock_boto3(self, quota=None):
        m = ModuleType('boto3')
        client = MagicMock()
        m.client = MagicMock(return_value=client)
        if quota is not None:
            client.get_send_quota.return_value = quota
        return m, client

    def test_send_simple_no_cc_bcc(self):
        mock_boto3, client = self._mock_boto3()
        with patch.dict(sys.modules, {'boto3': mock_boto3}):
            result = self._provider().send(['a@b.com'], [], [], 'Subj', '<p>hi</p>', [])
        assert result.success is True
        client.send_email.assert_called_once()
        client.send_raw_email.assert_not_called()

    def test_send_with_cc_and_bcc(self):
        mock_boto3, client = self._mock_boto3()
        with patch.dict(sys.modules, {'boto3': mock_boto3}):
            result = self._provider().send(['a@b.com'], ['cc@b.com'], ['bcc@b.com'], 'S', 'b', [])
        assert result.success is True
        assert len(result.recipients) == 3
        dest = client.send_email.call_args.kwargs['Destination']
        assert 'CcAddresses' in dest
        assert 'BccAddresses' in dest

    def test_send_with_attachment_uses_raw(self, tmp_path):
        att = tmp_path / 'report.csv'
        att.write_bytes(b'a,b\n1,2\n')
        mock_boto3, client = self._mock_boto3()
        with patch.dict(sys.modules, {'boto3': mock_boto3}):
            result = self._provider().send(['a@b.com'], [], [], 'S', 'b', [att])
        assert result.success is True
        client.send_raw_email.assert_called_once()
        client.send_email.assert_not_called()

    def test_send_with_attachment_with_cc(self, tmp_path):
        att = tmp_path / 'f.csv'
        att.write_bytes(b'data')
        mock_boto3, client = self._mock_boto3()
        with patch.dict(sys.modules, {'boto3': mock_boto3}):
            result = self._provider().send(['a@b.com'], ['c@b.com'], [], 'S', 'b', [att])
        assert result.success is True
        client.send_raw_email.assert_called_once()

    def test_boto3_not_installed(self):
        with patch.dict(sys.modules, {'boto3': None}):
            with pytest.raises(ImportError, match='boto3'):
                self._provider().send(['a@b.com'], [], [], 'S', 'b', [])

    def test_test_method_success(self):
        quota = {'SentLast24Hours': 5.0, 'Max24HourSend': 200.0}
        mock_boto3, client = self._mock_boto3(quota)
        with patch.dict(sys.modules, {'boto3': mock_boto3}):
            ok, msg = self._provider().test()
        assert ok is True
        assert '5' in msg

    def test_test_method_failure(self):
        mock_boto3, client = self._mock_boto3()
        client.get_send_quota.side_effect = Exception('AccessDenied')
        with patch.dict(sys.modules, {'boto3': mock_boto3}):
            ok, msg = self._provider().test()
        assert ok is False
        assert 'AccessDenied' in msg

    def test_from_name_equals_from_email_uses_bare_address(self):
        mock_boto3, client = self._mock_boto3()
        with patch.dict(sys.modules, {'boto3': mock_boto3}):
            from flowforge.email_providers.ses import SESProvider
            p = SESProvider('AKIA', 'sec', 'us-east-1', 'a@b.com')  # no from_name
            result = p.send(['x@b.com'], [], [], 'S', 'body', [])
        assert result.success is True
        src = client.send_email.call_args.kwargs['Source']
        assert src == 'a@b.com'

    def test_region_defaults_to_us_east_1(self):
        mock_boto3, client = self._mock_boto3()
        with patch.dict(sys.modules, {'boto3': mock_boto3}):
            from flowforge.email_providers.ses import SESProvider
            p = SESProvider('AKIA', 'sec', '', 'a@b.com')  # empty region
        assert p.region == 'us-east-1'


# ── Mailgun ────────────────────────────────────────────────────────────────────

class TestMailgunProvider:

    def _provider(self, region='us'):
        from flowforge.email_providers.mailgun import MailgunProvider
        return MailgunProvider(
            api_key='key-test',
            domain='mg.example.com',
            from_email='bot@mg.example.com',
            from_name='Bot',
            region=region,
        )

    def _mock_requests(self, status_code=200, text='', json_data=None):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.text = text
        mock_resp.json.return_value = json_data or {}
        m = ModuleType('requests')
        m.post = MagicMock(return_value=mock_resp)
        m.get  = MagicMock(return_value=mock_resp)
        return m

    def test_send_success(self):
        mock_req = self._mock_requests(200)
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], [], [], 'Subj', '<p>hi</p>', [])
        assert result.success is True
        assert result.recipients == ['a@b.com']

    def test_send_with_cc_and_bcc(self):
        mock_req = self._mock_requests(200)
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], ['cc@b.com'], ['bcc@b.com'], 'S', 'b', [])
        assert result.success is True
        assert len(result.recipients) == 3
        data = mock_req.post.call_args.kwargs['data']
        assert 'cc' in data
        assert 'bcc' in data

    def test_send_with_attachment(self, tmp_path):
        att = tmp_path / 'file.pdf'
        att.write_bytes(b'data')
        mock_req = self._mock_requests(200)
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], [], [], 'S', 'b', [att])
        assert result.success is True
        files = mock_req.post.call_args.kwargs['files']
        assert files is not None

    def test_send_failure(self):
        mock_req = self._mock_requests(401, 'Unauthorized')
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider().send(['a@b.com'], [], [], 'S', 'b', [])
        assert result.success is False
        assert '401' in result.error

    def test_send_requests_not_installed(self):
        with patch.dict(sys.modules, {'requests': None}):
            result = self._provider().send(['a@b.com'], [], [], 'S', 'b', [])
        assert result.success is False

    def test_eu_region_uses_eu_api_base(self):
        from flowforge.email_providers.mailgun import _api_base
        assert 'eu.mailgun.net' in _api_base('eu')
        assert 'eu.mailgun.net' in _api_base('EU')
        assert 'eu' not in _api_base('us')

    def test_test_success(self):
        mock_req = self._mock_requests(200, json_data={'domain': {'state': 'active'}})
        with patch.dict(sys.modules, {'requests': mock_req}):
            ok, msg = self._provider().test()
        assert ok is True
        assert 'active' in msg

    def test_test_failure_non_200(self):
        mock_req = self._mock_requests(404, 'Not found')
        with patch.dict(sys.modules, {'requests': mock_req}):
            ok, msg = self._provider().test()
        assert ok is False
        assert '404' in msg

    def test_test_exception(self):
        m = ModuleType('requests')
        m.get = MagicMock(side_effect=Exception('DNS resolution failed'))
        with patch.dict(sys.modules, {'requests': m}):
            ok, msg = self._provider().test()
        assert ok is False
        assert 'DNS resolution failed' in msg

    def test_from_name_same_as_email(self):
        mock_req = self._mock_requests(200)
        with patch.dict(sys.modules, {'requests': mock_req}):
            from flowforge.email_providers.mailgun import MailgunProvider
            p = MailgunProvider('key', 'mg.ex.com', 'a@mg.ex.com')  # no from_name
            result = p.send(['x@b.com'], [], [], 'S', 'b', [])
        assert result.success is True

    def test_eu_region_provider_send(self):
        mock_req = self._mock_requests(200)
        with patch.dict(sys.modules, {'requests': mock_req}):
            result = self._provider(region='eu').send(['a@b.com'], [], [], 'S', 'b', [])
        assert result.success is True
        url = mock_req.post.call_args.args[0]
        assert 'eu.mailgun.net' in url


# ── factory._build_provider paths for new providers ───────────────────────────

class TestFactoryNewProviders:
    """Tests that factory._build_provider returns the right class for sendgrid/ses/mailgun."""

    def test_build_sendgrid(self):
        from flowforge.email_providers.factory import _build_provider
        from flowforge.email_providers.sendgrid import SendGridProvider
        p = _build_provider('sendgrid', {'api_key': 'SG.x', 'from_email': 'a@b.com'})
        assert isinstance(p, SendGridProvider)

    def test_build_ses(self):
        from flowforge.email_providers.factory import _build_provider
        from flowforge.email_providers.ses import SESProvider
        p = _build_provider('ses', {
            'aws_access_key_id':     'AKIA',
            'aws_secret_access_key': 'sec',
            'from_email':            'a@b.com',
        })
        assert isinstance(p, SESProvider)

    def test_build_mailgun(self):
        from flowforge.email_providers.factory import _build_provider
        from flowforge.email_providers.mailgun import MailgunProvider
        p = _build_provider('mailgun', {
            'api_key':    'key',
            'domain':     'mg.ex.com',
            'from_email': 'a@mg.ex.com',
        })
        assert isinstance(p, MailgunProvider)
