from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
