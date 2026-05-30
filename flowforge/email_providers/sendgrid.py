"""SendGrid email provider — sends via the SendGrid Web API v3."""
import base64
import logging
from pathlib import Path

from flowforge.email_providers.base import EmailProvider, EmailResult

logger = logging.getLogger(__name__)

_API_URL = 'https://api.sendgrid.com/v3/mail/send'


class SendGridProvider(EmailProvider):
    def __init__(self, api_key: str, from_email: str, from_name: str = ''):
        self.api_key    = api_key
        self.from_email = from_email
        self.from_name  = from_name or from_email

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

        payload: dict = {
            'from':             {'email': self.from_email, 'name': self.from_name},
            'subject':          subject,
            'personalizations': [{'to': [{'email': a} for a in to]}],
            'content':          [{'type': 'text/html', 'value': html_body}],
        }
        if cc:
            payload['personalizations'][0]['cc'] = [{'email': a} for a in cc]
        if bcc:
            payload['personalizations'][0]['bcc'] = [{'email': a} for a in bcc]
        if attachments:
            payload['attachments'] = [
                {
                    'content':     base64.b64encode(p.read_bytes()).decode(),
                    'filename':    p.name,
                    'type':        'application/octet-stream',
                    'disposition': 'attachment',
                }
                for p in attachments
            ]

        all_recipients = to + cc + bcc
        resp = requests.post(
            _API_URL,
            json=payload,
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            timeout=30,
        )
        if resp.status_code in (200, 202):
            logger.info("SendGrid: sent to %d recipient(s)", len(all_recipients))
            return EmailResult(success=True, recipients=all_recipients)
        error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        logger.error("SendGrid send failed: %s", error)
        return EmailResult(success=False, error=error)

    def test(self) -> tuple[bool, str]:
        try:
            import requests
            resp = requests.get(
                'https://api.sendgrid.com/v3/user/profile',
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=10,
            )
            if resp.status_code == 200:
                username = resp.json().get('username', self.from_email)
                return True, f"Connected — account: {username}"
            return False, f"HTTP {resp.status_code}: {resp.text[:120]}"
        except Exception as e:
            logger.exception("SendGrid test failed")
            return False, str(e)
