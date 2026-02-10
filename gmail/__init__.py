"""Gmail integration module for email security tool.

This module provides functionality to authenticate with Gmail API,
fetch messages, and parse them into the common Email format.
"""

from gmail.auth import get_gmail_service
from gmail.parser import parse_gmail_message
from gmail.service import fetch_gmail_message_by_id, fetch_gmail_messages

__all__ = [
    "get_gmail_service",
    "parse_gmail_message",
    "fetch_gmail_messages",
    "fetch_gmail_message_by_id",
]
