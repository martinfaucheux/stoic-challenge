import logging
import os

from fastapi import FastAPI

from routes import auth_router, email_router

# Configure logging
log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)

app = FastAPI(title="Email Security Tool")

# Include routers
app.include_router(auth_router, tags=["auth"])
app.include_router(email_router, tags=["email"])
