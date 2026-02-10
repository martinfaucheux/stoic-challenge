"""Gmail API authentication module"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import settings


def get_gmail_service():
    """
    Authenticate and return Gmail API service.

    This function handles the OAuth 2.0 flow:
    1. Checks if valid token exists (token.json)
    2. If token expired, refreshes it
    3. If no valid credentials, runs OAuth flow to get new credentials
    4. Saves credentials for future use

    Returns:
        gmail service: Authenticated Gmail API service resource
    """
    creds = None

    # Load existing token if available
    if os.path.exists(settings.GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            settings.GMAIL_TOKEN_FILE, settings.GMAIL_SCOPES
        )

    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            creds.refresh(Request())
        else:
            # Run OAuth flow to get new credentials
            if not os.path.exists(settings.GMAIL_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Credentials file not found at {settings.GMAIL_CREDENTIALS_FILE}. "
                    "Please download it from Google Cloud Console."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                settings.GMAIL_CREDENTIALS_FILE, settings.GMAIL_SCOPES
            )
            # Use fixed port 8080 to match OAuth redirect URI
            creds = flow.run_local_server(port=8080)

        # Save credentials for next run
        with open(settings.GMAIL_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    # Build and return Gmail service
    service = build("gmail", "v1", credentials=creds)
    return service
