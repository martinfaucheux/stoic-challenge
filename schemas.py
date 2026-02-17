"""Response schemas for API endpoints"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EmailResponse(BaseModel):
    """Individual email response schema"""

    id: str = Field(..., description="Unique identifier (UUID)")
    message_id: str = Field(..., description="Provider-specific message ID")
    provider: str = Field(..., description="Email provider (google, microsoft)")
    sender: str = Field(..., description="Sender email address")
    recipient: str = Field(..., description="Primary recipient email address")
    subject: str = Field(..., description="Email subject")
    body_text: str = Field(
        ..., description="Plain text body (truncated to 500 chars if longer)"
    )
    received_at: datetime = Field(..., description="When the email was received")
    created_at: datetime = Field(
        ..., description="When the email was stored in the database"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmailListResponse(BaseModel):
    """List of emails with pagination info"""

    emails: list[EmailResponse] = Field(..., description="List of emails")
    count: int = Field(..., description="Number of emails returned in this response")
    offset: int = Field(..., description="Offset used for pagination")
    limit: int = Field(..., description="Limit used for pagination")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SyncResult(BaseModel):
    """Email sync result details"""

    synced_count: int = Field(..., description="Number of emails synced")
    new_count: int = Field(..., description="Number of new emails added")
    error_count: int = Field(default=0, description="Number of errors during sync")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmailSyncResponse(BaseModel):
    """Response from email sync endpoint"""

    message: str = Field(..., description="Status message")
    sync_result: SyncResult = Field(..., description="Sync operation details")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class GoogleAuthUrlResponse(BaseModel):
    """Response containing Google OAuth authorization URL"""

    authorization_url: str = Field(
        ..., description="URL to redirect user to for OAuth consent"
    )
    message: str = Field(..., description="Instructions for the user")


class EmailConfigurationResponse(BaseModel):
    """Individual email configuration response"""

    provider: str = Field(..., description="Email provider (google, microsoft)")
    token_expires_at: Optional[datetime] = Field(
        None, description="When the access token expires (null if no expiration)"
    )
    is_token_valid: Optional[bool] = Field(
        None, description="Whether the token is currently valid"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmailConfigurationsListResponse(BaseModel):
    """List of user's email configurations"""

    configurations: list[EmailConfigurationResponse] = Field(
        ..., description="User's configured email providers"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
