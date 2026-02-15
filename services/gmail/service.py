"""Gmail service - fetch messages from Gmail API"""

from typing import List, Optional

from config import settings
from .auth import get_gmail_service
from .parser import parse_gmail_message
from models import Email


def fetch_gmail_messages(
    max_results: int | None = None,
    query: str = "in:inbox",
    user_id: str = "me",
) -> List[Email]:
    """
    Fetch messages from Gmail and convert to Email objects.

    Args:
        max_results: Maximum number of messages to fetch (default from settings)
        query: Gmail search query (default: 'in:inbox')
               Examples:
               - 'in:inbox' - inbox messages only
               - 'after:2026/02/01' - messages after specific date
               - 'from:example@gmail.com' - messages from specific sender
               - 'is:unread' - unread messages only
        user_id: Gmail user ID (default: 'me' for authenticated user)

    Returns:
        List of Email objects
    """
    if max_results is None:
        max_results = settings.MAX_EMAILS_TO_FETCH

    # Get authenticated Gmail service
    service = get_gmail_service()

    # Fetch message IDs
    results = (
        service.users()
        .messages()
        .list(userId=user_id, q=query, maxResults=max_results)
        .execute()
    )

    messages_data = results.get("messages", [])

    if not messages_data:
        print(f"No messages found matching query: {query}")
        return []

    print(f"Found {len(messages_data)} messages. Fetching details...")

    # Fetch full message details and parse
    emails = []
    for i, msg_data in enumerate(messages_data, 1):
        try:
            # Fetch full message with format='full' to get parsed MIME
            message = (
                service.users()
                .messages()
                .get(userId=user_id, id=msg_data["id"], format="full")
                .execute()
            )

            # Parse to Email object
            email = parse_gmail_message(message)
            emails.append(email)

            print(f"  [{i}/{len(messages_data)}] Parsed: {email.subject[:50]}")

        except Exception as e:
            print(
                f"  [{i}/{len(messages_data)}] Error parsing message {msg_data['id']}: {e}"
            )
            continue

    print(f"\nSuccessfully fetched and parsed {len(emails)} emails")
    return emails


def fetch_gmail_message_by_id(message_id: str, user_id: str = "me") -> Optional[Email]:
    """
    Fetch a single message by ID.

    Args:
        message_id: Gmail message ID
        user_id: Gmail user ID (default: 'me')

    Returns:
        Email object or None if not found
    """
    service = get_gmail_service()

    try:
        message = (
            service.users()
            .messages()
            .get(userId=user_id, id=message_id, format="full")
            .execute()
        )
        return parse_gmail_message(message)
    except Exception as e:
        print(f"Error fetching message {message_id}: {e}")
        return None
