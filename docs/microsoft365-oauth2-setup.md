# Microsoft 365 OAuth2 Setup Guide

This guide walks you through registering an Azure AD app so FlowForge can send emails through your Microsoft 365 / Exchange Online tenant via the Microsoft Graph API.

---

## Prerequisites

- An Office 365 / Microsoft 365 subscription with at least one licensed user (the sender)
- Access to the [Azure portal](https://portal.azure.com) with permission to register apps

---

## Step 1 — Register an App in Azure AD

1. Sign in to [portal.azure.com](https://portal.azure.com)
2. Search for **App registrations** in the top bar → click it
3. Click **New registration**
4. Fill in:
   - **Name**: `FlowForge` (or any descriptive name)
   - **Supported account types**: *Accounts in this organizational directory only*
   - **Redirect URI**: leave blank (not needed for client credentials flow)
5. Click **Register**
6. Copy the **Application (client) ID** and **Directory (tenant) ID** — you need both

---

## Step 2 — Add API Permissions

1. In your app registration, go to **API permissions → Add a permission**
2. Select **Microsoft Graph**
3. Select **Application permissions** (not Delegated)
4. Search for and add: `Mail.Send`
5. Click **Add permissions**
6. Click **Grant admin consent for [your tenant]** → confirm

> **Application permissions** allow FlowForge to send as the configured sender without a user being signed in — this is what you want for background automation.

---

## Step 3 — Create a Client Secret

1. Go to **Certificates & secrets → Client secrets → New client secret**
2. Add a description (e.g. `FlowForge secret`) and choose an expiry
3. Click **Add**
4. **Copy the secret value immediately** — it is only shown once

> Client secrets expire (max 24 months in Azure AD). Note the expiry date somewhere you'll see it — an expired secret fails the same way as a wrong one (`AADSTS7000215`).

---

## Step 4 — Add Credentials to .env

```env
MICROSOFT_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=your-client-secret-value
MICROSOFT_SENDER_EMAIL=sender@yourcompany.com
```

The sender email must be a licensed Microsoft 365 user in your tenant.

Restart the FlowForge server to pick up the new values:

```powershell
# Windows
.\flowforge.ps1 dev restart
```

```bash
# macOS / Linux
./flowforge.sh dev restart
```

---

## Step 5 — Add a Microsoft 365 Provider in FlowForge

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

---

## Step 6 — Verify with the Test Script

```bash
python tests/manual/check_email.py --to your@email.com
```

A test email will arrive in your inbox within seconds.

---

## Token Refresh

FlowForge acquires a new access token before every `sendMail` call using the client credentials flow (app-to-app, no user sign-in). Microsoft 365 access tokens expire after 1 hour — re-acquisition happens transparently using the stored `MICROSOFT_CLIENT_SECRET`. There is no user-facing refresh token and nothing expires on a recurring schedule the way Gmail's Testing-mode refresh tokens do — **unless the client secret itself expires** (see Step 3), which requires minting a new secret in Azure AD and updating `.env`.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `AADSTS700016: Application not found` | Wrong tenant ID | Copy tenant ID from Azure portal → Overview |
| `AADSTS7000215: Invalid client secret` | Secret expired or copied incorrectly | Create a new client secret in Azure portal |
| `Authorization_RequestDenied: Insufficient privileges` | `Mail.Send` not granted or admin consent not given | Re-add the permission and click "Grant admin consent" |
| `ErrorSendAsDenied` | Sender email not a valid licensed M365 user | Verify `MICROSOFT_SENDER_EMAIL` is a licensed user in your tenant |

---

## Choosing a Provider

See [Email Providers](email-providers.md#choosing-a-provider) for a comparison of SMTP, Microsoft 365, and Gmail.
