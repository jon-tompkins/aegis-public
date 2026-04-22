"""InteractionState — process-local tracker for T1.5."""

from __future__ import annotations

from aegis_monitor.screening.interaction_state import InteractionState


def test_record_and_read_approval() -> None:
    state = InteractionState()
    addr = "0x" + "aa" * 20
    assert state.last_approval_ms(addr) is None
    state.record_approval(addr, 12345)
    assert state.last_approval_ms(addr) == 12345


def test_record_destination_and_lookup() -> None:
    state = InteractionState()
    addr = "0x" + "aa" * 20
    dest = "0x" + "bb" * 20
    assert state.has_seen_destination(addr, dest) is False
    state.record_destination(addr, dest)
    assert state.has_seen_destination(addr, dest) is True


def test_address_case_insensitive() -> None:
    state = InteractionState()
    upper = "0x" + "AA" * 20
    lower = "0x" + "aa" * 20
    state.record_destination(upper, "0x" + "bb" * 20)
    assert state.has_seen_destination(lower, "0x" + "BB" * 20) is True


def test_destination_lru_eviction() -> None:
    state = InteractionState(max_destinations_per_addr=2)
    addr = "0x" + "aa" * 20
    state.record_destination(addr, "0x" + "01" * 20)
    state.record_destination(addr, "0x" + "02" * 20)
    state.record_destination(addr, "0x" + "03" * 20)
    # Oldest (01) should have been evicted.
    assert state.has_seen_destination(addr, "0x" + "01" * 20) is False
    assert state.has_seen_destination(addr, "0x" + "02" * 20) is True
    assert state.has_seen_destination(addr, "0x" + "03" * 20) is True


def test_address_lru_eviction() -> None:
    state = InteractionState(max_addresses=2)
    addr1 = "0x" + "01" * 20
    addr2 = "0x" + "02" * 20
    addr3 = "0x" + "03" * 20
    state.record_destination(addr1, "0x" + "ab" * 20)
    state.record_destination(addr2, "0x" + "ab" * 20)
    state.record_destination(addr3, "0x" + "ab" * 20)
    # addr1 should have been evicted; addr2, addr3 retained.
    assert state.destination_count(addr1) == 0
    assert state.destination_count(addr2) == 1
    assert state.destination_count(addr3) == 1


def test_destination_count() -> None:
    state = InteractionState()
    addr = "0x" + "aa" * 20
    assert state.destination_count(addr) == 0
    state.record_destination(addr, "0x" + "01" * 20)
    state.record_destination(addr, "0x" + "02" * 20)
    state.record_destination(addr, "0x" + "01" * 20)  # dedupes
    assert state.destination_count(addr) == 2
