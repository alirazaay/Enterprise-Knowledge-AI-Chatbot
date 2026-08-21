"""Add document parsing lifecycle and extracted content storage.

Revision ID: 20260821_0002
Revises: 20260821_0001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260821_0002"
down_revision = "20260821_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'processed'")
    op.add_column("documents", sa.Column("processing_error", sa.Text(), nullable=True))
    op.create_table(
        "document_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "sequence_index", name="uq_document_pages_document_sequence"),
        sa.CheckConstraint("sequence_index >= 0", name="ck_document_pages_sequence_nonnegative"),
        sa.CheckConstraint("length(trim(content)) > 0", name="ck_document_pages_content_not_blank"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_document_pages_document_id", table_name="document_pages")
    op.drop_table("document_pages")
    op.drop_column("documents", "processing_error")

    # PostgreSQL enums cannot remove one value in place. Rebuild the prior enum
    # after mapping any Phase 5 rows to the prior uploaded state.
    op.execute("ALTER TABLE documents ALTER COLUMN status DROP DEFAULT")
    op.execute("UPDATE documents SET status = 'uploaded' WHERE status = 'processed'")
    op.execute("CREATE TYPE document_status_previous AS ENUM ('uploaded', 'processing', 'indexed', 'failed')")
    op.execute(
        "ALTER TABLE documents ALTER COLUMN status TYPE document_status_previous "
        "USING status::text::document_status_previous"
    )
    op.execute("DROP TYPE document_status")
    op.execute("ALTER TYPE document_status_previous RENAME TO document_status")
    op.execute("ALTER TABLE documents ALTER COLUMN status SET DEFAULT 'uploaded'::document_status")
