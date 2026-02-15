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

    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

    # Gmail API settings
    GMAIL_CREDENTIALS_FILE = os.getenv(
        "GMAIL_CREDENTIALS_FILE", str(BASE_DIR / "gmail" / "credentials.json")
    )
    GMAIL_TOKEN_FILE = os.getenv(
        "GMAIL_TOKEN_FILE", str(BASE_DIR / "gmail" / "token.json")
    )
    GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    # Email fetching settings
    MAX_EMAILS_TO_FETCH = int(os.getenv("MAX_EMAILS_TO_FETCH", "100"))

    # Database settings
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/email_security",
    )

    # JWT settings
    JWT_ENCRYPTION_ALGORITHM = os.getenv("JWT_ENCRYPTION_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # OAuth settings
    GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
        "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback/google"
    )
    GOOGLE_OAUTH_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "openid",
        "email",
        "profile",
    ]

    # Token encryption settings
    FERNET_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

    # Application base URL
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


settings = Settings()
