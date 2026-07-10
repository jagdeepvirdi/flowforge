# Email Providers

FlowForge supports three email providers. Each is configured once in **Connections → Email Providers**, then referenced by any number of email configs.

| Provider | Best for |
|---|---|
| **SMTP** | Any standard mail server — fastest to configure |
| **Microsoft 365** | Office 365 / Exchange Online — see [Microsoft 365 OAuth2 Setup](microsoft365-oauth2-setup.md) |
| **Gmail (OAuth2)** | Google accounts — see [Gmail OAuth2 Setup](gmail-oauth2-setup.md) |

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

## Choosing a Provider

| | SMTP | Microsoft 365 | Gmail |
|---|---|---|---|
| Setup time | 2 min | 20 min | 15 min |
| Requires cloud console | No | Yes (Azure) | Yes (Google Cloud) |
| Daily send limits | Varies by server | 10,000/day (standard) | 500/day (free), 2,000/day (Workspace) |
| Token expiry handling | N/A | Auto (re-acquire) | Auto (refresh token) |
| Best for | Anything with SMTP | Office 365 tenants | Google accounts / Workspace |
