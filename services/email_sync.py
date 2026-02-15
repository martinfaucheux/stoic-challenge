"""Email synchronization service"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings
from models import Email, EmailTable, UserEmailConfiguration, UserTable
from services.email.gmail import GmailService
from services.oauth.google import google_oauth_service


class EmailSyncService:
    """Service for synchronizing emails from external providers"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_user_emails(
        self,
        user_id: uuid.UUID,
        provider: str = "google",
        max_count: Optional[int] = None,
    ) -> dict:
        """
        Sync emails for a specific user from their configured provider

        Args:
            user_id: User ID to sync emails for
            provider: Email provider ('google' supported)
            max_count: Maximum emails to fetch (defaults to config setting)

        Returns:
            Dict with sync statistics
        """
        if max_count is None:
            max_count = settings.MAX_EMAILS_TO_FETCH

        # Get user with email configuration using eager loading (single query)
        stmt = (
            select(UserTable)
            .options(
                selectinload(
                    UserTable.email_configurations.and_(
                        UserEmailConfiguration.provider == provider
                    )
                )
            )
            .where(UserTable.id == user_id)
        )

        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get config from the already loaded relationship
        config = next(
            (c for c in user.email_configurations if c.provider == provider), None
        )
        if not config:
            raise ValueError(f"No {provider} configuration found for user {user_id}")

        # Get fresh access token
        access_token = await self._get_fresh_access_token(config)
        if not access_token:
            raise ValueError(f"Could not obtain valid access token for user {user_id}")

        # Fetch emails from provider
        emails = await self._fetch_emails_from_provider(
            provider, access_token, max_count, user.email
        )

        # Save new emails to database
        saved_count = await self._save_emails(emails, user_id)

        return {
            "user_id": user_id,
            "provider": provider,
            "fetched_count": len(emails),
            "saved_count": saved_count,
            "max_requested": max_count,
            "sync_timestamp": datetime.now(timezone.utc),
        }

    async def _get_fresh_access_token(
        self, config: UserEmailConfiguration
    ) -> Optional[str]:
        """Get a fresh access token, refreshing if necessary"""
        try:
            # Use the OAuth service to handle token refresh
            if config.provider == "google":
                tokens = google_oauth_service.decrypt_tokens(
                    config.access_token_encrypted, config.refresh_token_encrypted
                )

                # Check if token needs refresh
                if config.token_expires_at and config.token_expires_at <= datetime.now(
                    timezone.utc
                ):
                    # Token expired, try to refresh
                    refreshed_tokens = await google_oauth_service.refresh_access_token(
                        tokens["refresh_token"]
                    )
                    if refreshed_tokens:
                        # Update the config with new tokens
                        await google_oauth_service.save_user_tokens(
                            self.db, str(config.user_id), refreshed_tokens
                        )
                        return refreshed_tokens["access_token"]
                    return None
                else:
                    return tokens["access_token"]
        except Exception as e:
            print(f"Error getting fresh access token: {e}")
            return None

    async def _fetch_emails_from_provider(
        self, provider: str, access_token: str, max_count: int, user_email: str
    ) -> list[Email]:
        """Fetch emails from the specified provider"""
        match provider:
            case "google":
                gmail_service = GmailService(access_token)
                return await gmail_service.fetch_recent_emails(max_count, user_email)
            case _:
                raise NotImplementedError(f"Email provider '{provider}' not supported")

    async def _save_emails(self, emails: list[Email], user_id: uuid.UUID) -> int:
        """
        Save emails to database using bulk UPSERT, avoiding duplicates efficiently

        Returns:
            Number of emails actually saved (new emails only)
        """
        if not emails:
            return 0

        # Process emails in batches to avoid memory issues with large datasets
        batch_size = 1000
        total_saved = 0

        for i in range(0, len(emails), batch_size):
            batch = emails[i : i + batch_size]
            batch_saved = await self._save_email_batch(batch, user_id)
            total_saved += batch_saved

        return total_saved

    async def _save_email_batch(self, emails: list[Email], user_id: uuid.UUID) -> int:
        """
        Save a batch of emails using PostgreSQL UPSERT for optimal performance

        Returns:
            Number of emails actually saved (new emails only)
        """
        # Convert Email objects to dict format for bulk operations
        email_data = [
            {
                "message_id": email.id,
                "provider": email.provider,
                "sender": email.sender,
                "recipient": email.recipient,
                "recipients_cc": email.recipients_cc or [],
                "recipients_bcc": email.recipients_bcc or [],
                "subject": email.subject,
                "body_text": email.body_text,
                "body_html": email.body_html,
                "received_at": email.received_at,
                "headers": email.headers or {},
                "attachments": email.attachments or [],
                "raw_data": email.raw_data or {},
                "user_id": user_id,
            }
            for email in emails
        ]

        try:
            # PostgreSQL UPSERT: insert new records, ignore conflicts on unique constraint
            stmt = insert(EmailTable).values(email_data)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["message_id", "provider"]
            ).returning(EmailTable.id)

            result = await self.db.execute(stmt)
            await self.db.commit()

            # Count the number of rows actually inserted by counting returned IDs
            inserted_rows = result.fetchall()
            return len(inserted_rows)

        except Exception as e:
            await self.db.rollback()
            print(f"Error during bulk email save: {e}")
            # Fallback to individual saves if bulk operation fails
            return await self._save_emails_individually(emails, user_id)

    async def _save_emails_individually(
        self, emails: list[Email], user_id: uuid.UUID
    ) -> int:
        """
        Fallback method: save emails one by one if bulk operation fails
        """
        saved_count = 0

        for email in emails:
            try:
                email_record = EmailTable(
                    message_id=email.id,
                    provider=email.provider,
                    sender=email.sender,
                    recipient=email.recipient,
                    recipients_cc=email.recipients_cc or [],
                    recipients_bcc=email.recipients_bcc or [],
                    subject=email.subject,
                    body_text=email.body_text,
                    body_html=email.body_html,
                    received_at=email.received_at,
                    headers=email.headers or {},
                    attachments=email.attachments or [],
                    raw_data=email.raw_data or {},
                    user_id=user_id,
                )

                self.db.add(email_record)
                await self.db.commit()
                saved_count += 1

            except Exception:
                # Skip duplicate emails or other individual failures
                await self.db.rollback()
                continue

        return saved_count
