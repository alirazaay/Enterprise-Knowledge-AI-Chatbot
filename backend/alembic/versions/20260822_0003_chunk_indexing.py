"""Add indexing lifecycle and chunk metadata."""

from alembic import op
import sqlalchemy as sa


revision = "20260822_0003"
down_revision = "20260821_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'indexing'")
    op.add_column("documents", sa.Column("indexing_error", sa.Text(), nullable=True))
    op.add_column("document_chunks", sa.Column("word_count", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("source_sequence_start", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("source_sequence_end", sa.Integer(), nullable=True))
    op.execute("UPDATE document_chunks SET word_count = cardinality(regexp_split_to_array(trim(content), '\\s+'))")
    op.execute("UPDATE document_chunks SET source_sequence_start = 0, source_sequence_end = 0")
    op.alter_column("document_chunks", "word_count", nullable=False)
    op.alter_column("document_chunks", "source_sequence_start", nullable=False)
    op.alter_column("document_chunks", "source_sequence_end", nullable=False)
    op.create_check_constraint("ck_document_chunks_word_count_positive", "document_chunks", "word_count > 0")
    op.create_check_constraint("ck_document_chunks_source_order", "document_chunks", "source_sequence_end >= source_sequence_start")


def downgrade() -> None:
    op.drop_constraint("ck_document_chunks_source_order", "document_chunks", type_="check")
    op.drop_constraint("ck_document_chunks_word_count_positive", "document_chunks", type_="check")
    op.drop_column("document_chunks", "source_sequence_end")
    op.drop_column("document_chunks", "source_sequence_start")
    op.drop_column("document_chunks", "word_count")
    op.drop_column("documents", "indexing_error")
    op.execute("ALTER TYPE document_status RENAME TO document_status_old")
    op.execute("CREATE TYPE document_status AS ENUM ('uploaded', 'processing', 'processed', 'indexed', 'failed')")
    op.execute("ALTER TABLE documents ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE documents ALTER COLUMN status TYPE document_status USING status::text::document_status")
    op.execute("DROP TYPE document_status_old")
    op.execute("ALTER TABLE documents ALTER COLUMN status SET DEFAULT 'uploaded'")
