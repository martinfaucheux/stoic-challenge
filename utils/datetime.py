import email
import email.utils
from datetime import datetime, timezone


def parse_datetime(date_str: str) -> datetime:
    """Parse email date string"""
    if not date_str:
        return datetime.now(timezone.utc)

    # Try different parsing strategies
    try:
        # Try ISO format first (e.g., "2024-01-15T10:30:00Z")
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass

    try:
        # Try Unix timestamp (string or numeric)
        timestamp = float(date_str)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    try:
        # Try email date format (RFC 2822: "Mon, 15 Jan 2024 10:30:00 +0000")
        return email.utils.parsedate_to_datetime(date_str)
    except (ValueError, TypeError, AttributeError):
        pass

    try:
        # Try common datetime formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Assume UTC if no timezone info
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    except Exception:
        pass

    # TODO: add warning
    return datetime.now(timezone.utc)
