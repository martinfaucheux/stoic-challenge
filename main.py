from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from auth import Token, create_access_token, get_current_user
from config import settings
from database import get_db
from models import User, UserCreate, UserTable
from services.oauth.google import google_oauth_service
from services.user import authenticate_user, create_user

app = FastAPI(title="Email Security Tool")


@app.post("/register")
async def register_user(
    user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    """
    create a new user
    """
    user_obj = await create_user(db, user)
    return User(id=user_obj.id, email=user_obj.email)


@app.post("/token")
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


@app.get("/")
async def root():
    return {"message": "Email Security Tool API"}


@app.get("/emails")
async def get_emails(db: Annotated[AsyncSession, Depends(get_db)]):
    """Get all emails from the database"""
    # TODO: Implement email retrieval
    return {"emails": []}


@app.get("/protected")
async def protected_route(
    current_user: Annotated[UserTable, Depends(get_current_user)],
):
    """Example protected route that requires authentication"""
    return {"message": f"Hello, {current_user.email}! This is a protected route."}


@app.post("/email-configuration/google")
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
        # Generate OAuth authorization URL
        auth_url = google_oauth_service.generate_authorization_url()

        return {
            "authorization_url": auth_url,
            "message": "Please visit the authorization URL to connect your Google account",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth: {str(e)}",
        )


@app.get("/auth/callback/google")
async def google_oauth_callback(
    request: Request,
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
        # Exchange code for tokens
        token_response = await google_oauth_service.exchange_code_for_tokens(code)

        # Get user info from Google
        user_info = await google_oauth_service.get_user_info(
            token_response["access_token"]
        )

        # TODO: save the token to the UserEmailConfiguration for the current user

        return {
            "status": "success",
            "message": "Google account connected successfully",
            "user_email": user_info.get("email"),
            "redirect_url": f"{settings.BASE_URL}/dashboard",  # Frontend dashboard URL
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process OAuth callback: {str(e)}",
        )


@app.get("/email-configuration")
async def get_email_configurations(
    current_user: Annotated[UserTable, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get user's email provider configurations

    Returns the list of configured email providers for the authenticated user,
    without exposing sensitive token information.
    """
    from sqlalchemy import select

    from models import UserEmailConfiguration

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


@app.post("/webhook")
async def receive_webhook(db: Annotated[AsyncSession, Depends(get_db)]):
    """Receive email data from Google Workspace and Microsoft O365"""
    # TODO: Implement webhook handling
    return {"status": "received"}
