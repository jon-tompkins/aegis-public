"""arweave audit trail + supersedes correction pointer

Revision ID: 0002_arweave_supersedes
Revises: 0001_initial
Create Date: 2026-04-30

Additive only: every column is nullable, no defaults change. Safe to apply
on a running Phase 1a — existing rows backfill to NULL, the writer task
treats `arweave_tx_id IS NULL` as the outbox queue, and historical
attestations remain verifiable because the canonical body excludes
None-valued optional fields.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_arweave_supersedes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("flags", sa.Column("supersedes", sa.BigInteger, nullable=True))
    op.add_column("flags", sa.Column("arweave_tx_id", sa.String(64), nullable=True))
    op.add_column(
        "flags",
        sa.Column("arweave_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_flags_supersedes", "flags", ["supersedes"])

    # Partial index = outbox queue. Writer task selects off this with
    # FOR UPDATE SKIP LOCKED so concurrent workers don't double-upload.
    op.create_index(
        "ix_flags_arweave_pending",
        "flags",
        ["id"],
        postgresql_where=sa.text("arweave_tx_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_flags_arweave_pending", table_name="flags")
    op.drop_index("ix_flags_supersedes", table_name="flags")
    op.drop_column("flags", "arweave_confirmed_at")
    op.drop_column("flags", "arweave_tx_id")
    op.drop_column("flags", "supersedes")
