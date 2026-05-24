import logging
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from flowforge.email_providers.base import EmailProvider, EmailResult

logger = logging.getLogger(__name__)


class SMTPProvider(EmailProvider):
    """Generic SMTP provider — covers Gmail (SSL), Microsoft (STARTTLS), and any SMTP server."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = False,
        use_tls: bool = True,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.use_tls = use_tls

    def send(
        self,
        to: list[str],
        cc: list[str],
        bcc: list[str],
        subject: str,
        html_body: str,
        attachments: list[Path],
    ) -> EmailResult:
        msg = MIMEMultipart()
        msg['From'] = self.username
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
        context = ssl.create_default_context()
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=30)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=30)
                if self.use_tls:
                    server.starttls(context=context)
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            logger.info("Email sent to %d recipient(s) via %s:%s", len(all_recipients), self.host, self.port)
            return EmailResult(success=True, recipients=all_recipients)
        except Exception as e:
            logger.error("SMTP send failed: %s", e)
            return EmailResult(success=False, error=str(e))

    def test(self) -> tuple[bool, str]:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                if self.use_tls:
                    server.starttls(context=ctx)
            if self.username:
                server.login(self.username, self.password)
            server.quit()
            return True, f"Connected to {self.host}:{self.port}"
        except Exception as e:
            logger.error("SMTP test failed: %s", e)
            return False, str(e)
