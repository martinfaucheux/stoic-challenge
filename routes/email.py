from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import create_oauth_state_token, get_current_user
from database import get_db
from models import EmailTable, UserEmailConfiguration, UserTable
from services.oauth.google import google_oauth_service

router = APIRouter()


@router.get("/emails")
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
    """Get user's emails from the database with optional filtering and pagination"""
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
        return {
            # TODO: work on a common pagination format
            "emails": [
                {
                    "id": str(email.id),
                    "message_id": email.message_id,
                    "provider": email.provider,
                    "sender": email.sender,
                    "recipient": email.recipient,
                    "subject": email.subject,
                    "body_text": email.body_text[:500] + "..."
                    if len(email.body_text) > 500
                    else email.body_text,
                    "received_at": email.received_at,
                    "created_at": email.created_at,
                }
                for email in emails
            ],
            "count": len(emails),
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve emails: {str(e)}",
        )


@router.post("/email-configuration/google")
async def configure_google_email(
    current_user: Annotated[UserTable, Depends(get_current_user)],
):
    """
    Initiate Google OAuth flow for email configuration

    This endpoint starts the OAuth process by redirecting the user to Google's
    consent screen. After user authorization, they will be redirected back to
    the callback endpoint.
    """

    try:
        # Create secure state token with user ID
        state_token = create_oauth_state_token(str(current_user.id))

        # Generate OAuth authorization URL with state
        auth_url = google_oauth_service.generate_authorization_url(state=state_token)

        return {
            "authorization_url": auth_url,
            "message": "Please visit the authorization URL to connect your Google account",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth: {str(e)}",
        )


@router.get("/email-configuration")
async def get_email_configurations(
    current_user: Annotated[UserTable, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get user's email provider configurations

    Returns the list of configured email providers for the authenticated user,
    without exposing sensitive token information.
    """

    stmt = select(UserEmailConfiguration).where(
        UserEmailConfiguration.user_id == current_user.id
    )
    result = await db.execute(stmt)
    configurations = result.scalars().all()

    return {
        "configurations": [
            {
                "provider": config.provider,
                "configured_at": config.created_at,
                "token_expires_at": config.token_expires_at,
                "is_token_valid": (
                    config.token_expires_at is None
                    or config.token_expires_at > datetime.utcnow()
                )
                if config.token_expires_at
                else None,
            }
            for config in configurations
        ]
    }


@router.post("/webhook")
async def receive_webhook(db: Annotated[AsyncSession, Depends(get_db)]):
    """Receive email data from Google Workspace and Microsoft O365"""
    # TODO: Implement webhook handling
    return {"status": "received"}
