from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

app = FastAPI(title="Email Security Tool")


@app.get("/")
async def root():
    return {"message": "Email Security Tool API"}


@app.get("/emails")
async def get_emails(db: AsyncSession = Depends(get_db)):
    """Get all emails from the database"""
    # TODO: Implement email retrieval
    return {"emails": []}


@app.post("/webhook")
async def receive_webhook(db: AsyncSession = Depends(get_db)):
    """Receive email data from Google Workspace and Microsoft O365"""
    # TODO: Implement webhook handling
    return {"status": "received"}
