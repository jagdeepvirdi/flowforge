import base64
import logging
from pathlib import Path

from flowforge.email_providers.base import EmailProvider, EmailResult

logger = logging.getLogger(__name__)

_GRAPH_SEND_URL = 'https://graph.microsoft.com/v1.0/users/{sender}/sendMail'


class Microsoft365Provider(EmailProvider):
    """Microsoft 365 via Microsoft Graph API using MSAL client credentials flow."""

    def __init__(self, tenant_id: str, client_id: str, client_secret: str, sender_email: str):
        self.sender = sender_email
        self._msal_app = self._build_msal_app(tenant_id, client_id, client_secret)

    def _build_msal_app(self, tenant_id: str, client_id: str, client_secret: str):
        try:
            import msal
        except ImportError:
            raise ImportError(
                "Microsoft 365 support requires: pip install 'flowforge[microsoft365]'"
            )
        return msal.ConfidentialClientApplication(
            client_id,
            authority=f'https://login.microsoftonline.com/{tenant_id}',
            client_credential=client_secret,
        )

    def _get_token(self) -> str:
        """Acquire a token, using MSAL's in-memory cache when still valid."""
        result = self._msal_app.acquire_token_for_client(
            scopes=['https://graph.microsoft.com/.default']
        )
        if 'access_token' not in result:
            raise RuntimeError(f"MSAL token acquisition failed: {result.get('error_description')}")
        return result['access_token']

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
            raise ImportError(
                "Microsoft 365 support requires: pip install 'flowforge[microsoft365]'"
            )

        graph_attachments = []
        for file_path in attachments:
            with open(file_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode()
            graph_attachments.append({
                '@odata.type': '#microsoft.graph.fileAttachment',
                'name': file_path.name,
                'contentBytes': content,
            })

        payload = {
            'message': {
                'subject': subject,
                'body': {'contentType': 'HTML', 'content': html_body},
                'toRecipients': [{'emailAddress': {'address': a}} for a in to],
                'ccRecipients': [{'emailAddress': {'address': a}} for a in cc],
                'bccRecipients': [{'emailAddress': {'address': a}} for a in bcc],
                'attachments': graph_attachments,
            }
        }

        all_recipients = to + cc + bcc
        try:
            url = _GRAPH_SEND_URL.format(sender=self.sender)
            resp = requests.post(
                url,
                json=payload,
                headers={
                    'Authorization': f'Bearer {self._get_token()}',
                    'Content-Type': 'application/json',
                },
                timeout=30,
            )
            resp.raise_for_status()
            logger.info("Email sent to %d recipient(s) via Microsoft Graph", len(all_recipients))
            return EmailResult(success=True, recipients=all_recipients)
        except Exception as e:
            logger.error("Microsoft 365 send failed: %s", e)
            return EmailResult(success=False, error=str(e))

    def test(self) -> tuple[bool, str]:
        try:
            self._get_token()
            return True, f"Connected ({self.sender})"
        except Exception as e:
            logger.error("Microsoft 365 test failed: %s", e)
            return False, str(e)
