# Gmail API Setup Instructions

## Prerequisites

You need a Google Cloud account to use the Gmail API.

## Step-by-Step Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Note your project ID

### 2. Enable Gmail API

1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Gmail API"
3. Click on it and click **Enable**

### 3. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - User Type: **External** (for personal Gmail) or **Internal** (for Google Workspace)
   - App name: "Email Security Tool" (or your choice)
   - User support email: Your email
   - Developer contact: Your email
   - Add scope: `https://www.googleapis.com/auth/gmail.readonly`
   - Add test users (your Gmail address)
4. Back to Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: "Email Security Desktop Client"
   - Click **Create**
5. Download the credentials JSON file
6. Rename it to `credentials.json` and place it in the project root directory

### 4. Install Dependencies

```bash
# Install/update dependencies
uv sync
```

### 5. Run the Test Script

```bash
python fetch_gmail.py
```

On first run:

- A browser window will open asking you to authorize the application
- Sign in with your Google account
- Grant the requested permissions (read-only access to Gmail)
- The script will save a `token.json` file for future use

### 6. Verify It Works

The script will fetch your most recent emails and display them in the terminal, converted to `Email` objects.

## Configuration

You can customize settings by creating a `.env` file (see `.env.example`):

```bash
cp .env.example .env
```

Available settings:

- `GMAIL_CREDENTIALS_FILE`: Path to credentials.json (default: ./credentials.json)
- `GMAIL_TOKEN_FILE`: Path to token.json (default: ./token.json)
- `MAX_EMAILS_TO_FETCH`: Default number of emails to fetch (default: 10)

## Using in Your Code

```python
from gmail_service import fetch_gmail_messages

# Fetch recent inbox emails
emails = fetch_gmail_messages(max_results=5, query="in:inbox")

# Fetch emails after a specific date
emails = fetch_gmail_messages(query="after:2026/02/01")

# Fetch unread emails
emails = fetch_gmail_messages(query="is:unread")

# Each email is an Email object with all the fields from models.py
for email in emails:
    print(f"From: {email.sender}")
    print(f"Subject: {email.subject}")
    print(f"Body: {email.body[:100]}...")
```

## Gmail Search Query Examples

- `in:inbox` - Inbox messages
- `in:sent` - Sent messages
- `is:unread` - Unread messages
- `from:example@gmail.com` - From specific sender
- `to:example@gmail.com` - To specific recipient
- `subject:invoice` - Subject contains "invoice"
- `after:2026/02/01` - After specific date
- `before:2026/02/10` - Before specific date
- `has:attachment` - Has attachments
- `newer_than:7d` - Newer than 7 days

You can combine queries with spaces (implicit AND):

- `from:example@gmail.com after:2026/02/01` - From specific sender after date

## Troubleshooting

**Error: credentials.json not found**

- Make sure you downloaded the OAuth credentials from Google Cloud Console
- Place the file in the project root directory
- Verify the filename is exactly `credentials.json`

**Error: Access blocked**

- Ensure the OAuth consent screen is configured correctly
- Add your email to the test users list if using External user type
- Make sure Gmail API is enabled

**Error: Token expired**

- Delete `token.json` and run the script again to re-authenticate

## Security Notes

- `credentials.json` and `token.json` contain sensitive information
- They are already in `.gitignore` to prevent accidental commits
- Never share these files or commit them to version control
- The app only requests read-only access (`gmail.readonly` scope)
