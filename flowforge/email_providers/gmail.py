import base64
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from flowforge.email_providers.base import EmailProvider, EmailResult

logger = logging.getLogger(__name__)

_GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class GmailProvider(EmailProvider):
    """Gmail via OAuth2 using the Gmail REST API. Requires google-auth + google-api-python-client."""

    def __init__(self, client_id: str, client_secret: str, refresh_token: str, sender: str):
        self.sender = sender
        self._creds = self._build_credentials(client_id, client_secret, refresh_token)

    def _build_credentials(self, client_id: str, client_secret: str, refresh_token: str):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
        except ImportError:
            raise ImportError(
                "Gmail support requires: pip install 'flowforge[gmail]'"
            )
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=_GMAIL_SCOPES,
        )
        creds.refresh(Request())
        return creds

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
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "Gmail support requires: pip install 'flowforge[gmail]'"
            )

        msg = MIMEMultipart()
        msg['From'] = self.sender
        msg['To'] = ', '.join(to)
        if cc:
            msg['Cc'] = ', '.join(cc)
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        for file_path in attachments:
            with open(file_path, 'rb') as f:
                payload = f.read()
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(payload)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{file_path.name}"')
            msg.attach(part)

        all_recipients = to + cc + bcc
        try:
            service = build('gmail', 'v1', credentials=self._creds)
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId='me', body={'raw': raw}).execute()
            logger.info("Email sent to %d recipient(s) via Gmail API", len(all_recipients))
            return EmailResult(success=True, recipients=all_recipients)
        except Exception as e:
            logger.error("Gmail API send failed: %s", e)
            return EmailResult(success=False, error=str(e))

    def test(self) -> tuple[bool, str]:
        try:
            from googleapiclient.discovery import build as api_build
            service = api_build('gmail', 'v1', credentials=self._creds)
            profile = service.users().getProfile(userId='me').execute()
            return True, f"Connected as {profile.get('emailAddress', 'unknown')}"
        except Exception as e:
            logger.error("Gmail test failed: %s", e)
            return False, str(e)
