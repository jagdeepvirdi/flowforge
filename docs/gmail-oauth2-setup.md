# Gmail OAuth2 Setup Guide

This guide walks you through creating Gmail OAuth2 credentials so FlowForge can send emails using your Google account — at zero cost via the Gmail API.

---

## Prerequisites

- A Google account (Gmail or Google Workspace)
- Access to [Google Cloud Console](https://console.cloud.google.com)

---

## Step 1 — Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top → **New Project**
3. Give it a name (e.g. `FlowForge`) → click **Create**
4. Wait a few seconds, then make sure the new project is selected in the dropdown

---

## Step 2 — Enable the Gmail API

1. In the left sidebar go to **APIs & Services → Library**
2. Search for **Gmail API**
3. Click on it → click **Enable**
4. *(Optional but recommended)* Also search for and enable **Google Drive API** if you plan to use Drive uploads

---

## Step 3 — Configure the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** → click **Create**
3. Fill in the required fields:
   - **App name**: `FlowForge` (or anything you like)
   - **User support email**: your Gmail address
   - **Developer contact email**: your Gmail address
4. Click **Save and Continue**
5. On the **Scopes** page — click **Save and Continue** (no scopes needed here)
6. On the **Test users** page:
   - Click **+ Add Users**
   - Add your own Gmail address
   - Click **Save and Continue**
7. Click **Back to Dashboard**

> **Why test users?** While the app is in "Testing" mode (not published), only listed test users can authorise it. Adding your own address lets you proceed.

---

## Step 4 — Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. For **Application type** select **Desktop app**

   > ⚠️ This must be **Desktop app**. Choosing Web application will cause an `invalid_client` error (401) during the OAuth flow.

4. Give it a name (e.g. `FlowForge Desktop`) → click **Create**
5. A dialog shows your **Client ID** and **Client Secret** — copy both and keep them safe

---

## Step 5 — Get the Refresh Token

With your virtual environment activated, run:

```bash
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_config(
    {'installed': {
        'client_id': 'YOUR_CLIENT_ID',
        'client_secret': 'YOUR_CLIENT_SECRET',
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'redirect_uris': ['urn:ietf:wg:oauth:2.0:oob', 'http://localhost']
    }},
    scopes=[
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/drive'
    ]
)
creds = flow.run_local_server(port=0)
print('REFRESH TOKEN:', creds.refresh_token)
"
```

Replace `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` with the values from Step 4.

A browser window will open:
1. Sign in with the Google account you added as a test user
2. Click **Continue** on the "Google hasn't verified this app" warning
3. Grant the requested permissions
4. The browser will show a success message and print your refresh token in the terminal

---

## Step 6 — Add Credentials to .env

Open `.env` and fill in:

```env
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GMAIL_REFRESH_TOKEN=1//xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GMAIL_SENDER=your-gmail@gmail.com
```

Restart the FlowForge server to pick up the new values:

```powershell
# Windows
.\flowforge.ps1 stop
.\flowforge.ps1 start
```

```bash
# macOS / Linux
./flowforge.sh stop
./flowforge.sh start
```

---

## Step 7 — Add a Gmail Provider in FlowForge

1. Go to **Connections → Email Providers tab**
2. Click **Add Connection → Email Provider**
3. Select **Gmail (OAuth2)**
4. Enter your sender email and client credentials
5. Click **Test** — you should see "Verified"
6. Click **Save Provider**

---

## Step 8 — Verify with the Test Script

```bash
python tests/manual/check_email.py --to your@email.com
```

A test email will arrive in your inbox within seconds.

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Error 401: invalid_client` | Application type is not Desktop app | Delete the credential and re-create as **Desktop app** |
| `Error 403: access_denied` | Your Gmail account is not a Test User | Add it in OAuth consent screen → Test users |
| `Token has been expired or revoked` | Refresh token was invalidated | Re-run Step 5 to generate a new one |
| `Mail.Send permission denied` | Gmail API not enabled | Go to APIs & Services → Library → Enable Gmail API |
| Browser doesn't open during Step 5 | Running headless / SSH | Add `--no-browser` and use the printed URL manually |

---

## Keeping the App in Testing vs Publishing

The OAuth consent screen stays in **Testing** mode indefinitely — this is fine for personal or team use. You only need to publish if you want other Google accounts (not listed as test users) to authorise the app.

For a small team, simply add each team member's email as a Test User.

---

## Google Drive Setup (Same Credentials)

If your sender Gmail account is also the one you want to use for Drive uploads, no extra setup is needed — the same OAuth credentials and refresh token cover both `gmail.send` and `drive` scopes (both are requested in Step 5).

Set the default upload folder in `.env`:

```env
GOOGLE_DRIVE_FOLDER_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs
```

The folder ID is the last part of the Drive folder URL:
`https://drive.google.com/drive/folders/`**`1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs`**
