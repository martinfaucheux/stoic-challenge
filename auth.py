from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db

# Global objects for auth
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


def verify_password(plain_password, hashed_password):
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    return password_hash.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ENCRYPTION_ALGORITHM
    )
    return encoded_jwt


def create_oauth_state_token(
    user_id: str, expires_delta: timedelta | None = None
) -> str:
    """Create a secure state token for OAuth flow with user ID"""
    to_encode = {"user_id": user_id}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=30
        )  # 30 min for OAuth flow
    to_encode.update({"exp": expire})  # type: ignore
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ENCRYPTION_ALGORITHM
    )
    return encoded_jwt


def verify_oauth_state_token(state_token: str) -> str | None:
    """Verify OAuth state token and return user ID"""
    try:
        payload = jwt.decode(
            state_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ENCRYPTION_ALGORITHM],
        )
        user_id: str = payload["user_id"]
        if user_id is None:
            return None
        return user_id
    except (InvalidTokenError, KeyError):
        return None


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    """Get current authenticated user from JWT token"""
    from services.user import get_user_by_email

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ENCRYPTION_ALGORITHM]
        )
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception

    if not isinstance(token_data.email, str):
        raise credentials_exception

    user = await get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user
