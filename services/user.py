from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserCreate, UserTable
from services.auth import get_password_hash, verify_password


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserTable]:
    """Get user by email from database"""
    result = await db.execute(select(UserTable).where(UserTable.email == email))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, username: str, password: str):
    """Authenticate user with database lookup"""
    user = await get_user_by_email(db, username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
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
