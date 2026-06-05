"""Mailgun email provider — sends via the Mailgun Messages API."""
import logging
from pathlib import Path

from flowforge.email_providers.base import EmailProvider, EmailResult

logger = logging.getLogger(__name__)


def _api_base(region: str) -> str:
    return 'https://api.eu.mailgun.net' if region.lower() == 'eu' else 'https://api.mailgun.net'


class MailgunProvider(EmailProvider):
    def __init__(
        self,
        api_key: str,
        domain: str,
        from_email: str,
        from_name: str = '',
        region: str = 'us',
    ):
        self.api_key    = api_key
        self.domain     = domain
        self.from_email = from_email
        self.from_name  = from_name or from_email
        self.region     = region

    def send(
        self,
        to: list[str],
        cc: list[str],
        bcc: list[str],
        subject: str,
        html_body: str,
        attachments: list[Path],
    ) -> EmailResult:
        try:
            import requests
        except ImportError:
            return EmailResult(success=False, error='requests is not installed')

        url  = f'{_api_base(self.region)}/v3/{self.domain}/messages'
        from_field = f'{self.from_name} <{self.from_email}>' if self.from_name != self.from_email else self.from_email

        data = {
            'from':    from_field,
            'to':      ','.join(to),
            'subject': subject,
            'html':    html_body,
        }
        if cc:
            data['cc']  = ','.join(cc)
        if bcc:
            data['bcc'] = ','.join(bcc)

        files = [('attachment', (p.name, p.read_bytes(), 'application/octet-stream')) for p in attachments]
        all_recipients = to + cc + bcc

        resp = requests.post(
            url,
            auth=('api', self.api_key),
            data=data,
            files=files or None,
            timeout=30,
        )
        if resp.status_code == 200:
            logger.info("Mailgun: sent to %d recipient(s)", len(all_recipients))
            return EmailResult(success=True, recipients=all_recipients)
        error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        logger.error("Mailgun send failed: %s", error)
        return EmailResult(success=False, error=error)

    def test(self) -> tuple[bool, str]:
        try:
            import requests
            url  = f'{_api_base(self.region)}/v3/domains/{self.domain}'
            resp = requests.get(url, auth=('api', self.api_key), timeout=10)
            if resp.status_code == 200:
                state = resp.json().get('domain', {}).get('state', 'unknown')
                return True, f"Domain '{self.domain}' — state: {state}"
            return False, f"HTTP {resp.status_code}: {resp.text[:120]}"
        except Exception as e:
            logger.exception("Mailgun test failed")
            return False, str(e)
