#!/usr/bin/env python
"""
Manual Gmail send test.
Verifies that the Gmail credentials in .env can actually send an email.

Usage:
    python tests/manual/check_email.py --to you@example.com
"""
import argparse
import os
import sys

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


def check_env():
    required = ['GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET', 'GMAIL_REFRESH_TOKEN', 'GMAIL_SENDER']
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f'✗ Missing env vars: {", ".join(missing)}')
        print('  Set these in .env — see docs/gmail-oauth2-setup.md')
        return False
    print('✓ Gmail env vars present')
    return True


def send_test_email(to_address: str):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from flowforge.email_providers.gmail import GmailProvider
    from pathlib import Path

    config = {
        'client_id':     os.environ['GMAIL_CLIENT_ID'],
        'client_secret': os.environ['GMAIL_CLIENT_SECRET'],
        'refresh_token': os.environ['GMAIL_REFRESH_TOKEN'],
        'sender':        os.environ['GMAIL_SENDER'],
    }

    provider = GmailProvider(config)
    result = provider.send(
        to=[to_address],
        cc=[],
        bcc=[],
        subject='[FlowForge] Email test',
        html_body='<p>This is a test email from the FlowForge manual email check script.</p>',
        attachments=[],
    )

    if result.success:
        print(f'✓ Email sent to {to_address}')
        return True
    else:
        print(f'✗ Send failed: {result.error}')
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FlowForge Gmail send test')
    parser.add_argument('--to', required=True, help='Email address to send test to')
    args = parser.parse_args()

    print('\nFlowForge Gmail check\n' + '─'*30)
    ok = check_env()
    if ok:
        ok = send_test_email(args.to)

    print('─'*30)
    sys.exit(0 if ok else 1)
