# Staking Systems Research — Aegis Economics

**Research Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-17  
**Status:** Research Complete  
**Drives:** Aegis Economics (#12), Validator Security Model  

---

## Source Documents

- Clark's economics draft: `docs/specs/economics.md`
- Jonto's DeFi in a Box (2024-06-21): https://paragraph.com/@jonto/defi-in-a-box
- EigenLayer docs: https://docs.eigenlayer.xyz
- UMA Oracle docs: https://docs.uma.xyz
- Aegis chain design: `aegis-chain-design.md`

---

## Staking Systems Evaluated

### 1. Ethereum Native Staking

**Model:** POS consensus — validators stake ETH, get rewarded for correct attestation, slashed for double voting / downtime.

**What works:**
- Battle-tested since Merge (Sept 2022), >$50B staked
- Slashing mechanics well-understood
- Decentralized validator set with no privileged operators
- Clear惩罚 (slashing) for malicious behavior

**What doesn't work for Aegis:**
- Designed for consensus, not application-specific screening
- No mechanism for task-level rewards (per-tx screening)
- Slashing is binary (attested correctly or didn't), not probabilistic
- 32 ETH minimum = validator centralization risk for smaller chains

**Aegis applicability:** Base security layer for L2 consensus. Aegis validators must be Ethereum stakers — but native ETH staking alone doesn't solve the screening economics problem.

---

### 2. EigenLayer — Restaking

**Model:** ETH/LST restakers delegate to Operators who secure AVSs (Autonomous Verifiable Services). Restakers earn extra yield; Operators earn fees from AVSs. Slashing flows back to restakers.

**Architecture:**
```
Restakers → DelegationManager → Operators → AVSs (Aegis Screening)
                                            ↑
                                    Slash penalties flow back
```

**Contracts (mainnet):**
- `DelegationManager`: 0x39053D51B77DC0d36036Fc1fCc8Cb819df8Ef37A
- `StrategyManager`: 0x858646372CC42E1A627fcE94aa7A7033e7CF075A
- `AVSDirectory`: 0x135dda560e946695d6f155dacf6f1f25c1f5af
- `RewardsCoordinator`: 0x7750d328b314EfFa365A0402CcfD489B80B0adda

**What works:**
- AVS ecosystem growing — operators can serve multiple AVSs simultaneously
- EigenLayer already deployed on mainnet Ethereum + Base
- AgentKit (eigencloud.xyz/agentkit) enables agents to operate as AVS operators — relevant for Aegis agents
- Restaked ETH as collateral for Aegis screening is compelling: existing ETH stakers can diversify into screening income without new capital commitment
- Slashing penalties flow back to restakers — aligns incentives cleanly

**What doesn't work for Aegis:**
- **Cascading slash risk:** If an Aegis AVS gets exploited via the validator set, the slash flows back to all restakers who delegated to those operators. This is the main criticism of EigenLayer — correlated slashing.
- **External dependency:** Building on EigenLayer means Aegis's security is coupled to EigenLayer's contract security. If EigenLayer itself has a bug, all AVSs are affected.
- **AVS registration complexity:** AVS must register with EigenLayer's AVSDirectory, define reward/slash parameters. Adds integration overhead.
- **EigenDA cost:** Data availability through EigenDA adds cost; must evaluate vs raw L2 sequencing.

**Should Aegis use EigenLayer?**

| Scenario | Verdict | Reasoning |
|----------|---------|-----------|
| Aegis validators = ETH restakers via EigenLayer | ⚠️ Consider | Clean capital efficiency — ETH stakers earn screening yield |
| Aegis as AVS on EigenLayer | ⚠️ Deferred | External dependency risk for a new chain; revisit post-mainnet |
| Aegis native staking (no EigenLayer) | ✅ Yes for v1 | Keep it simple. Add EigenLayer AVS integration in v2. |

**Recommendation:** Build native AEGIS staking for v1. Design the AVS interface so v2 can plug into EigenLayer without changing the core contract logic.

---

### 3. UMA — Optimistic Oracle + Bonding

**Model:** Asserter posts a bond, makes an assertion. Disputer can refute within liveness period. If not disputed → assertion accepted. If disputed → DVM (tokenholder vote) resolves.

**Architecture (from UMA docs):**
```
Asserter posts bond → Assertion made
         ↓
    Disputer has window to refute
         ↓
   Undisputed → Accepted
   Disputed → DVM (48-96h vote) → Final resolution
```

**What works for Aegis:**
- **Bond + dispute model maps directly to Aegis escalation:** Guardian makes assertion (flag), validator can dispute (escalate), council resolves
- **Human-in-the-loop for hard cases:** DVM (UMA tokenholders) as council — proven mechanism
- **Economic security = cost of corruption > profit from corruption** — the UMA security model
- **Slow path (DVM) vs fast path (optimistic):** Matches Aegis design (fast screening, slow council for disputes)
- **Bond sizing:** Asserter chooses bond size — higher bond = more credible assertion. Aegis could require larger bonds for higher-confidence assertions.

**What doesn't work for Aegis:**
- **48-96h DVM resolution is too slow for high-frequency L2 tx** — but works for council-level disputes
- **UMA token dependency:** DVM voters must hold UMA — adds another governance token
- ** UMA token price volatility** affects security budget (cost of corruption measured in UMA)

**Aegis applicability:** 
- **Council escalation model:** Use UMA-like bond + dispute + DVM for council arbitration
- **Guardian assertions:** Bonded assertions at Tier 1/2 level (not needed for every tx — only escalated cases)
- **Not for core screening:** Too slow for 100% tx screening

---

### 4. L2 Native Staking (Arbitrum, Optimism, Base)

**Model:** Sequencer/staker hybrids — validators stake L2 tokens to participate in fraud proof or validity proof systems.

**What works:**
- **Base:** No native staking token — relies on Ethereum security. Clean for Aegis.
- **Arbitrum:** Uses ETH staking for validators. Validators must stake ETH to run a validator node.
- **Proven at scale:** Arbitrum has $15B+ TVL, Optimism $10B+.

**What doesn't work for Aegis:**
- L2 staking is primarily for sequencing/fraud proof participation, not task-specific screening
- No built-in mechanism for per-tx screening rewards

**Aegis applicability:** Base chain should use Ethereum native staking (no L2 token). Aegis validators stake ETH + AEGIS, not an L2 token.

---

### 5. Berachain / Chain-Native DeFi (from DeFi in a Box)

**Model:** Chain itself deploys core DeFi primitives (AMM, lending) and collects fees. Validator = chain operator + DeFi participant.

**What works:**
- **Proven by Berachain:** Built-in PMM (Polaris AMM) + lending, chain collects fees
- **Eliminates protocol TVL migration risk** — TVL stays on chain by default
- **Validator incentives are structural:** Validators benefit from chain fee revenue
- **Agents managing protocols = chain-native:** From DeFi in a Box — agents manage protocols, chain provides the infrastructure

**From DeFi in a Box (Jonto):**

The Core DeFi Stack required for a new chain:
- **Required:** AMM (Uniswap v3/Solidly), Pool Lending (Aave/Compound), Bridging (LayerZero/Across/Native), Governance/Gauges (Curve/Solidly)
- **Nice to Have:** Token/NFT Factory, NFT Marketplace, CDP Stablecoin, Regulated Stablecoin
- **Hurdles:** Oracles (Chainlink), Bridges

**For Aegis:**
- If Aegis runs chain-native DeFi, the validators are also LP providers and borrowers
- Screening becomes a fee-generating service ON the chain, not just a security cost
- Agents as protocol managers fits the model — agents manage the lending pool, AMM, bridging

**Aegis applicability:** Strong fit for the DeFi primitives layer. If Aegis embeds core DeFi:
1. Fees from AMM/lending go to validator pool (security + operations funded)
2. Agents manage protocols (per DeFi in a Box)
3. Screening = embedded service, not external cost center

---

## Synthesis: Recommended Architecture

### Layer 1: Ethereum Security
- Validators stake ETH natively (or via liquid staking tokens)
- No new L2 token required for consensus

### Layer 2: Aegis Native Staking (v1)
```
Validator stakes AEGIS + ETH
    │
    ├── Screening rewards (gas surcharge)
    ├── Inflation (bounded bootstrap)
    └── Slashing (negligence)
```

### Layer 3: EigenLayer AVS (v2, deferred)
```
Restakers → EigenLayer → Aegis as AVS
    │
    └── Extra yield for ETH restakers
        │
        └── Aegis validators as Operators
```

### Layer 4: Council Arbitration (UMA-style)
```
Guardian assertion (bonded)
    │
    ├── Disputed → Council review
    │       │
    │       └── DVM vote (48-96h)
    │
    └── Undisputed → Accepted
```

---

## Chain-Native DeFi Primitives for Aegis

Per Jonto's DeFi in a Box framework:

| Primitive | Implementation | Purpose |
|-----------|---------------|---------|
| Primitive | Implementation | Purpose | Notes |
|-----------|---------------|---------|-------|
| AMM | **Solidly** (volatile + stableswap) | Fee generation, LP for validators | Battle-tested. Volatile pairs + stablecoin swaps. |
| Pool Lending | **Aave v3** | Borrow against staked position | Widely audited, large TVL, upgradeable proxy |
| CDP Stablecoin | **GHO** (Aave-built) | Chain-native stable, backed by protocol collateral | Mintable by protocol, governed via Aave governance |

**Agents as Protocol Managers:**
- Agents don't actively trade — they monitor and manage protocols
- Threshold-based intervention: if TVL drops, liquidity incentives auto-adjust
- Agents file teacups on protocol anomalies → feeds training pipeline
- Largely hands-off, per DeFi in a Box — "agents manage the protocols but they're largely hands off"

**Fee Flows:**
```
AMM fees ──────────────→ Validator pool
Lending interest ──────→ Validator pool  
Bridging fees ─────────→ Validator pool
Screening fee (gas) ───→ Validator pool
Inflation (AEGIS) ──────→ Validator pool (bounded)
```

---

## Decision Matrix

| System | Use for Aegis | Rationale |
|--------|--------------|-----------|
| Ethereum native staking | ✅ Consensus layer | Required, battle-tested |
| AEGIS native staking | ✅ v1 | Core validator bonding + slash |
| EigenLayer AVS | ⚠️ v2 deferred | External dependency risk for v1; compelling for v2 |
| UMA-style council | ✅ Escalation/arbitration | Bond + dispute + DVM fits council model |
| L2 token staking | ❌ No | No L2 token for Aegis |
| Chain-native DeFi | ✅ Core primitives | Per DeFi in a Box — AMM + lending + bridging |
| Berachain model | ✅ Reference | Chain collects DeFi fees = sustainable validator income |

---

## Open Questions

1. **EigenLayer timeline:** When does Aegis v1 ship vs when EigenLayer AVS registration stabilizes?
2. **Chain-native DeFi scope:** How deep does Aegis go? Just AMM + lending, or full DeFi stack?
3. **AEGIS token distribution:** Is there an inflation schedule? Who gets genesis allocation?
4. **Council composition:** UMA-style tokenholders or designated set? Term limits?
5. **Insurance tier:** High-TVL protocols pay Aegis for enhanced screening — how is price set?

---

## Recommendations

1. **Skip EigenLayer for v1** — too much external dependency coupling. Design for v2 pluggability.
2. **Use UMA-style bond+dispute for council escalation** — proven pattern, matches Aegis Guardian design.
3. **Build chain-native DeFi per DeFi in a Box** — AMM + lending as core primitives. Validators = fee recipients.
4. **Agents as hands-off protocol managers** — per Jonto's model. Only intervene on threshold breaches.
5. **AEGIS token = staking + governance only** — no speculative trading utility in v1.


---

## Design Decision (Jonto — 2026-04-17)

**Gas token: ETH or chain-native stable. NOT AEGIS.**

Users pay gas in ETH (or stable) — no AEGIS required to transact. AEGIS is staking + governance only.

This avoids:
- AEGIS speculative premium baked into every tx cost
- Token price volatility affecting user gas costs
- New token friction for onboarding users


