"""initial: flags + monitored_addresses

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "flags",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tx_hash", sa.String(66), nullable=False),
        sa.Column("monitored_address", sa.String(42), nullable=False),
        sa.Column("rule_id", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("reason_human", sa.String(280), nullable=False),
        sa.Column(
            "reason_structured",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("ts_ms", sa.BigInteger, nullable=False),
        sa.Column("sig", sa.String(132), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_flags_monitored_address", "flags", ["monitored_address"])
    op.create_index("ix_flags_tx_hash", "flags", ["tx_hash"])
    op.create_index("ix_flags_ts_ms", "flags", ["ts_ms"])
    op.create_index(
        "ix_flags_monitored_address_ts_ms",
        "flags",
        ["monitored_address", "ts_ms"],
    )
    op.create_index("ix_flags_rule_id", "flags", ["rule_id"])

    op.create_table(
        "monitored_addresses",
        sa.Column("address", sa.String(42), primary_key=True),
        sa.Column("label", sa.String(128), nullable=True),
        sa.Column(
            "active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "address ~ '^0x[0-9a-f]{40}$'",
            name="ck_monitored_addresses_address_format",
        ),
    )
    op.create_index(
        "ix_monitored_addresses_active", "monitored_addresses", ["active"]
    )


def downgrade() -> None:
    op.drop_index("ix_monitored_addresses_active", table_name="monitored_addresses")
    op.drop_table("monitored_addresses")
    op.drop_index("ix_flags_rule_id", table_name="flags")
    op.drop_index("ix_flags_monitored_address_ts_ms", table_name="flags")
    op.drop_index("ix_flags_ts_ms", table_name="flags")
    op.drop_index("ix_flags_tx_hash", table_name="flags")
    op.drop_index("ix_flags_monitored_address", table_name="flags")
    op.drop_table("flags")
