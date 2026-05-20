# Email Providers

FlowForge supports three email providers. Each is configured once in **Connections → Email Providers**, then referenced by any number of email configs.

| Provider | Best for |
|---|---|
| **SMTP** | Any standard mail server — fastest to configure |
| **Microsoft 365** | Office 365 / Exchange Online — Azure AD app registration required |
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

Microsoft 365 uses OAuth2 via the MSAL library and the Microsoft Graph API. Sending happens through Graph's `sendMail` endpoint — no SMTP relay needed.

### Prerequisites

- An Office 365 / Microsoft 365 subscription with at least one licensed user (the sender)
- Access to the [Azure portal](https://portal.azure.com) with permission to register apps

### Step 1 — Register an App in Azure AD

1. Sign in to [portal.azure.com](https://portal.azure.com)
2. Search for **App registrations** in the top bar → click it
3. Click **New registration**
4. Fill in:
   - **Name**: `FlowForge` (or any descriptive name)
   - **Supported account types**: *Accounts in this organizational directory only*
   - **Redirect URI**: leave blank (not needed for client credentials flow)
5. Click **Register**
6. Copy the **Application (client) ID** and **Directory (tenant) ID** — you need both

### Step 2 — Add API Permissions

1. In your app registration, go to **API permissions → Add a permission**
2. Select **Microsoft Graph**
3. Select **Application permissions** (not Delegated)
4. Search for and add: `Mail.Send`
5. Click **Add permissions**
6. Click **Grant admin consent for [your tenant]** → confirm

> **Application permissions** allow FlowForge to send as the configured sender without a user being signed in — this is what you want for background automation.

### Step 3 — Create a Client Secret

1. Go to **Certificates & secrets → Client secrets → New client secret**
2. Add a description (e.g. `FlowForge secret`) and choose an expiry
3. Click **Add**
4. **Copy the secret value immediately** — it is only shown once

### Step 4 — Add Credentials to .env

```env
MICROSOFT_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=your-client-secret-value
MICROSOFT_SENDER_EMAIL=sender@yourcompany.com
```

The sender email must be a licensed Microsoft 365 user in your tenant.

### Step 5 — Add a Microsoft 365 Provider in FlowForge

1. Go to **Connections → Email Providers tab**
2. Click **Add Connection → Email Provider**
3. Select **Microsoft 365**
4. Enter your Tenant ID, Client ID, Client Secret, and Sender Email
5. Click **Test** — FlowForge acquires a token via MSAL and verifies the Graph API connection
6. Click **Save Provider**

Or run the guided setup wizard:

```bash
flowforge setup microsoft365
```

This prompts for each value and writes them to `.env`.

### Token Refresh

FlowForge acquires a new access token before every `sendMail` call. Microsoft 365 tokens expire after 1 hour — the re-acquisition happens transparently using the stored client credentials. No manual refresh is needed.

### Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `AADSTS700016: Application not found` | Wrong tenant ID | Copy tenant ID from Azure portal → Overview |
| `AADSTS7000215: Invalid client secret` | Secret expired or copied incorrectly | Create a new client secret in Azure portal |
| `Authorization_RequestDenied: Insufficient privileges` | `Mail.Send` not granted or admin consent not given | Re-add the permission and click "Grant admin consent" |
| `ErrorSendAsDenied` | Sender email not a valid licensed M365 user | Verify `MICROSOFT_SENDER_EMAIL` is a licensed user in your tenant |

---

## Choosing a Provider

| | SMTP | Microsoft 365 | Gmail |
|---|---|---|---|
| Setup time | 2 min | 20 min | 15 min |
| Requires cloud console | No | Yes (Azure) | Yes (Google Cloud) |
| Daily send limits | Varies by server | 10,000/day (standard) | 500/day (free), 2,000/day (Workspace) |
| Token expiry handling | N/A | Auto (re-acquire) | Auto (refresh token) |
| Best for | Anything with SMTP | Office 365 tenants | Google accounts / Workspace |
