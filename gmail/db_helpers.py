"""Database helpers for Gmail fetching."""

from typing import List

from sqlalchemy.dialects.postgresql import insert

from database import AsyncSessionLocal, init_db
from models import Email, EmailTable


async def save_emails_to_db(emails: List[Email]) -> int:
    """Save emails to the database, ignoring duplicates."""
    if not emails:
        return 0

    await init_db()

    rows = []
    for email in emails:
        rows.append(
            {
                "message_id": email.id,
                "provider": email.provider,
                "sender": email.sender,
                "recipient": email.recipient,
                "recipients_cc": email.recipients_cc,
                "recipients_bcc": email.recipients_bcc,
                "subject": email.subject,
                "body_text": email.body,
                "body_html": email.body_html,
                "received_at": email.received_at,
                "headers": email.headers,
                "attachments": email.attachments,
                "raw_data": email.raw_data,
            }
        )

    async with AsyncSessionLocal() as session:
        stmt = insert(EmailTable).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["message_id", "provider"]
        ).returning(EmailTable.id)
        result = await session.execute(stmt)
        inserted_ids = result.scalars().all()
        await session.commit()

    return len(inserted_ids)
