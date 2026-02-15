from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import User, UserCreate, UserTable

app = FastAPI(title="Email Security Tool")


password_hash = PasswordHash.recommended()

DUMMY_HASH = password_hash.hash("dummypassword")

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


async def get_user(db: AsyncSession, email: str) -> Optional[UserTable]:
    """Get user by email (wrapper for compatibility)"""
    result = await db.execute(select(UserTable).where(UserTable.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str):
    """Authenticate user with database lookup"""
    user = await get_user(db, username)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user


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


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Depends(oauth2_scheme)],
):
    """Get current authenticated user from JWT token"""
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

    user = await get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


async def create_user(db: AsyncSession, user: UserCreate) -> UserTable:
    """Create a new user in the database"""
    user_obj = UserTable(
        email=user.email,
        password_hash=get_password_hash(user.password),
    )
    try:
        db.add(user_obj)
        await db.commit()
        await db.refresh(user_obj)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )
    return user_obj


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


@app.post("/webhook")
async def receive_webhook(db: Annotated[AsyncSession, Depends(get_db)]):
    """Receive email data from Google Workspace and Microsoft O365"""
    # TODO: Implement webhook handling
    return {"status": "received"}
