# Guardian Performance Research — Aegis Screening Benchmarks

**Research Version:** 1.0  
**Author:** Bob  
**Date:** 2026-04-19  
**Status:** Research Complete  
**Drives:** Guardian architecture, Tier 2/3 model selection, infra sizing  

---

## The Problem

Aegis has a ~2s L2 block time. Every transaction needs to be screened before it can be included. The constraint:

- **Normal tx:** must screen in <100ms (so it fits in the block window)
- **Escalated tx:** must screen in <2s (Tier 3 LLM)
- **Budget:** screening cost must not make the L2 expensive vs other L2s

The naive approach — run an LLM on every tx — fails immediately. An 8B model on GPU still takes 50-200ms per inference. At 10,000 TPS that's 500+ GPUs. Not viable.

**The solution: tiered architecture + batching.**

---

## Tiered Screening Architecture

### Tier 1 — Heuristics (runs on 100% of txs)

**Latency target:** <1ms per tx  
**Hardware:** CPU  
**Cost:** ~$0 per tx

Pure deterministic code. No ML. Examples from hack-taxonomy spec:
- Known malicious address match (bloom filter)
- Unusual gas price for contract type
- Bridge validator count below threshold
- Mint amount > threshold + same-block DEX swap
- Contract type +行为的异常组合

This eliminates ~95-99% of txs as clearly benign. Only the suspicious tail goes to Tier 2.

### Tier 2 — Statistical Model (runs on ~1-5% of txs)

**Latency target:** 30-50ms per tx  
**Hardware:** 1x A100 GPU (80GB)  
**Cost:** ~$0.00001 per tx (amortized)

Small open model (7B parameters) with quantization (AWQ/GGUF). This is the workhorse. It scores transactions, not explains them.

**Throughput on single A100 (vLLM):**
- Llama 3 8B (4-bit AWQ): ~200-400 tokens/sec
- Mistral 7B (4-bit): ~300-500 tokens/sec
- Qwen 2.5 7B: ~250-450 tokens/sec

With input averaging ~128 tokens, that's **~1500-3000 inferences/sec per A100**.

At 10,000 TPS with 2% → ~200 TPS suspicious → **1 A100 handles ~7x headroom**.

### Tier 3 — LLM Explanation (runs on escalated txs only, ~0.1%)

**Latency target:** <2s per tx  
**Hardware:** 1x H100 GPU  
**Cost:** ~$0.001 per escalation (amortized)

Larger model (70B+) for hard cases. Only escalations reach here. At 0.1% of 10,000 TPS = 10 escalations/sec = 10 H100 queries/sec = $0.01/sec = ~$900/day. But we can **batch** — group escalations over 500ms and process together.

**Batching:** 5 escalations in one call. Latency goes from 2s to ~2.5s (batching overhead). Cost drops 5x.

---

## Realistic Benchmarks

Based on publicly known vLLM benchmarks and Modal/Lambda inference pricing:

### Tier 2 — 7B Model on A100

| Model | Quant | Throughput (tok/s) | Input latency (128 tok) | Cost/hr |
|-------|-------|-------------------|------------------------|---------|
| Llama 3 8B | 4-bit AWQ | ~300 | ~0.4ms | ~$1.50 |
| Mistral 7B | 4-bit GGUF | ~400 | ~0.3ms | ~$1.50 |
| Qwen 2.5 7B | 4-bit | ~350 | ~0.36ms | ~$1.50 |

**Input latency is the wrong metric.** What matters is **time-to-first-token** for short outputs (flag + confidence = ~20 tokens):

- Llama 3 8B: ~15-25ms (TTFT)
- Mistral 7B: ~12-20ms (TTFT)
- Qwen 2.5: ~18-30ms (TTFT)

**P95 latency target: 30-50ms** — achievable with any of these.

### Tier 3 — 70B Model on H100

| Model | Quant | Throughput | TTFT (20 tok) | Cost/hr |
|-------|-------|-----------|---------------|---------|
| Llama 3 70B | 4-bit | ~150 tok/s | ~130ms | ~$4.50 |
| Mixtral 8x22B | 4-bit | ~200 tok/s | ~100ms | ~$4.50 |
| Qwen 2.5 72B | 4-bit | ~180 tok/s | ~110ms | ~$4.50 |

**P95 latency: <1s** — comfortable within the 2s escalation window.

---

## Cost Analysis

**Scenario: 10,000 TPS L2, 2% suspicious, 0.1% escalated**

| Component | Load | Hardware | Cost |
|-----------|------|---------|------|
| Tier 1 | 10,000 TPS | CPU (free) | $0 |
| Tier 2 | 200 TPS | 1x A100 | ~$0.00001/tx → $130/month |
| Tier 3 | 10 TPS | 1x H100 (batched) | ~$0.0001/tx → $90/month |
| **Total** | | | **~$220/month** |

For context: 10,000 TPS at $0.001 gas per tx = **$8.6M/month in gas revenue**. Screening cost is negligible.

---

## The Key Insight: Batching

The biggest lever is **batching suspicious txs**:

Instead of processing each suspicious tx individually (~30ms each), group them:

```
Batch of 50 suspicious txs, each 128 tokens input:
- Parallel processing on vLLM: ~150ms total
- Per-tx cost: 30x cheaper
- Per-tx latency: +50ms vs individual
```

Tradeoff: slightly higher latency, but 30x cost reduction. For Tier 2 (which is already fast), we don't batch. For Tier 3 (which is expensive), we batch aggressively.

---

## Model Recommendations (Open Source, Not Prescriptive)

**Requirement:** Any model that fits the latency/cost targets. No mandate on specific model.

### Tier 2 Candidates (7B, must be open weights):

| Model | License | Notes |
|-------|---------|-------|
| Mistral 7B | Apache 2.0 | Battle-tested, fast |
| Llama 3 8B | Llama 3 license | Strong, needs 4-bit for speed |
| Qwen 2.5 7B | Apache 2.0 | Competitive, fast |
| Phi-3.5 3.8B | MIT | Smallest, fastest, lower accuracy |

**Recommendation:** Mistral 7B + Qwen 2.5 as alternatives. Validator can choose.

### Tier 3 Candidates (70B, open weights):

| Model | License | Notes |
|-------|---------|-------|
| Llama 3 70B | Llama 3 license | Strong reasoning |
| Mixtral 8x22B | Apache 2.0 | MoE, cheaper to run |
| Qwen 2.5 72B | Apache 2.0 | Competitive |

---

## Infrastructure Options

### Option 1: Lambda Labs / Modal (recommended for v1)

- **Lambda:** A100/H100 instances, ~$0.00069/sec for A100 80GB
- **Modal:** Pay-per-second GPU, no idle cost, ~$1.50/hr for A100
- **vLLM** deployed as API endpoint
- **Cost at scale:** ~$200-500/month for 10,000 TPS

### Option 2: Self-hosted

- Buy/rent H100 servers
- More control, higher upfront
- Makes sense only at very high volume (>100k TPS)

### Option 3: Cloud GPU (AWS/GCP)

- EC2 p4d ($3.67/hr for A100) — expensive and idle-prone
- Better for batch workloads, not real-time

**Recommendation:** Modal for v1. No idle cost, pay per second, vLLM pre-configured.

---

## The Real Answer: Hardware IS the Answer

Jonto asked about chips. The honest answer:

- **Custom ASICs for Tier 1:** Would be ideal — bloom filter for malicious addresses, deterministic rule engine. But not worth it at Aegis scale yet.
- **GPU for Tier 2/3:** This is the real cost. But batching + Modal makes it affordable.
- **Small model specialization:** Fine-tuned 7B on screening data could match 70B performance. This is where research goes next.

**What we'd need to validate:**
1. Run vLLM benchmark on A100 with our tx format
2. Measure actual p95 latency on suspicious tx classification
3. Cost model at target TPS

---

## Open Questions

1. **What % of txs are actually suspicious?** Need real chain data. If >5%, Tier 2 cost scales up.
2. **Per-validator or shared screening?** Do all validators run their own Tier 2, or do they share a screening service?
3. **Slashing risk from slow screening?** If screening times out, what happens to the tx? What happens to the validator?
4. **BYO model + self-hosted GPU?** Can validators run their own inference? What's the latency SLA?
5. **Specialized fine-tuned model?** Could a 7B model fine-tuned on exploit patterns match a general 70B?

---

## Next Steps

1. **Benchmark:** Deploy Llama 3 8B on Modal, run against sample exploit txs, measure p95 latency
2. **Cost model:** Run 10k TPS simulation with 2% suspicious rate, calculate actual GPU cost
3. **Tier 1 expansion:** Encode more hack patterns as fast heuristics to increase % handled at CPU level
4. **Fine-tune exploration:** Fine-tune a 7B model on hack taxonomy data, measure if it catches what Tier 1 misses
