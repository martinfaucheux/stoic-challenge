"""Configuration settings for the email security tool"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings"""

    # Project root directory
    BASE_DIR = Path(__file__).parent

    # Gmail API settings
    GMAIL_CREDENTIALS_FILE = os.getenv(
        "GMAIL_CREDENTIALS_FILE", str(BASE_DIR / "gmail" / "credentials.json")
    )
    GMAIL_TOKEN_FILE = os.getenv(
        "GMAIL_TOKEN_FILE", str(BASE_DIR / "gmail" / "token.json")
    )
    GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    # Email fetching settings
    MAX_EMAILS_TO_FETCH = int(os.getenv("MAX_EMAILS_TO_FETCH", "10"))

    # Database settings
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/email_security",
    )


settings = Settings()
