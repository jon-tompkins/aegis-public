> **v0 note — Clark's pre-merge draft, preserved for diff.**
>
> Bob's current version is [`soul-hash.md`](./soul-hash.md). That's the canonical one.
> This file exists so we can diff and recover anything Bob's rewrite dropped.
> Run `git diff docs/specs/soul-hash.v0.md docs/specs/soul-hash.md` to compare.

---

# Soul Hash / Intent Hashing

**Status:** Draft (tracks [#10](https://github.com/jon-tompkins/aegis-public/issues/10))
**Phase:** 0 — design
**Related:** [`aegis-chain-design.md` §Validator Integrity](../../aegis-chain-design.md), [intent-mapping.md](./intent-mapping.md)

---

## Purpose

Commit every block to the exact behavioral-profile dataset the validator screened against. Validators bring their own models, but they must prove they evaluated txs against the same ground-truth profiles. Chain-level analog of *"if you aren't running the right code, your blocks are rejected."*

## Goals

- Single root hash that commits to the full profile dataset for an epoch.
- Cheap to verify (block header field), cheap to update incrementally.
- Compatible with both "fully public" and "public-hash / private-detail" privacy modes.
- Clear rule for when a block is invalid because of a stale or wrong hash.

## Proposal

### Structure

```
ProfileDB @ epoch E
  ├── address_profiles:   sorted Merkle tree over (address → canonical_profile_bytes)
  ├── contract_profiles:  sorted Merkle tree over (contract → canonical_profile_bytes)
  └── meta:               { epoch, schema_version, created_at_block }

profile_root = keccak256(
    address_root ∥ contract_root ∥ keccak256(canonical_meta)
)
```

### Primitives

- **Hash:** `keccak256` — consistent with EVM, no new dependency.
- **Tree:** Sparse Merkle tree keyed by address (20-byte key). Sparse so absence proofs are as cheap as presence proofs.
- **Serialization:** SSZ. Fixed layout, auditable, already Ethereum-consensus-grade. Canonical-JSON is a weaker fallback.
- **Canonicalization:** fixed-width numerics, length-prefixed arrays, no floating point (scores in basis points).

### Block header extension

```
BlockHeader {
    ...standard OP Stack fields...
    aegis_ext: {
        profile_root:    bytes32,   // root above
        screening_root:  bytes32,   // merkle root over {tx_hash → {flag, score}}
        validator_sig:   bytes,     // BLS sig over (profile_root ∥ screening_root ∥ block_hash)
    }
}
```

### Validity rules

A block is invalid if:
1. `profile_root` does not match the canonical root for the block's epoch (within a grace window on epoch boundaries).
2. `screening_root` cannot be reconstructed from the block's txs.
3. `validator_sig` does not verify against the validator's registered BLS key.

### Epoch cadence

- Profile dataset frozen per epoch. Candidate periods: 12h or 1d (TBD with [intent-mapping.md](./intent-mapping.md)).
- Committee publishes the new `profile_root` at the epoch boundary + ~30s grace for validator sync.
- During grace, both old and new roots are accepted.

### Privacy compatibility

- **Fully public:** anyone rebuilds and verifies locally.
- **Private-detail:** committee publishes the root only; validators hold the preimage. Disputes reveal the relevant Merkle branch (`tx_hash → profile leaf`), not the full dataset.

## Acceptance criteria

- [ ] This spec (byte-level encoding included)
- [ ] Reference impl in Rust or Go of `profile_root` computation, tested against vectors
- [ ] Consumer of [intent-mapping.md `profile_epoch`](./intent-mapping.md#schema-v0)
- [ ] OP Stack header patch adding `aegis_ext` + validity check
- [ ] Test: validator with wrong `profile_root` has its block rejected
- [ ] Test: epoch transition grace window accepts both roots

## Open questions

- **Signature scheme:** BLS aggregates better for multi-validator vote paths — confirm ECDSA isn't cheaper given OP Stack conventions.
- **Model-hash commitment:** commit only to profile data (current design), or also to the reference Tier 2 model weights? Arguments either way.
- **Intra-epoch drift:** updates accumulate within an epoch and apply at the next boundary. Confirm that window isn't too long for fast-moving addresses.
