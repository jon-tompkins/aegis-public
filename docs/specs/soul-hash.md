# Soul Hash — Verifiable Behavioral Ground Truth

**Spec Version:** 1.0  
**Author:** Bob + Clark  
**Date:** 2026-04-17  
**Status:** Draft  
**Depends on:** `#7` (profile schema)

---

## Overview

Validators bring their own AI models but must evaluate transactions against a **canonical behavioral profile dataset**. The soul hash is the chain's mechanism for enforcing this: a Merkle root of the canonical profile dataset is committed in each block header, and blocks that reference stale or wrong roots are rejected.

Analogous to Ethereum's rule: *"if you aren't running the right code, your blocks are rejected."* Here: *"if you aren't evaluating against the current profiles, your blocks are rejected."*

---

## Data Model

### ProfileEntry

Represents a single address's behavioral profile at a point in time.

```
ProfileEntry {
    address: bytes20          # Ethereum address
    epoch: uint64             # Epoch number this profile is valid for
    version: uint16           # Schema version for forward compatibility
    
    # Core behavioral features
    tx_count_30d: uint64      # Txs in last 30 days
    avg_value_30d: uint256     # Average tx value (wei), encoded as uint256
    max_value_30d: uint256    # Max tx value (wei)
    active_hours: bytes3       # Bitfield: 8-hour windows over 3 days (72 bits packed into 9 bytes, truncated to 3)
    counterparty_count: uint32
    protocol_count: uint16
    
    # Anomaly thresholds (in basis points, 10000 = 1.0)
    value_threshold_bp: uint16  # >N bp above avg → flag
    frequency_threshold_bp: uint16
    new_counterparty_threshold_bp: uint16
    
    # Risk signals
    risk_flags: uint16        # Bitfield: NEW_ADDRESS, MIXER_HINT, PROXY_CREATED, etc.
    anomaly_score: uint16     # 0-10000 BP
    
    # Metadata
    first_tx_epoch: uint64
    last_update_epoch: uint64
    profile_type: uint8       # 0=EOA, 1=contract, 2=contract钱包
}
```

### ProfileSnapshot

A sparse Merkle tree containing all `ProfileEntry` entries for a given epoch.

```
ProfileSnapshot {
    epoch: uint64
    root: bytes32             # Root hash of the sparse Merkle tree
    tree_size: uint64         # Number of entries
    hash_function: uint8      # 0=keccak256, 1=sha256
    created_at: uint64        # Unix timestamp
}
```

### ScreeningEntry

Records what a validator did with a transaction.

```
ScreeningEntry {
    tx_hash: bytes32
    validator_address: bytes20
    epoch: uint64
    
    # What the validator concluded
    flag: uint8               # 0=clear, 1=watch, 2=escalate, 3=pause, 4=reject
    confidence_bp: uint16      # 0-10000 basis points
    reasoning_hash: bytes32   # Hash of the validator's reasoning (for disputes)
    
    # Sig: sign(profile_root || tx_hash || flag)
    validator_sig: bytes65     # ECDSA signature
}
```

### AegisExt (Block Header Extension)

Appended to the L2 block header.

```
AegisExt {
    profile_root: bytes32      # Root of ProfileSnapshot for this epoch
    screening_root: bytes32    # Root of ScreeningEntry tree (if any)
    validator_sig: bytes65     # Aggregated sig or single validator's sig
    
    # Epoch transition
    prev_profile_root: bytes32 # Root from previous epoch (for grace period)
    epoch_transition_at: uint64 # Block number of last epoch boundary
}
```

---

## Sparse Merkle Tree

### Why Sparse

The profile dataset is too large to hash entirely on-chain (millions of addresses). A sparse Merkle tree lets us commit to the full dataset with a single 32-byte root, while allowing compact proofs for any individual address.

### Structure

- **Depth:** 160 bits (one per bit of an Ethereum address)
- **Leaf:** `hash(address || ProfileEntry)` — hash of address concatenated with encoded profile
- **Node:** `hash(left_child || right_child)`
- **Empty leaf:** `hash(0)` — a special sentinel
- **Root:** Top node after hashing all 2¹⁶⁰ possible paths

### Hash Function

`keccak256` for all node hashes. Compatible with Ethereum's native ABI encoding.

### Profile Root Computation

```
def compute_profile_root(entries: List[ProfileEntry]) -> bytes32:
    tree = {}
    
    for entry in entries:
        key = entry.address  # 20 bytes
        value = encode_ssz(entry)  # SSZ-encoded ProfileEntry
        
        # Compute leaf hash
        leaf = keccak256(key || value)
        
        # Place at depth-160 path corresponding to address bits
        path = [True/False for each of 160 address bits]
        tree[path] = leaf
    
    # Compute root by hashing pairs up the tree
    return compute_merkle_root(tree, depth=160)
```

---

## SSZ Encoding

All structs use Ethereum's **Simple Serialize (SSZ)** format.

### Type Mappings

| Type | SSZ Bytes |
|------|-----------|
| uintN | N/8 bytes, little-endian |
| bytes20 | 20 bytes |
| bytes32 | 32 bytes |
| bytes3 | 3 bytes |
| uint256 | 32 bytes, big-endian |
| Flag bitfield | Variable, packed |

### Notable Encoding Rules

- **No floats:** All fractional values stored as basis points (BP). `0.05 = 500 bp`.
- **Fixed-width only:** No strings, no variable-length arrays.
- **Bitfields packed:** `active_hours` is 9 bytes (72 bits for 72 8-hour windows), NOT a dynamic bitlist.

---

## Block Validity Rules

### Profile Root Check

```
IF block.aegis_ext.profile_root != canonical_root_for(block.epoch):
    REJECT_BLOCK
```

### Grace Window (Epoch Transition)

On epoch boundary, both old and new roots are valid for a bounded window:

```
GRACE_PERIOD = 30 seconds  # Or 1 epoch, whichever is larger

def is_valid_profile_root(block, prev_profile_root):
    if block.epoch == prev_block.epoch:
        return block.profile_root == canonical_root(block.epoch)
    
    # Epoch transition: allow previous root during grace
    if block.timestamp - prev_block.timestamp < GRACE_PERIOD:
        return block.profile_root in [canonical_root(block.epoch), prev_profile_root]
    
    return block.profile_root == canonical_root(block.epoch)
```

---

## Privacy Modes

### Mode A: Public Profiles

All `ProfileEntry` data is publicly readable. Anyone can recompute the root. Good for transparency, bad for security — attackers can study profiles to find blind spots.

### Mode B: Public Hash / Private Detail

- Profile entries are **encrypted** before committing the root
- Root is public
- Validators prove (via ZK-SNARK or VDF) that their encrypted entry matches the root
- For v1: **use this mode**

### Mode C: Silent But Verify (future)

- Profiles never exposed publicly
- Validator proves they hold a valid entry matching the root
- Requires trusted execution environment (TEE) or ZKP

---

## OP Stack Integration

### Modified Components

1. **l2block.go** — Add `AegisExt` to `PayloadAttributes` or `L2Block`
2. **validation.go** — Add `ValidateAegisExt()` check in block validation pipeline
3. **derivation.go** — Compute `profile_root` from `ProfileSnapshot` and inject into header
4. **config.go** — Add `AegisConfig { enabled, epoch_duration, grace_period }`

### Derivation Pipeline Change

```
PayloadAttributes {
    ...
    aegis_ext: {
        profile_root: bytes32
        prev_profile_root: bytes32
        epoch_transition_at: uint64
    }
}
```

### Key Function

```go
func ValidateAegisExt(ext AegisExt, epoch uint64, prevRoot bytes32) error {
    expectedRoot := GetCanonicalProfileRoot(epoch)
    if ext.profile_root != expectedRoot && !withinGracePeriod(ext, epoch, prevRoot) {
        return fmt.Errorf("invalid profile root: got %x, expected %x", ext.profile_root, expectedRoot)
    }
    return nil
}
```

---

## Reference Implementation (Go)

### Core Types

```go
package aegis

import "github.com/ethereum/go-ethereum/params"

type AegisExt struct {
    ProfileRoot        [32]byte
    ScreeningRoot      [32]byte
    ValidatorSig       [65]byte
    PrevProfileRoot    [32]byte
    EpochTransitionAt  uint64
}

type ProfileEntry struct {
    Address              [20]byte
    Epoch               uint64
    Version             uint16
    
    TxCount30D          uint64
    AvgValue30D         *big.Int  // uint256, SSZ encoded as 32 bytes
    MaxValue30D         *big.Int
    ActiveHours         [3]byte   // Packed bitfield
    CounterpartyCount   uint32
    ProtocolCount       uint16
    
    ValueThresholdBP      uint16
    FrequencyThresholdBP  uint16
    NewCounterpartyThresholdBP uint16
    
    RiskFlags       uint16
    AnomalyScore    uint16  // 0-10000 bp
    
    FirstTxEpoch   uint64
    LastUpdateEpoch uint64
    ProfileType    uint8
}

// ComputeRoot returns the canonical profile root for a given epoch
func ComputeRoot(entries []ProfileEntry) ([32]byte, error) {
    // Build sparse Merkle tree
    // Return root
}

// IsValid checks if an AegisExt is valid for the given epoch
func (a *AegisExt) IsValid(epoch uint64, prevRoot [32]byte, gracePeriod uint64) bool {
    expected := GetCanonicalProfileRoot(epoch)
    if a.ProfileRoot == expected {
        return true
    }
    // Grace period check
    if a.EpochTransitionAt > 0 && epoch > a.EpochTransitionAt {
        if a.PrevProfileRoot == prevRoot {
            return withinGracePeriod(a, epoch, prevRoot)
        }
    }
    return false
}
```

### Profile Root Contract (on-chain)

```solidity
contract SoulHashRegistry {
    mapping(uint64 => bytes32) public profileRoots;  // epoch → root
    uint64 public currentEpoch;
    
    function commitRoot(uint64 epoch, bytes32 root) external {
        require(epoch >= currentEpoch);
        profileRoots[epoch] = root;
        if (epoch > currentEpoch) currentEpoch = epoch;
    }
    
    function getProfileRoot(uint64 epoch) view returns (bytes32) {
        return profileRoots[epoch];
    }
    
    function isValidRoot(uint64 epoch, bytes32 root) view returns (bool) {
        return profileRoots[epoch] == root;
    }
}
```

---

## Acceptance Criteria

- [x] Full byte-level encoding spec (this doc)
- [ ] Reference impl (Go) of `compute_profile_root` with test vectors
- [ ] Reference impl (Go) of `IsValid` with grace period logic
- [ ] SSZ encoding tests for all types
- [ ] Consumer of `#7` profile_epoch data
- [ ] OP Stack header patch adding `AegisExt` + validity check
- [ ] Test: stale/wrong `profile_root` rejects block
- [ ] Test: epoch transition accepts both roots during grace
- [ ] Test: correctly-formed ext accepts block

---

## Open Questions

1. **Screening root:** Do we commit to all `ScreeningEntry` data on-chain? Storage cost?
2. **Aggregator sig:** Single validator sig vs BLS aggregated sig — what's the threshold?
3. **ZK proof mode:** For v2, can we do ZK proofs of profile inclusion without revealing the profile?
4. **Profile update frequency:** Every block vs every epoch vs event-driven?
5. **SMT vs Pell MST:** Address collision handling — Pell-encoded MST handles non-injective mappings better for address→index.
