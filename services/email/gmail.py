"""Gmail API service for fetching emails"""

import base64
import logging
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models import Email
from utils.datetime import parse_datetime

logger = logging.getLogger(__name__)


class GmailService:
    """Service for interacting with Gmail API"""

    def __init__(self, access_token: str):
        """Initialize Gmail service with OAuth access token"""
        self.access_token = access_token
        self.service = None

    def _get_service(self):
        """Get authenticated Gmail service"""
        if not self.service:
            credentials = Credentials(token=self.access_token)
            self.service = build("gmail", "v1", credentials=credentials)
        return self.service

    async def fetch_recent_emails(
        self, max_results: int = 100, user_email: str = ""
    ) -> list[Email]:
        """
        Fetch recent emails from Gmail

        Args:
            max_results: Maximum number of emails to fetch
            user_email: User's email address (for recipient field)

        Returns:
            list of Email objects
        """
        try:
            service = self._get_service()

            # Get list of message IDs
            results = (
                service.users()
                .messages()
                .list(userId="me", maxResults=max_results, labelIds=["INBOX"])
                .execute()
            )

            messages = results.get("messages", [])
            emails = []

            for message in messages:
                try:
                    email_data = await self._get_email_details(
                        service, message["id"], user_email
                    )
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.error(f"Error fetching email {message['id']}: {e}")
                    continue

            return emails

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            raise Exception(f"Failed to fetch emails: {error}")

    async def _get_email_details(
        self, service, message_id: str, user_email: str
    ) -> Optional[Email]:
        """Get detailed email information"""
        try:
            message = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            # Parse email headers
            headers = {}
            for header in message["payload"].get("headers", []):
                headers[header["name"].lower()] = header["value"]

            # Extract email parts
            sender = headers.get("from", "")
            recipient = headers.get("to", user_email)
            subject = headers.get("subject", "")
            date_str = headers.get("date", "")

            # Parse date
            received_at = parse_datetime(date_str)

            # Extract body
            body_text, body_html = self._extract_body(message["payload"])

            # Extract recipients
            recipients_cc = self._parse_recipients(headers.get("cc", ""))
            recipients_bcc = self._parse_recipients(headers.get("bcc", ""))

            return Email(
                id=message_id,
                provider="google",
                sender=sender,
                recipient=recipient,
                recipients_cc=recipients_cc,
                recipients_bcc=recipients_bcc,
                subject=subject,
                body=body_text or body_html or "",
                body_text=body_text or "",
                body_html=body_html,
                received_at=received_at,
                headers=headers,
                attachments=self._extract_attachments(message["payload"]),
                raw_data={"gmail_message": message},
            )

        except Exception as e:
            logger.error(f"Error parsing email {message_id}: {e}")
            return None

    def _extract_body(self, payload: dict) -> tuple[str, Optional[str]]:
        """Extract text and HTML body from email payload"""
        body_text = ""
        body_html = None

        def extract_parts(part):
            nonlocal body_text, body_html

            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    body_text = base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="ignore"
                    )

            elif part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    body_html = base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="ignore"
                    )

            # Handle multipart
            if "parts" in part:
                for subpart in part["parts"]:
                    extract_parts(subpart)

        extract_parts(payload)
        return body_text, body_html

    def _extract_attachments(self, payload: dict) -> list[dict]:
        """Extract attachment metadata"""
        attachments = []

        def find_attachments(part):
            if part.get("filename"):
                attachments.append(
                    {
                        "filename": part["filename"],
                        "mime_type": part.get("mimeType", ""),
                        "size": part.get("body", {}).get("size", 0),
                    }
                )

            if "parts" in part:
                for subpart in part["parts"]:
                    find_attachments(subpart)

        find_attachments(payload)
        return attachments

    def _parse_recipients(self, recipients_str: str) -> list[str]:
        """Parse comma-separated recipient list"""
        if not recipients_str:
            return []
        return [email.strip() for email in recipients_str.split(",")]
