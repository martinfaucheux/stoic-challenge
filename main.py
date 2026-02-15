from datetime import timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from auth import Token, create_access_token, get_current_user
from config import settings
from database import get_db
from models import User, UserCreate, UserTable
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


@app.post("/webhook")
async def receive_webhook(db: Annotated[AsyncSession, Depends(get_db)]):
    """Receive email data from Google Workspace and Microsoft O365"""
    # TODO: Implement webhook handling
    return {"status": "received"}
