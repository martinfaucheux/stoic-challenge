from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database import Base


class EmailTable(Base):
    """SQLAlchemy model for storing emails in database"""

    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Provider-specific message ID"
    )
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Email provider (google, microsoft)"
    )
    sender: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Sender email address"
    )
    recipient: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Primary recipient"
    )
    recipients_cc: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=list, comment="CC'd email addresses"
    )
    recipients_bcc: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=list, comment="BCC'd email addresses"
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Plain text body"
    )
    body_html: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="HTML body if available"
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When email was received",
    )
    headers: Mapped[Dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict, comment="Email headers for validation"
    )
    attachments: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, comment="Attachment metadata"
    )
    raw_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict, comment="Original provider data"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("message_id", "provider", name="uq_message_provider"),
        Index("ix_emails_sender", "sender"),
        Index("ix_emails_recipient", "recipient"),
        Index("ix_emails_received_at", "received_at"),
    )


class Email(BaseModel):
    """Common internal email structure for all providers"""

    id: str = Field(..., description="Unique identifier (provider_id)")
    provider: str = Field(..., description="'google' or 'microsoft'")
    sender: str = Field(..., description="Email address")
    recipient: str = Field(..., description="Email address")
    recipients_cc: List[str] = Field(default_factory=list, description="CC'd addresses")
    recipients_bcc: List[str] = Field(
        default_factory=list, description="BCC'd addresses"
    )
    subject: str
    body: str = Field(..., description="Plain text or HTML")
    body_html: Optional[str] = Field(None, description="HTML version if available")
    received_at: datetime
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Raw headers for additional validation"
    )
    attachments: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of attachment metadata"
    )
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Original provider-specific data for debugging",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class User(BaseModel):
    """User model for authentication"""

    id: Optional[int] = Field(None, description="User ID (database primary key)")
    email: str = Field(..., description="User email address")


class UserTable(Base):
    """SQLAlchemy model for storing users in database"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="User email address"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Password hash (bcrypt)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
    )
