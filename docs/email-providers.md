# Email Providers

FlowForge supports six email providers. Each is configured once in **Connections → Email Providers**, then referenced by any number of email configs. All six implement the same `EmailProvider` interface (`flowforge/email_providers/base.py`), so nothing else in a pipeline needs to know which one is sending.

| Provider | Best for |
|---|---|
| **SMTP** | Any standard mail server — fastest to configure |
| **Microsoft 365** | Office 365 / Exchange Online — see [Microsoft 365 OAuth2 Setup](microsoft365-oauth2-setup.md) |
| **Gmail (OAuth2)** | Google accounts — see [Gmail OAuth2 Setup](gmail-oauth2-setup.md) |
| **SendGrid** | Transactional email at scale via SendGrid's HTTP API |
| **Amazon SES** | AWS-native transactional email |
| **Mailgun** | Transactional email via Mailgun's HTTP API |

SendGrid, SES, and Mailgun can also be reached the SMTP way (see **Common Presets** under SMTP
below) if you'd rather manage one credential type — but each has a dedicated provider below that
talks to the vendor's HTTP API directly instead of an SMTP relay, with its own config schema (API
key, not host/port/username/password).

---

## SMTP

SMTP works with any standard mail server: corporate Exchange, Outlook.com, Yahoo Mail, SendGrid SMTP relay, AWS SES SMTP, Mailgun, and others.

### Configuration

| Field | Description |
|---|---|
| `host` | SMTP server hostname |
| `port` | Typically `587` (STARTTLS) or `465` (SSL) or `25` (plain) |
| `username` | Login username (usually the sender's email) |
| `password` | SMTP password or app password |
| `use_tls` | `true` to use STARTTLS (port 587) |
| `use_ssl` | `true` to use SSL/TLS from the start (port 465) |
| `from_address` | Envelope sender address |

### Common Presets

**Outlook / Office 365 (personal accounts)**
```
Host:     smtp-mail.outlook.com
Port:     587
TLS:      true
SSL:      false
```

**Gmail (app password — simpler than OAuth2 but less secure)**
```
Host:     smtp.gmail.com
Port:     587
TLS:      true
Password: 16-character App Password (not your account password)
```
> Generate an App Password at myaccount.google.com → Security → 2-Step Verification → App Passwords

**Yahoo Mail**
```
Host:     smtp.mail.yahoo.com
Port:     587
TLS:      true
Password: App-specific password from Yahoo account settings
```

**SendGrid**
```
Host:     smtp.sendgrid.net
Port:     587
Username: apikey
Password: your SendGrid API key
```

### Adding in FlowForge

1. Go to **Connections → Email Providers tab**
2. Click **Add Connection → Email Provider**
3. Select **SMTP**
4. Fill in host, port, username, password, and TLS/SSL flags
5. Click **Test** — FlowForge sends a test connection (no email is sent)
6. Click **Save Provider**

---

## Microsoft 365

Microsoft 365 uses OAuth2 via the MSAL library and the Microsoft Graph API. Sending happens through Graph's `sendMail` endpoint — no SMTP relay needed. Full setup walkthrough (Azure AD app registration, API permissions, client secret, `.env` config, troubleshooting): see [Microsoft 365 OAuth2 Setup](microsoft365-oauth2-setup.md).

### Adding in FlowForge

1. Go to **Connections → Email Providers tab**
2. Click **Add Connection → Email Provider**
3. Select **Microsoft 365**
4. Enter your Tenant ID, Client ID, Client Secret, and Sender Email
5. Click **Test** — FlowForge acquires a token via MSAL and verifies the Graph API connection
6. Click **Save Provider**

Or run the guided setup wizard: `flowforge setup microsoft365`

---

## SendGrid

Sends via SendGrid's HTTP API (`flowforge/email_providers/sendgrid.py`) rather than an SMTP relay. Requires `pip install -e .[sendgrid]`.

### Configuration

| Field | Description |
|---|---|
| `api_key` | SendGrid API key with Mail Send permission |
| `from_email` | Verified sender address (single sender or domain-authenticated) |
| `from_name` | Optional display name |

### Adding in FlowForge

1. Go to **Connections → Email Providers tab**
2. Click **Add Connection → Email Provider**
3. Select **SendGrid**
4. Enter your API key and `from_email`
5. Click **Test**, then **Save Provider**

---

## Amazon SES

Sends via the AWS SES API (`flowforge/email_providers/ses.py`). Requires `pip install -e .[ses]`.

### Configuration

| Field | Description |
|---|---|
| `aws_access_key_id` | IAM credential with `ses:SendEmail` / `ses:SendRawEmail` |
| `aws_secret_access_key` | IAM secret key |
| `aws_region` | SES region (default `us-east-1`) |
| `from_email` | Verified SES sender identity |
| `from_name` | Optional display name |

### Adding in FlowForge

1. Go to **Connections → Email Providers tab**
2. Click **Add Connection → Email Provider**
3. Select **Amazon SES**
4. Enter your IAM access key, secret key, region, and verified `from_email`
5. Click **Test**, then **Save Provider**

> SES accounts in the sandbox can only send to verified addresses — request production access in the AWS console before sending to arbitrary recipients.

---

## Mailgun

Sends via Mailgun's HTTP API (`flowforge/email_providers/mailgun.py`). Requires `pip install -e .[mailgun]`.

### Configuration

| Field | Description |
|---|---|
| `api_key` | Mailgun private API key |
| `domain` | Your verified sending domain |
| `from_email` | Sender address on that domain |
| `from_name` | Optional display name |
| `region` | `us` (default) or `eu` — must match the region your domain was created in |

### Adding in FlowForge

1. Go to **Connections → Email Providers tab**
2. Click **Add Connection → Email Provider**
3. Select **Mailgun**
4. Enter your API key, domain, `from_email`, and region
5. Click **Test**, then **Save Provider**

---

## Choosing a Provider

| | SMTP | Microsoft 365 | Gmail | SendGrid | Amazon SES | Mailgun |
|---|---|---|---|---|---|---|
| Setup time | 2 min | 20 min | 15 min | 5 min | 10 min (IAM + verify) | 5 min |
| Requires cloud console | No | Yes (Azure) | Yes (Google Cloud) | Yes (SendGrid) | Yes (AWS) | Yes (Mailgun) |
| Daily send limits | Varies by server | 10,000/day (standard) | 500/day (free), 2,000/day (Workspace) | Plan-dependent | Plan-dependent (sandbox is verified-recipients-only) | Plan-dependent |
| Token expiry handling | N/A | Auto (re-acquire) | Auto (refresh token) | N/A (static API key) | N/A (static IAM key) | N/A (static API key) |
| Best for | Anything with SMTP | Office 365 tenants | Google accounts / Workspace | High-volume transactional email | AWS-native stacks | High-volume transactional email |
