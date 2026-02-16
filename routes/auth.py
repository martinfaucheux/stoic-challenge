import logging
import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import User, UserCreate, UserTable
from services.auth import (
    Token,
    create_access_token,
    verify_oauth_state_token,
)
from services.database import get_db
from services.oauth.google import google_oauth_service
from services.user import authenticate_user, create_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register")
async def register_user(
    user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    create a new user
    """
    user_obj = await create_user(db, user)
    return User(id=user_obj.id, email=user_obj.email)


@router.post("/token")
async def login_for_access_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Login endpoint to get JWT access token"""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/auth/callback/google")
async def google_oauth_callback(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str | None = None,
    error: str | None = None,
    state: str | None = None,
):
    """
    Handle Google OAuth callback

    This endpoint receives the authorization code from Google after user consent
    and exchanges it for access and refresh tokens.
    """
    # Handle OAuth errors
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"OAuth error: {error}"
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided",
        )

    try:
        # Verify state parameter and get user ID
        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State parameter is required for security",
            )

        user_id = verify_oauth_state_token(state)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state parameter",
            )

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID in state parameter",
            )

        query = select(UserTable).where(UserTable.id == user_uuid)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Exchange code for tokens
        token_response = await google_oauth_service.exchange_code_for_tokens(code)

        # Get user info from Google
        user_info = await google_oauth_service.get_user_info(
            token_response["access_token"]
        )

        # Save the token configuration to the database
        await google_oauth_service.save_user_configuration(
            db=db,
            user_id=user_uuid,
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token"),
            expires_in=token_response.get("expires_in"),
            token_type=token_response.get("token_type", "Bearer"),
        )

        return {
            "status": "success",
            "message": "Google account connected successfully",
            "user_email": user_info.get("email"),
            "google_email": user_info.get("email"),
            "redirect_url": f"{settings.BASE_URL}/dashboard",  # Frontend dashboard URL
        }

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error processing Google OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process OAuth callback",
        )
