from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Email:
    """Common internal email structure for all providers"""

    id: str  # Unique identifier (provider_id)
    provider: str  # 'google' or 'microsoft'
    sender: str  # Email address
    recipient: str  # Email address
    recipients_cc: List[str]  # CC'd addresses
    recipients_bcc: List[str]  # BCC'd addresses
    subject: str
    body: str  # Plain text or HTML
    body_html: Optional[str]  # HTML version if available
    received_at: datetime
    headers: dict  # Raw headers for additional validation
    attachments: List[dict]  # List of attachment metadata
    raw_data: dict  # Original provider-specific data for debugging
