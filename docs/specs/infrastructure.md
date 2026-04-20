# Aegis Infrastructure Planning — Stand-Up Requirements

**Spec Version:** 0.1  
**Author:** Bob (initial sketch)  
**Date:** 2026-04-20  
**Status:** Draft — for Jonto/Clark review  
**Drives:** Phase 1a deployment, AWS Fargate spec (#23)  

---

## Overview

What infrastructure does Aegis need to stand up and run? This doc maps components to concrete services and costs.

---

## Core Components

### 1. Layer 2 Blockchain Nodes

**What:** OP Stack rollup — sequencer + validator nodes for Aegis L2.

| Component | Spec | Cloud | Cost/mo |
|-----------|------|-------|---------|
| Sequencer | 4 vCPU, 16GB RAM, 500GB SSD | AWS c6i.xlarge (~$120/mo) or dedicated | $200-400 |
| Validator (x2) | 4 vCPU, 16GB RAM, 500GB SSD | AWS c6i.xlarge × 2 | $200-400 |
| Archive node (optional, for indexing) | 8 vCPU, 32GB RAM, 2TB SSD | AWS c6i.2xlarge | $200 |

**Note:** OP Stack can run on standard cloud VMs. No special GPU or custom silicon needed for the base rollup.

**Total L2 nodes:** ~$400-800/mo

---

### 2. Guardian Screening Service

**What:** Real-time transaction screening. Runs 24/7, needs GPU for Tier 2 inference.

| Component | Spec | Cloud | Cost/mo |
|-----------|------|-------|---------|
| Guardian API server | 2 vCPU, 8GB RAM | AWS c6i.large | $70 |
| GPU inference | A100 80GB or A10G | Modal (pay-per-second) or Lambda Labs | ~$200-500/mo at 10k TPS |
| Tier 3 batching | H100 (spot or batch) | Modal batch or GCP preemptible | ~$50-100/mo |

**Total screening:** ~$320-670/mo

**Key decision:** Self-host GPU vs pay-per-second (Modal/Lambda). Self-host = buy a GPU server (~$3k+/mo for H100) — only makes sense at high volume.

---

### 3. Intent Mapping Database

**What:** ClickHouse or Postgres for indexing + querying historical transactions.

| Component | Spec | Cloud | Cost/mo |
|-----------|------|-------|---------|
| Intent indexer | 8 vCPU, 32GB RAM, 1TB NVMe | AWS r6i.xlarge | $350 |
| ClickHouse (if used) | 8 vCPU, 32GB RAM, 500GB SSD | AWS r6i.2xlarge or ClickHouse Cloud | $300-600 |
| Envio indexer (optional) | Managed service | Envio Cloud or self-hosted | $0-200/mo |

**Total indexing:** ~$350-800/mo

---

### 4. Monitoring & Observability

**What:** Grafana dashboard, alerting, logs.

| Component | Spec | Cloud | Cost/mo |
|-----------|------|-------|---------|
| Metrics | Prometheus + Grafana Cloud | Grafana Cloud (free tier up to 10k metrics) | $0-45 |
| Logs | Loki or CloudWatch | AWS CloudWatch | $10-50/mo |
| Alerting | PagerDuty or OpsGenie | OpsGenie Free | $0 |

**Total observability:** ~$10-95/mo

---

### 5. Landing Page + Docs

**What:** Already deployed to Vercel.

| Component | Spec | Cost/mo |
|-----------|------|---------|
| Vercel (pro plan, for privacy repo access) | 3 team seats, analytics | $20/mo |
| Domain (aegischain.xyz) | Namecheap | $12/yr |

**Total web:** ~$20/mo

---

### 6. Guardian Set Smart Contracts

**What:** On-chain components.

| Component | Notes | Cost |
|-----------|-------|------|
| SoulHashRegistry | On-chain registry of guardian profile roots | Deployment gas only |
| GuardianValidatorSet | Validator registration + staking | Deployment gas only |
| DisputeResolver | Escalation handling | Deployment gas only |

**Total contracts:** ~$50-200 (one-time gas for deployment on mainnet/testnet)

---

## Estimated Total Monthly Cost

| Environment | Components | Cost/mo |
|------------|-----------|---------|
| **Testnet** | OP Stack dev nodes + Guardian dev + no GPU | $100-200 |
| **Phase 1a MVP** | 1 sequencer + 1 validator + Guardian API + Modal GPU + Intent DB | $500-800 |
| **Production (early)** | 2 validators + Guardian GPU + ClickHouse + Monitoring | $1,000-2,000 |

---

## Infrastructure Decisions Needed

### 1. Cloud Provider
- **AWS** — most flexibility, best for Fargate (ECS) container deployment
- **GCP** — better GPU pricing, strong Kubernetes support
- **Rollup-as-a-service** (e.g., Conduit, Chronicle) — reduces infra burden, subscription model

### 2. OP Stack Hosting
- Self-hosted on AWS EC2/ECS
- Or use a managed rollup service (Conduit, Chronicle, Caldera)

### 3. GPU Strategy
- **Modal/Lambda Labs** (pay-per-second) — best for variable load, Phase 1
- **Self-hosted H100/A100** — makes sense only when Aegis is processing >100k TPS

### 4. Intent Mapping Database
- **ClickHouse** — better for high-volume structured event data
- **Postgres + TimescaleDB** — simpler, already familiar tooling
- **Envio** — managed indexer, fast to set up

### 5. Deployment Model
- **Docker on ECS Fargate** — container-based, easy scaling, no EC2 management
- **Kubernetes (EKS)** — more ops overhead but more control
- **Bare EC2** — cheapest if you don't need auto-scaling

---

## Phase 1a Infrastructure Budget

Phase 1a is the Monitor Agent MVP. Components needed:

1. **OP Stack dev node** (sequencer) — for testing
2. **Guardian API** — screening the mempool
3. **Intent indexer** — storing tx history
4. **Monitor frontend** — web dashboard at /monitor

Estimated Phase 1a MVP cost: **$200-400/mo** on AWS (using Modal for GPU, dev-grade instances).

---

## Next Steps for This Issue

1. Jonto/Clark review and refine the component list
2. Decide: managed rollup (Conduit/Chronicle) vs self-hosted OP Stack
3. Decide: ClickHouse vs Postgres for intent mapping
4. Map Phase 1a MVP components to specific AWS resources
5. Create terraform/ECS task definitions for each component
