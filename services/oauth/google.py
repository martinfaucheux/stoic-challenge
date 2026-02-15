"""Google OAuth integration service"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import UserEmailConfiguration
from utils.crypto import decrypt_token, encrypt_token


class GoogleOAuthService:
    """Service for handling Google OAuth flow and token management"""

    # Google OAuth 2.0 endpoints
    AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self):
        pass  # Validate credentials when needed, not during initialization

    def _validate_credentials(self):
        """Validate that OAuth credentials are configured"""
        if (
            not settings.GOOGLE_OAUTH_CLIENT_ID
            or not settings.GOOGLE_OAUTH_CLIENT_SECRET
        ):
            raise ValueError(
                "Google OAuth credentials not configured. Please set GOOGLE_OAUTH_CLIENT_ID "
                "and GOOGLE_OAUTH_CLIENT_SECRET environment variables."
            )

    def generate_authorization_url(self, state: str | None = None) -> str:
        """
        Generate Google OAuth authorization URL

        Args:
            state: Optional state parameter for security (generated if not provided)

        Returns:
            Authorization URL to redirect user to
        """
        self._validate_credentials()

        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "scope": " ".join(settings.GOOGLE_OAUTH_SCOPES),
            "response_type": "code",
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Always show consent screen to ensure refresh token
            "state": state,
        }

        return f"{self.AUTHORIZATION_BASE_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, authorization_code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens

        Args:
            authorization_code: Authorization code from OAuth callback

        Returns:
            Token response containing access_token, refresh_token, expires_in, etc.
            Also adds 'expires_at' field with calculated expiration timestamp.

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        self._validate_credentials()
        data = {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "code": authorization_code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Valid refresh token

        Returns:
            Token response with new access_token and expires_in.
            Also adds 'expires_at' field with calculated expiration timestamp.

        Raises:
            httpx.HTTPError: If token refresh fails
        """
        self._validate_credentials()
        data = {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """
        Get user information using access token

        Args:
            access_token: Valid access token

        Returns:
            User info including email, name, etc.

        Raises:
            httpx.HTTPError: If user info request fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(self.USERINFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()

    async def save_user_configuration(
        self,
        db: AsyncSession,
        user_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int | None = None,
        token_type: str = "Bearer",
    ) -> UserEmailConfiguration:
        """
        Save OAuth tokens to user's email configuration

        Args:
            db: Database session
            user_id: User UUID
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_at: Token expiration datetime (optional)
            expires_in: Token expiration in seconds (fallback if expires_at not provided)
            token_type: Token type (default: "Bearer")

        Returns:
            Created or updated UserEmailConfiguration
        """
        if not (
            settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET
        ):
            raise ValueError("Google OAuth credentials not configured")

        # Use the provided expiration time or calculate it from expires_in
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            if expires_in
            else None
        )

        # Encrypt tokens
        access_token_encrypted = encrypt_token(access_token)
        refresh_token_encrypted = None
        if refresh_token:
            refresh_token_encrypted = encrypt_token(refresh_token)

        query = select(UserEmailConfiguration).where(
            UserEmailConfiguration.user_id == user_id,
            UserEmailConfiguration.provider == "google",
        )
        result = await db.execute(query)
        existing_config = result.scalar_one_or_none()

        if existing_config:
            # Update existing configuration
            update_stmt = (
                update(UserEmailConfiguration)
                .where(
                    UserEmailConfiguration.user_id == user_id,
                    UserEmailConfiguration.provider == "google",
                )
                .values(
                    access_token_encrypted=access_token_encrypted,
                    refresh_token_encrypted=refresh_token_encrypted
                    or existing_config.refresh_token_encrypted,
                    client_id_encrypted=encrypt_token(settings.GOOGLE_OAUTH_CLIENT_ID),
                    client_secret_encrypted=encrypt_token(
                        settings.GOOGLE_OAUTH_CLIENT_SECRET
                    ),
                    token_expires_at=expires_at,
                    provider_config={
                        "scopes": settings.GOOGLE_OAUTH_SCOPES,
                        "token_type": token_type,
                    },
                )
                .returning(UserEmailConfiguration)
            )
            result = await db.execute(update_stmt)
            config = result.scalar_one()
        else:
            # Create new configuration
            config = UserEmailConfiguration(
                user_id=user_id,
                provider="google",
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                client_id_encrypted=encrypt_token(settings.GOOGLE_OAUTH_CLIENT_ID),
                client_secret_encrypted=encrypt_token(
                    settings.GOOGLE_OAUTH_CLIENT_SECRET
                ),
                token_expires_at=expires_at,
                provider_config={
                    "scopes": settings.GOOGLE_OAUTH_SCOPES,
                    "token_type": token_type,
                },
            )
            db.add(config)

        await db.commit()
        await db.refresh(config)
        return config

    async def get_valid_access_token(
        self, db: AsyncSession, user_id: str
    ) -> Optional[str]:
        """
        Get valid access token for user, refreshing if necessary

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Valid access token or None if no configuration exists

        Raises:
            ValueError: If token refresh fails
        """

        stmt = select(UserEmailConfiguration).where(
            UserEmailConfiguration.user_id == user_id,
            UserEmailConfiguration.provider == "google",
        )
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config or not config.access_token_encrypted:
            return None

        # Check if token is still valid (with 5 minute buffer)
        now = datetime.now(timezone.utc)
        if config.token_expires_at and config.token_expires_at > now + timedelta(
            minutes=5
        ):
            return decrypt_token(config.access_token_encrypted)

        # Token expired, try to refresh
        if not config.refresh_token_encrypted:
            raise ValueError("Access token expired and no refresh token available")

        refresh_token = decrypt_token(config.refresh_token_encrypted)
        try:
            token_response = await self.refresh_access_token(refresh_token)

            # Update configuration with new token
            await self.save_user_configuration(
                db=db,
                user_id=user_id,
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                expires_in=token_response.get("expires_in"),
                token_type=token_response.get("token_type", "Bearer"),
            )

            return token_response["access_token"]
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to refresh access token: {e}")

    def decrypt_tokens(
        self,
        encrypted_access_token: Optional[str],
        encrypted_refresh_token: Optional[str],
    ) -> dict[str, str]:
        """Decrypt stored tokens

        Args:
            encrypted_access_token: Encrypted access token from database
            encrypted_refresh_token: Encrypted refresh token from database

        Returns:
            dict with 'access_token' and 'refresh_token' keys
        """
        tokens = {}

        if encrypted_access_token:
            tokens["access_token"] = decrypt_token(encrypted_access_token)
        else:
            tokens["access_token"] = ""

        if encrypted_refresh_token:
            tokens["refresh_token"] = decrypt_token(encrypted_refresh_token)
        else:
            tokens["refresh_token"] = ""

        return tokens

    async def save_user_tokens(
        self, db: AsyncSession, user_id: str, tokens: dict[str, Any]
    ) -> None:
        """Save refreshed tokens to database

        Args:
            db: Database session
            user_id: User ID
            tokens: Token response from OAuth refresh
        """
        await self.save_user_configuration(
            db=db,
            user_id=user_id,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_in=tokens.get("expires_in"),
            token_type=tokens.get("token_type", "Bearer"),
        )


# Global service instance
google_oauth_service = GoogleOAuthService()
