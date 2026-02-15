"""Gmail message parser - converts Gmail API response to Email dataclass"""

import base64
from datetime import datetime
from typing import Dict, List, Optional

from models import Email


def decode_base64url(data: str) -> str:
    """Decode base64url encoded string"""
    # Add padding if needed
    padding = 4 - len(data) % 4
    if padding:
        data += "=" * padding
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")


def get_header_value(headers: List[Dict], name: str) -> Optional[str]:
    """Extract header value by name from Gmail headers list"""
    for header in headers:
        if header["name"].lower() == name.lower():
            return header["value"]
    return None


def parse_email_addresses(address_string: Optional[str]) -> List[str]:
    """Parse comma-separated email addresses"""
    if not address_string:
        return []
    # Simple parsing - can be enhanced with email.utils.parseaddr for complex cases
    addresses = [addr.strip() for addr in address_string.split(",")]
    return [addr for addr in addresses if addr]


def extract_body_from_parts(parts: List[Dict], mime_type: str = "text/plain") -> str:
    """
    Recursively extract body content from message parts.

    Args:
        parts: List of message parts from Gmail API
        mime_type: MIME type to extract (text/plain or text/html)

    Returns:
        Decoded body content
    """
    body = ""

    for part in parts:
        part_mime_type = part.get("mimeType", "")

        # If this part matches our desired mime type
        if part_mime_type == mime_type:
            if "data" in part.get("body", {}):
                body += decode_base64url(part["body"]["data"])

        # If this part has nested parts, recurse
        if "parts" in part:
            body += extract_body_from_parts(part["parts"], mime_type)

    return body


def extract_attachments(parts: List[Dict]) -> List[Dict]:
    """
    Extract attachment metadata from message parts.

    Returns:
        List of attachment dictionaries with filename, mimeType, and size
    """
    attachments = []

    for part in parts:
        filename = part.get("filename")
        if filename:  # This part has a filename, likely an attachment
            attachments.append(
                {
                    "filename": filename,
                    "mimeType": part.get("mimeType"),
                    "size": part.get("body", {}).get("size", 0),
                    "attachmentId": part.get("body", {}).get("attachmentId"),
                }
            )

        # Recurse into nested parts
        if "parts" in part:
            attachments.extend(extract_attachments(part["parts"]))

    return attachments


def parse_gmail_message(message: Dict) -> Email:
    """
    Convert Gmail API message to Email dataclass.

    Args:
        message: Full message from Gmail API (format='full')

    Returns:
        Email dataclass instance
    """
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    # Extract headers
    sender = get_header_value(headers, "From") or ""
    recipient = get_header_value(headers, "To") or ""
    cc = get_header_value(headers, "Cc")
    bcc = get_header_value(headers, "Bcc")
    subject = get_header_value(headers, "Subject") or "(No Subject)"

    # Parse recipient lists
    recipients_cc = parse_email_addresses(cc)
    recipients_bcc = parse_email_addresses(bcc)

    # Extract body
    parts = payload.get("parts", [])

    # If no parts, check if body is directly in payload
    if not parts and "body" in payload and "data" in payload["body"]:
        body = decode_base64url(payload["body"]["data"])
        body_html = None
    else:
        # Extract plain text and HTML versions
        body = extract_body_from_parts(parts, "text/plain")
        body_html = extract_body_from_parts(parts, "text/html")

        # If no plain text but HTML exists, use HTML as body
        if not body and body_html:
            body = body_html
            body_html = None

    # Extract attachments
    attachments = extract_attachments(parts) if parts else []

    # Convert timestamp (milliseconds since epoch)
    internal_date = int(message.get("internalDate", 0))
    received_at = datetime.fromtimestamp(internal_date / 1000)

    # Convert headers list to dict for easier access
    headers_dict = {header["name"]: header["value"] for header in headers}

    return Email(
        id=message["id"],
        provider="google",
        sender=sender,
        recipient=recipient,
        recipients_cc=recipients_cc,
        recipients_bcc=recipients_bcc,
        subject=subject,
        body=body,
        body_html=body_html,
        received_at=received_at,
        headers=headers_dict,
        attachments=attachments,
        raw_data=message,  # Store entire message for debugging
    )
