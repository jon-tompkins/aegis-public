"""Guard rails for the DB model definitions.

These tests don't touch a live database. They catch accidental breakage
of the wire-format-adjacent pieces: table names, column names, index
coverage, the CHECK constraint on addresses. If any of these flip, the
migration rewrite work is on whoever flipped them.
"""

from __future__ import annotations

from aegis_monitor.db.models import Base, Flag, MonitoredAddress

# -----------------------------------------------------------------------------
# Table identities
# -----------------------------------------------------------------------------


def test_table_names() -> None:
    assert Flag.__tablename__ == "flags"
    assert MonitoredAddress.__tablename__ == "monitored_addresses"


def test_both_tables_registered_on_metadata() -> None:
    assert "flags" in Base.metadata.tables
    assert "monitored_addresses" in Base.metadata.tables


# -----------------------------------------------------------------------------
# Flag columns
# -----------------------------------------------------------------------------


def test_flag_column_surface() -> None:
    expected = {
        "id",
        "tx_hash",
        "monitored_address",
        "rule_id",
        "rule_version",
        "severity",
        "reason_human",
        "reason_structured",
        "agent_id",
        "ts_ms",
        "sig",
        "created_at",
        # Append-only correction pointer (see arweave-flag-storage spec).
        "supersedes",
        # Arweave audit trail; populated async by the writer task.
        "arweave_tx_id",
        "arweave_confirmed_at",
    }
    actual = {c.name for c in Flag.__table__.columns}
    assert actual == expected


def test_flag_indexes_cover_query_axes() -> None:
    names = {ix.name for ix in Flag.__table__.indexes}
    # The three spec-mandated axes plus the composite for recent-flags-per-address
    # and per-rule lookups, plus the correction pointer and the partial outbox
    # index that the Arweave writer drains.
    assert {
        "ix_flags_monitored_address",
        "ix_flags_tx_hash",
        "ix_flags_ts_ms",
        "ix_flags_monitored_address_ts_ms",
        "ix_flags_rule_id",
        "ix_flags_supersedes",
        "ix_flags_arweave_pending",
    }.issubset(names)


def test_flag_non_null_fields() -> None:
    nullable_names = {c.name for c in Flag.__table__.columns if c.nullable}
    # supersedes + the two arweave columns are nullable by design — they're
    # populated post-insert (correction emit / writer task).
    assert nullable_names == {"supersedes", "arweave_tx_id", "arweave_confirmed_at"}


# -----------------------------------------------------------------------------
# MonitoredAddress columns
# -----------------------------------------------------------------------------


def test_monitored_address_column_surface() -> None:
    expected = {"address", "label", "active", "added_at", "removed_at"}
    actual = {c.name for c in MonitoredAddress.__table__.columns}
    assert actual == expected


def test_monitored_address_primary_key_is_address() -> None:
    pk = [c.name for c in MonitoredAddress.__table__.primary_key]
    assert pk == ["address"]


def test_monitored_address_has_format_check() -> None:
    # The CHECK constraint keeps bad strings out even if an API bug slips one
    # through validation — defense in depth.
    check_names = {
        c.name
        for c in MonitoredAddress.__table__.constraints
        if hasattr(c, "sqltext") and c.name
    }
    assert "ck_monitored_addresses_address_format" in check_names


def test_monitored_address_soft_delete_columns() -> None:
    cols = {c.name: c for c in MonitoredAddress.__table__.columns}
    # active is NOT NULL with server default; removed_at is nullable.
    assert not cols["active"].nullable
    assert cols["removed_at"].nullable
