"""add_user_id_to_emails

Revision ID: 8aedd8a2fca8
Revises: 79796f2a86d2
Create Date: 2026-02-15 17:53:32.451276

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8aedd8a2fca8"
down_revision: Union[str, Sequence[str], None] = "79796f2a86d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id column to emails table
    op.add_column("emails", sa.Column("user_id", UUID(as_uuid=True), nullable=True))

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_emails_user_id", "emails", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )

    # Create index for user_id
    op.create_index("ix_emails_user_id", "emails", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index("ix_emails_user_id", "emails")

    # Drop foreign key constraint
    op.drop_constraint("fk_emails_user_id", "emails", type_="foreignkey")

    # Drop column
    op.drop_column("emails", "user_id")
