from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import EmailTable, UserEmailConfiguration, UserTable
from schemas import (
    EmailConfigurationResponse,
    EmailConfigurationsListResponse,
    EmailListResponse,
    EmailResponse,
    EmailSyncResponse,
    GoogleAuthUrlResponse,
    SyncResult,
)
from services.auth import create_oauth_state_token, get_current_user
from services.database import get_db
from services.email_sync import EmailSyncService
from services.oauth.google import google_oauth_service

router = APIRouter()


@router.get("/emails", response_model=EmailListResponse)
async def get_emails(
    current_user: Annotated[UserTable, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(
        default=50, le=500, description="Maximum number of emails to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of emails to skip"),
    provider: Optional[str] = Query(default=None, description="Filter by provider"),
    sender: Optional[str] = Query(default=None, description="Filter by sender email"),
):
    """
    Retrieve user's emails with optional filtering and pagination

    Returns a paginated list of emails stored in the database with optional filtering
    by email provider and sender address. Body text is truncated to 500 characters.

    **Query Parameters:**
    - `limit`: Maximum number of emails to return (default: 50, max: 500)
    - `offset`: Number of emails to skip for pagination (default: 0)
    - `provider`: Optional provider filter (e.g., 'google', 'microsoft')
    - `sender`: Optional sender email filter (case-insensitive substring match)

    **Response:**
    - `emails`: Array of email objects with basic metadata
    - `count`: Number of emails in this response
    - `offset` and `limit`: Pagination parameters used in the request
    """
    try:
        # Build query for user's emails only
        stmt = select(EmailTable).where(EmailTable.user_id == current_user.id)

        # Apply optional filters
        if provider:
            stmt = stmt.where(EmailTable.provider == provider)
        if sender:
            stmt = stmt.where(EmailTable.sender.ilike(f"%{sender}%"))

        # Order by received_at descending (most recent first)
        stmt = stmt.order_by(EmailTable.received_at.desc())

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

        result = await db.execute(stmt)
        emails = result.scalars().all()

        # Convert to response format
        return EmailListResponse(
            emails=[
                EmailResponse(
                    id=str(email.id),
                    message_id=email.message_id,
                    provider=email.provider,
                    sender=email.sender,
                    recipient=email.recipient,
                    subject=email.subject,
                    body_text=email.body_text[:500] + "..."
                    if len(email.body_text) > 500
                    else email.body_text,
                    received_at=email.received_at,
                    created_at=email.created_at,
                )
                for email in emails
            ],
            count=len(emails),
            offset=offset,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve emails: {str(e)}",
        )


@router.post("/emails/sync", response_model=EmailSyncResponse)
async def sync_emails(
    current_user: Annotated[UserTable, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    provider: str = Query(default="google", description="Email provider to sync"),
    max_count: Optional[int] = Query(
        default=None, le=500, description="Max emails to fetch"
    ),
):
    """
    Sync emails for the authenticated user

    Triggers the email synchronization process for the authenticated user.
    Checks for configured email providers and fetches new emails from those providers.

    **Query Parameters:**
    - `provider`: Email provider to sync (default: 'google', options: 'google', 'microsoft')
    - `max_count`: Maximum number of emails to fetch in this sync (optional, max: 500)

    **Response:**
    - `message`: Status message indicating sync completion
    - `sync_result`: Object containing sync statistics (synced_count, new_count, error_count)
    """
    try:
        # Initialize email sync service
        email_sync_service = EmailSyncService(db)

        # Sync emails for the user
        result = await email_sync_service.sync_user_emails(
            user_id=current_user.id, provider=provider, max_count=max_count
        )

        return EmailSyncResponse(
            message=f"Email sync completed for {provider}",
            sync_result=SyncResult(**result) if isinstance(result, dict) else result,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync emails: {str(e)}",
        )


@router.post("/email-configuration/google", response_model=GoogleAuthUrlResponse)
async def configure_google_email(
    current_user: Annotated[UserTable, Depends(get_current_user)],
):
    """
    Initiate Google OAuth flow for email configuration

    Starts the OAuth process by generating a redirect URL to Google's consent screen.
    After user authorization, they will be redirected back to the callback endpoint.

    **Response:**
    - `authorization_url`: URL to redirect user to for OAuth consent
    - `message`: Instructions for the user to complete the authorization flow
    """

    try:
        # Create secure state token with user ID
        state_token = create_oauth_state_token(str(current_user.id))

        # Generate OAuth authorization URL with state
        auth_url = google_oauth_service.generate_authorization_url(state=state_token)

        return GoogleAuthUrlResponse(
            authorization_url=auth_url,
            message="Please visit the authorization URL to connect your Google account",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth: {str(e)}",
        )


@router.get("/email-configuration", response_model=EmailConfigurationsListResponse)
async def get_email_configurations(
    current_user: Annotated[UserTable, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get user's email provider configurations

    Returns the list of configured email providers for the authenticated user.
    Sensitive token information (access tokens, refresh tokens) are not exposed.

    **Response:**
    - `configurations`: Array of configured email providers with token validity info
      - `provider`: Email provider name
      - `token_expires_at`: When the access token expires (null if no expiration)
      - `is_token_valid`: Whether the token is currently valid
    """

    stmt = select(UserEmailConfiguration).where(
        UserEmailConfiguration.user_id == current_user.id
    )
    result = await db.execute(stmt)
    configurations = result.scalars().all()

    return EmailConfigurationsListResponse(
        configurations=[
            EmailConfigurationResponse(
                provider=config.provider,
                token_expires_at=config.token_expires_at,
                is_token_valid=(
                    config.token_expires_at is None
                    or config.token_expires_at > datetime.now(timezone.utc)
                )
                if config.token_expires_at
                else None,
            )
            for config in configurations
        ]
    )
