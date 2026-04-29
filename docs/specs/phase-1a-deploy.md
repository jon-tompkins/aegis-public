# Phase 1a Deploy — AWS Fargate + Postgres + Secrets Manager

**Spec Version:** 0.1 (draft)
**Author:** Bob
**Date:** 2026-04-29
**Status:** Draft — operator inputs pending (see "Operator inputs" section)
**Tracks:** [#23](https://github.com/jon-tompkins/aegis-public/issues/23)
**Related:** [`infrastructure.md`](./infrastructure.md), [`arweave-flag-storage.md`](./arweave-flag-storage.md), [`phase-1a-tasks.md`](./phase-1a-tasks.md)

---

## Purpose

Ship `aegis-monitor` (from #21) on AWS so the demo is reachable at a public URL and the `/monitor` UI from #22 can hit it. This is the smallest deploy that satisfies Phase 1a — one Fargate task, one small RDS instance, one ALB, secrets in AWS Secrets Manager, image in ECR.

This spec exists to (a) lock the AWS resource shape before terraform is written and (b) capture the small set of operator inputs the deploy needs from Jonto.

---

## Goals

- One public URL serving the monitor's HTTP API + WebSocket `/stream`.
- Single-task Fargate service to start; can scale horizontally without code changes.
- Postgres (RDS) for the hot cache (canonical store is Arweave per `arweave-flag-storage.md`).
- Secrets in Secrets Manager; the Fargate task pulls them via task-role IAM at boot.
- Container image pushed to ECR; Fargate task definition pinned to a specific image digest.
- Reproducible: every resource is in terraform, no click-ops in the AWS console.
- First deploy from Jonto's laptop via `terraform apply`; OIDC GitHub Actions deploy role is a Phase 1a.5 follow-up.

## Non-goals

- Multi-region. Single region (`us-west-2` default).
- Auto-scaling beyond 1 task. Manual scale-out via terraform until load justifies it.
- HSM/KMS custody for the agent signing key. Plain Secrets Manager entry for Phase 1a; KMS-wrapped or HSM in Phase 1b.
- CDN in front of the API. ALB direct is fine for demo volume; CloudFront added when we care about geo or DDoS.
- A separate worker for the Arweave writer task. Runs in-process inside the Fargate task for Phase 1a (per arweave-flag-storage.md §Operator checklist).

---

## Topology

```
                       ┌────────────────────────┐
                       │   Route 53 hosted zone │
                       │   monitor.<domain>     │
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │   ALB (HTTPS + WSS)    │
                       │   ACM cert (auto-renew)│
                       └───────────┬────────────┘
                                   │
                       ┌───────────▼────────────┐
                       │  ECS Fargate service   │
                       │  task: aegis-monitor   │
                       │  desired_count = 1     │
                       │  0.5 vCPU / 1 GB       │
                       └───┬──────────────┬─────┘
                           │              │
                ┌──────────▼──────┐   ┌───▼────────────────┐
                │  RDS Postgres    │   │ Secrets Manager    │
                │  db.t4g.micro    │   │  - alchemy_api_key │
                │  20 GB gp3       │   │  - signing_pk_pem  │
                │  private subnet  │   │  - irys_pk_pem     │
                └──────────────────┘   │  - db_password     │
                                       └────────────────────┘

                       ┌────────────────────────┐
                       │           ECR          │
                       │   aegis-monitor:<sha>  │
                       └────────────────────────┘
```

Networking:
- One VPC, two private subnets (Fargate task + RDS) and two public subnets (ALB + NAT).
- Single NAT gateway in one AZ (Phase 1a cost trade-off; not multi-AZ HA — accept the SPOF, it's a demo).
- Security groups: ALB → Fargate (port 8000), Fargate → RDS (port 5432), Fargate → 0.0.0.0/0 via NAT.

---

## Resource list (terraform modules)

| Module | Resource | Notes |
|---|---|---|
| `network` | VPC, 4 subnets, IGW, single NAT, route tables | Single NAT to keep Phase 1a costs down |
| `ecr` | One repo `aegis-monitor` with lifecycle rule | Keep last 10 untagged images, 30 tagged |
| `secrets` | Four Secrets Manager entries | Values populated out-of-band — see "Operator inputs" |
| `rds` | One `db.t4g.micro` Postgres 16 instance, 20 GB gp3, private subnet group | No multi-AZ for Phase 1a |
| `alb` | ALB, HTTPS listener (443), HTTP→HTTPS redirect (80), ACM cert via DNS validation | One target group, /health check |
| `ecs` | Cluster, task definition, service, IAM exec + task roles | Service depends on initial image existing in ECR |
| `route53` | Hosted zone reference + A-record alias to ALB | Hosted zone assumed pre-existing, see Operator inputs |
| `observability` | CloudWatch log group, basic metric alarms | Alarms: 5xx rate, RDS CPU, Arweave queue depth (custom metric from app) |

Total monthly cost estimate (us-west-2, on-demand, Phase 1a steady state):

| Item | $/mo |
|---|---|
| Fargate task (0.5 vCPU / 1 GB, 24/7) | ~$15 |
| RDS db.t4g.micro + 20 GB gp3 + backups | ~$18 |
| ALB | ~$18 |
| NAT Gateway (single AZ) | ~$32 |
| Route 53 hosted zone | ~$0.50 |
| Secrets Manager (4 secrets, low access) | ~$2 |
| ECR storage (~2 GB) | ~$0.20 |
| CloudWatch logs (~5 GB/mo) | ~$3 |
| Data transfer (low) | ~$2 |
| **Total** | **~$90/mo** |

NAT gateway is the biggest line. If we can prove Fargate egress traffic stays under ~5 GB/mo, swapping for a NAT instance on a t4g.nano would cut ~$25/mo — defer that optimization to Phase 1a.5.

---

## Container image

Multi-stage Dockerfile (`agent/Dockerfile`):

```dockerfile
# ---- builder
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*
COPY agent/pyproject.toml agent/uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY agent/aegis_monitor ./aegis_monitor

# ---- runtime
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 10001 --shell /usr/sbin/nologin aegis
WORKDIR /app
COPY --from=builder /app /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH=/app/.venv/bin:$PATH
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3); sys.exit(0)" || exit 1
CMD ["uvicorn", "aegis_monitor.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Notes:
- Non-root user, no shell.
- `uv` for dependency install (matches the agent's existing tooling).
- Healthcheck endpoint: `aegis-monitor` already exposes `/health` (per #21). Confirm before merge.

---

## Configuration model

Twelve-factor: all configuration via environment variables, secret values via Secrets Manager references that ECS resolves at task boot.

| Env var | Source | Example |
|---|---|---|
| `DATABASE_URL` | Constructed in task-def from RDS endpoint + secret | `postgresql://aegis:***@<rds>/aegis` |
| `ALCHEMY_API_KEY` | Secrets Manager `aegis/monitor/alchemy_api_key` | (operator-supplied) |
| `SIGNING_PRIVATE_KEY_PEM` | Secrets Manager `aegis/monitor/signing_pk_pem` | (generated at install) |
| `IRYS_PRIVATE_KEY_PEM` | Secrets Manager `aegis/monitor/irys_pk_pem` | (generated at install) |
| `ARWEAVE_IDENTITY_TX_ID` | Plain task-def env var | `<tx_id from upload-agent-identity.py>` |
| `LOG_LEVEL` | Plain task-def env var | `INFO` |
| `AWS_REGION` | Plain task-def env var | `us-west-2` |

The agent code already supports env-var config (per #21 task 7). New for this deploy: `IRYS_PRIVATE_KEY_PEM` and `ARWEAVE_IDENTITY_TX_ID` for the Arweave writer task.

---

## Deploy flow (first deploy)

1. **One-time bootstrap (Jonto, on laptop):**
   - `cd infra/terraform && terraform init` (uses S3 backend; bucket name from `infra/terraform/backend.tf`).
   - `terraform apply -target=module.ecr` to create the ECR repo before the first image push.
2. **Build + push image (Jonto, on laptop):**
   - `docker build -t aegis-monitor:bootstrap -f agent/Dockerfile .`
   - `aws ecr get-login-password ... | docker login ...`
   - `docker tag aegis-monitor:bootstrap <ecr-uri>:bootstrap && docker push <ecr-uri>:bootstrap`
3. **Generate signing + Irys keys, upload identity:**
   - `python scripts/generate-keys.py --out-dir /tmp/aegis-keys` (writes `signing_pk.pem`, `irys_pk.pem`)
   - `aws secretsmanager put-secret-value --secret-id aegis/monitor/signing_pk_pem --secret-string file:///tmp/aegis-keys/signing_pk.pem`
   - Same for `irys_pk_pem`. Wipe `/tmp/aegis-keys`.
   - `python scripts/upload-agent-identity.py --signing-key-pem <stdin> --output infra/arweave-identity.json`
   - Commit `infra/arweave-identity.json` (it contains the public tx id, not the key).
4. **Provision Alchemy key:**
   - `aws secretsmanager put-secret-value --secret-id aegis/monitor/alchemy_api_key --secret-string '<alchemy key>'`
5. **Apply remaining infra:**
   - `terraform apply` — creates VPC, RDS, ALB, ECS service. Initial task uses `:bootstrap` image.
6. **Run migrations:**
   - `aws ecs run-task ... --task-definition aegis-monitor-migrate ...` (one-shot task that runs `alembic upgrade head`).

## Deploy flow (subsequent deploys)

GitHub Actions workflow (separate commit because workflow files need elevated PAT scope — to be applied manually by Jonto, see "Workflow YAML for Jonto to apply" in the #23 comment):

- Trigger: push to `main` touching `agent/**`.
- Steps:
  1. Build image, tag `<short-sha>`.
  2. Push to ECR.
  3. Render new task-def revision with `image = <ecr-uri>:<short-sha>`.
  4. `aws ecs update-service --force-new-deployment` to roll the service.
- Rollback: `terraform apply -var image_tag=<previous-sha>`.

---

## Key rotation runbook

Per the #23 issue body. Implementation:

```bash
# scripts/rotate-agent-key.sh
set -euo pipefail
NEW_KEY=$(mktemp)
python scripts/generate-keys.py --signing-only --out "$NEW_KEY"

# 1. Upload new key as a new secret version (old version still active)
aws secretsmanager put-secret-value \
  --secret-id aegis/monitor/signing_pk_pem \
  --secret-string "file://$NEW_KEY"

# 2. Anchor the new pubkey identity statement on Arweave (supersedes old)
python scripts/upload-agent-identity.py \
  --signing-key-pem "file://$NEW_KEY" \
  --supersedes "$(jq -r .arweave_tx_id infra/arweave-identity.json)" \
  --output infra/arweave-identity.json

# 3. Roll the Fargate service so it picks up AWSCURRENT
aws ecs update-service --cluster aegis --service aegis-monitor --force-new-deployment

shred -u "$NEW_KEY"
git add infra/arweave-identity.json
git commit -m "infra: rotate agent signing key (supersedes prior identity tx)"
```

Old attestations remain verifiable: each `Attestation` body carries the signer address it was signed under, and the chain of identity statements on Arweave establishes which pubkey was authoritative at any historical timestamp.

---

## Operator inputs (still needed from Jonto before terraform apply)

These are the only inputs that don't have a defensible default. Everything else is in the spec.

1. **AWS account ID** — terraform `account_id` variable, used for ECR URIs and IAM policy ARNs.
2. **Domain** — base hosted zone (e.g. `aegischain.xyz`). The deploy will create `monitor.<domain>` A-record. If the hosted zone doesn't exist yet, Jonto needs to either register the domain or hand over a delegation set so terraform can create it.
3. **Alchemy API key** — operator-supplied secret. Free tier is fine for demo; paid tier needed once we cross 30 RPS sustained.
4. **Terraform state backend bucket** — name of the S3 bucket that holds `terraform.tfstate`. Bob will create the bucket if it doesn't exist (one-shot, outside the main terraform plan, to avoid the chicken-and-egg).

Bob assumes:
- **Region:** `us-west-2` (close to Jonto, close to Alchemy us-west endpoints). Override with `aws_region` tfvar if wrong.
- **AWS access model:** first deploy is `terraform apply` from Jonto's laptop using a long-lived IAM user. OIDC GitHub Actions deploy role is Phase 1a.5 — wired in once we have a known-good deploy and want to stop running secrets through laptops.

---

## Open risks / things to watch after first deploy

- **NAT cost surprise.** If Alchemy's WS keeps a long-lived connection that pumps a lot of egress, NAT data transfer ($0.045/GB) can dwarf the compute bill. Plan to add a CloudWatch alarm on NAT bytes and revisit if it climbs.
- **RDS sizing.** `db.t4g.micro` has burstable CPU credits. Steady ~10 flags/min is well within budget, but a sustained attack burst could exhaust credits. Track `BurstBalance` metric for the first month and upsize to `db.t4g.small` if it dips below 50%.
- **Single Fargate task SPOF.** Acceptable for demo; flag for upgrade once we want SLAs.
- **Workflow file deploy.** GitHub Actions YAML can't be pushed by Bob (PAT lacks `workflow` scope). The workflow file ships in a separate commit by Jonto.

---

## Migration to OIDC GHA deploy role (Phase 1a.5)

Sketch, not in scope for first ship:

1. Add `aws_iam_openid_connect_provider` for `token.actions.githubusercontent.com` to terraform.
2. Add a deploy role with `sts:AssumeRoleWithWebIdentity` trust policy scoped to `repo:jon-tompkins/aegis-public:ref:refs/heads/main`.
3. GHA workflow uses `aws-actions/configure-aws-credentials` with the role ARN.
4. Revoke the laptop IAM user's deploy permissions.
