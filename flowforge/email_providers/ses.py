"""AWS SES email provider — sends via boto3 SES client (raw MIME for attachment support)."""
import logging
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from flowforge.email_providers.base import EmailProvider, EmailResult

logger = logging.getLogger(__name__)


class SESProvider(EmailProvider):
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str,
        from_email: str,
        from_name: str = '',
    ):
        self.key_id     = aws_access_key_id
        self.secret_key = aws_secret_access_key
        self.region     = aws_region or 'us-east-1'
        self.from_email = from_email
        self.from_name  = from_name or from_email

    def _client(self):
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 is required for AWS SES. Install with: pip install flowforge[ses]")
        return boto3.client(
            'ses',
            region_name=self.region,
            aws_access_key_id=self.key_id,
            aws_secret_access_key=self.secret_key,
        )

    def send(
        self,
        to: list[str],
        cc: list[str],
        bcc: list[str],
        subject: str,
        html_body: str,
        attachments: list[Path],
    ) -> EmailResult:
        client = self._client()
        all_recipients = to + cc + bcc

        if attachments:
            # Use SendRawEmail for attachments
            msg = MIMEMultipart()
            msg['From']    = f'{self.from_name} <{self.from_email}>' if self.from_name != self.from_email else self.from_email
            msg['To']      = ', '.join(to)
            if cc:
                msg['Cc']  = ', '.join(cc)
            msg['Subject'] = subject
            msg.attach(MIMEText(html_body, 'html'))

            for path in attachments:
                with open(path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{path.name}"')
                msg.attach(part)

            client.send_raw_email(
                Source=self.from_email,
                Destinations=all_recipients,
                RawMessage={'Data': msg.as_bytes()},
            )
        else:
            dest: dict = {'ToAddresses': to}
            if cc:
                dest['CcAddresses'] = cc
            if bcc:
                dest['BccAddresses'] = bcc
            client.send_email(
                Source=f'{self.from_name} <{self.from_email}>' if self.from_name != self.from_email else self.from_email,
                Destination=dest,
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body':    {'Html': {'Data': html_body, 'Charset': 'UTF-8'}},
                },
            )

        logger.info("AWS SES: sent to %d recipient(s)", len(all_recipients))
        return EmailResult(success=True, recipients=all_recipients)

    def test(self) -> tuple[bool, str]:
        try:
            client = self._client()
            resp = client.get_send_quota()
            used  = resp.get('SentLast24Hours', 0)
            limit = resp.get('Max24HourSend', 0)
            return True, f"Connected — sent today: {used:.0f}/{limit:.0f}"
        except Exception as e:
            logger.exception("AWS SES test failed")
            return False, str(e)
