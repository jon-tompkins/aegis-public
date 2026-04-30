"""SQLAlchemy 2.0 declarative models for the agent's persistence layer.

Two tables:

- **`flags`** — one row per emitted attestation. Append-only; the `sig`
  column locks the payload so retroactive edits are detectable. Indexed on
  the three query axes we actually use (per-address history, per-tx
  lookup, time range) plus a composite for "recent flags for address"
  which is the primary UI query.

- **`monitored_addresses`** — soft-deletable record of addresses under
  watch. The `active` flag lets `DELETE /monitor/:address` deactivate
  without breaking historical joins on `flags.monitored_address`. Address
  format is enforced with a CHECK constraint so bad data can't land.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Note on typing: SQLAlchemy's Mapped[] resolver evaluates annotations at
# class-body time, which on Python < 3.10 can't parse PEP 604 `str | None`
# unions. We use `Optional[str]` here for Python 3.9 compatibility at the
# few nullable columns. Every other annotation can stay PEP-604 because
# those types are unambiguous and `from __future__ import annotations`
# stringifies them for runtime import.


class Base(DeclarativeBase):
    """Shared declarative base for all Aegis monitor tables."""


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    monitored_address: Mapped[str] = mapped_column(String(42), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    reason_human: Mapped[str] = mapped_column(String(280), nullable=False)
    reason_structured: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ts_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sig: Mapped[str] = mapped_column(String(132), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Append-only correction pointer. NULL on a fresh flag; set to the prior
    # flag id when this row supersedes an earlier attestation. The prior row
    # is never deleted — the chain is auditable.
    supersedes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Arweave audit trail. Populated asynchronously by the writer task; NULL
    # while the row is still in the outbox queue.
    arweave_tx_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    arweave_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_flags_monitored_address", "monitored_address"),
        Index("ix_flags_tx_hash", "tx_hash"),
        Index("ix_flags_ts_ms", "ts_ms"),
        Index("ix_flags_monitored_address_ts_ms", "monitored_address", "ts_ms"),
        Index("ix_flags_rule_id", "rule_id"),
        Index("ix_flags_supersedes", "supersedes"),
        # Partial index doubles as the outbox queue: pending Arweave uploads
        # only. The writer task pulls off this with FOR UPDATE SKIP LOCKED.
        Index(
            "ix_flags_arweave_pending",
            "id",
            postgresql_where=text("arweave_tx_id IS NULL"),
        ),
    )


class MonitoredAddress(Base):
    __tablename__ = "monitored_addresses"

    address: Mapped[str] = mapped_column(String(42), primary_key=True)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_monitored_addresses_active", "active"),
        CheckConstraint(
            "address ~ '^0x[0-9a-f]{40}$'",
            name="ck_monitored_addresses_address_format",
        ),
    )
