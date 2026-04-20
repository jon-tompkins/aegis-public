# BYO-Model Interface — Validator Screening API

**Spec Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-17  
**Status:** Draft  
**Drives:** Soul hash determinism, validator diversity  

---

## Problem

Validators must use the same canonical behavioral profiles (committed via soul hash) but may run different models. The BYO-model interface defines how a validator's model interacts with the protocol — what it receives as input, what it must produce as output, and how the soul hash verifies the model was given the correct profiles.

**Core constraint:** All models must produce the same screening result given the same profile + transaction. If Model A and Model B disagree on the same tx with the same profile, the soul hash cannot verify which was correct.

**Solution:** The soul hash commits to the **profile data** (input), not the model behavior. Models can differ — but they must all be given the same canonical profiles. Disagreement between models on the same input is a governance issue, not a protocol issue.

---

## Interface Definition

### ScreeningInput

What every model receives, deterministically:

```protobuf
message ScreeningInput {
    Transaction tx = 1;           // The transaction being screened
    ProfileEntry address_profile = 2;   // Canonical address profile
    ProfileEntry contract_profile = 3;  // Canonical contract profile
    uint64 epoch = 4;             // Current epoch
}

message Transaction {
    bytes32 tx_hash = 1;
    bytes20 sender = 2;
    bytes20 receiver = 3;
    uint256 value = 4;             // wei
    bytes   data = 5;              // calldata
    uint64  nonce = 6;
    uint64  block_number = 7;
    uint64  timestamp = 8;
}
```

### ScreeningOutput

What every model must produce:

```protobuf
message ScreeningOutput {
    Flag flag = 1;               // 0=clear, 1=watch, 2=escalate, 3=pause, 4=reject
    uint32 confidence_bp = 2;    // 0-10000 basis points
    bytes32 reasoning_hash = 3;  // Hash of model's reasoning (for disputes)
    string reasoning_snippet = 4; // First 200 chars of reasoning (not verified)
}

enum Flag {
    CLEAR = 0;      // Execute immediately
    WATCH = 1;       // Execute + log
    ESCALATE = 2;    // Hold for validator vote
    PAUSE = 3;       // Reject + pause contract/address
    REJECT = 4;      // Hard reject
}
```

### ModelInterface (Rust trait)

```rust
use super::{ScreeningInput, ScreeningOutput};

#[tonic::proto]
trait AegisScreener {
    async fn screen(&self, input: ScreeningInput) -> Result<ScreeningOutput, Status>;
}

/// gRPC service definition:
/// service AegisScreener {
///     rpc Screen(ScreeningInput) returns (ScreeningOutput);
///     rpc Health(HealthRequest) returns (HealthResponse);
/// }
```

### VerificationCondition

The soul hash does NOT verify model reasoning — it verifies the model was given the correct profiles:

```
IsValidScreening = {
    profile_root matches canonical root for epoch,
    model produced a valid ScreeningOutput,
    output.flag ∈ {CLEAR, WATCH, ESCALATE, PAUSE, REJECT},
    output.confidence_bp ∈ [0, 10000]
}
```

The soul hash commits to `profile_root`. If a validator's block references a wrong profile root, the block is rejected — regardless of what flag the model produced.

---

## Profile Loading Protocol

Before screening any transaction, the model MUST load the current canonical profiles:

```rust
async fn load_profiles(&self, epoch: u64) -> Result<ProfileSet, Error> {
    // 1. Fetch profile_root from chain
    let profile_root = self.chain.get_profile_root(epoch)?;
    
    // 2. Fetch encrypted profiles (Mode B: public hash / private detail)
    let encrypted_profiles = self.store.get_profiles(epoch)?;
    
    // 3. Verify profiles match profile_root
    let computed_root = compute_merkle_root(encrypted_profiles)?;
    if computed_root != profile_root {
        return Err(Error::ProfileRootMismatch);
    }
    
    // 4. Decrypt profiles (validator's local key)
    let profiles = decrypt_profiles(encrypted_profiles)?;
    
    return Ok(profiles);
}
```

This is the key invariant: **the model cannot screen against a non-canonical profile set.** The protocol enforces this by requiring `profile_root` in the block header.

---

## Tier Mapping to Model Interface

| Tier | Input | Model Type | Latency Target |
|------|-------|-----------|--------------|
| Tier 1 (heuristics) | tx only | Rule engine | <10ms |
| Tier 2 (statistical) | tx + profiles | IsolationForest / ML | <50ms |
| Tier 3 (LLM) | tx + profiles + history | LLM | <2s |

**v0 implementation:** Tier 1 + Tier 2 in a single Rust service. Tier 3 as separate LLM call.

---

## Model Registration

Validators register their model interface version at startup:

```json
{
  "validator": "0xabc...",
  "model_id": "isolation-forest-v1",
  "model_hash": "0xdef...",     // Hash of model weights / rules
  "interface_version": "1.0.0",
  "screener_endpoint": "grpc://localhost:50051",
  "profile_epoch_loaded": 12345,
  "profile_root": "0x123..."
}
```

This registration is on-chain and included in the validator's block signature.

---

## Compliance Tests (CAPTCHA for validators)

To prevent lazy or broken models, validators must pass periodic compliance tests:

1. **Known exploit replay:** Model must correctly flag 10/10 historical exploits
2. **Random sampling:** 1% of normal txs audited against consensus
3. **Reasoning hash check:** If >20% of validators disagree on a CLEAR/WATCH flag, reasoning_hash is audited

```
TestResult {
    test_id: "exploit-replay-v1",
    passed: bool,
    false_negatives: uint32,   // Missed exploits
    false_positives: uint32,   // Normal txs flagged
    timestamp: uint64,
}
```

Failed compliance → validator flagged for review → potential stake slash.

---

## What Models Can Differ On (Valid Disagreement)

- Reasoning style (verbose vs terse)
- Internal confidence scoring (as long as flag agrees)
- Processing approach (neural vs statistical)
- Threshold calibration (as long as flag agrees with protocol thresholds)

## What Models Must Agree On (Soul Hash Enforcement)

- **Flag** on the same tx with the same profiles
- **Profile root** loaded at screening time
- **Output format** (valid ScreeningOutput structure)

---

## Training Resources

- [SEAL Intel SDK](https://github.com/security-alliance/seal-intel-sdk) — TypeScript SDK from Security Alliance for web content trust/block/revoke signals. Integrate with Aegis screening pipeline for off-chain threat intel.
- [rekt.news](https://rekt.news) — Exploit database with post-mortems
- Aegis Hack Taxonomy (`docs/specs/hack-taxonomy.md`) — Major DeFi exploits catalogued by attack vector

## Open Questions

1. **Reasoning hash audit:** Who triggers it? How is reasoning submitted for comparison? ZK proof of reasoning?
2. **Compliance test frequency:** How often must validators run compliance tests? On every epoch?
3. **Model hash:** What exactly do we hash? Model weights? Rule set? Code commit?
4. **Interface versioning:** If the ScreeningInput proto changes, how do we handle old/incorrect model outputs?

---

## Implementation Path

1. Define proto files (this doc)
2. Implement `ScreeningInput` / `ScreeningOutput` types in Rust
3. Implement reference Tier 1+2 screener as gRPC server
4. Write compliance test harness
5. Integrate with validator block signing
6. Test with historical exploit replay
