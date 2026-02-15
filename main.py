from typing import Annotated

from fastapi import Depends, FastAPI

from auth import get_current_user
from models import UserTable
from routes import auth_router, email_router

app = FastAPI(title="Email Security Tool")

# Include routers
app.include_router(auth_router, tags=["auth"])
app.include_router(email_router, tags=["email"])


@app.get("/")
async def root():
    return {"message": "Email Security Tool API"}


@app.get("/protected")
async def protected_route(
    current_user: Annotated[UserTable, Depends(get_current_user)],
):
    """Example protected route that requires authentication"""
    return {"message": f"Hello, {current_user.email}! This is a protected route."}
