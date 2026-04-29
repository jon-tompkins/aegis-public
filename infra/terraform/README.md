# Aegis — Phase 1a Terraform

Skeleton for the Phase 1a deploy described in [`../../docs/specs/phase-1a-deploy.md`](../../docs/specs/phase-1a-deploy.md).

**Status:** scaffold only — modules contain enough structure to demonstrate the intended shape. Resource bodies marked `# TODO(bob)` need to be filled in before first apply. Don't run `terraform apply` against this until those TODOs are resolved.

## Layout

```
infra/terraform/
├── README.md                 ← you are here
├── backend.tf                ← S3 state backend
├── providers.tf              ← AWS provider, default tags
├── main.tf                   ← module wiring
├── variables.tf              ← root inputs (account_id, domain, etc.)
├── outputs.tf                ← public URL, ECR URI, etc.
├── terraform.tfvars.example  ← fill in and copy to terraform.tfvars (gitignored)
└── modules/
    ├── network/              ← VPC + subnets + NAT
    ├── ecr/                  ← container registry
    ├── secrets/              ← Secrets Manager entries (empty values)
    ├── rds/                  ← Postgres
    ├── alb/                  ← ALB + ACM cert
    ├── ecs/                  ← Fargate cluster, task def, service
    ├── route53/              ← A-record alias to ALB
    └── observability/        ← CloudWatch logs + alarms
```

## First-time setup

1. Copy `terraform.tfvars.example` → `terraform.tfvars` and fill in the four operator inputs (`aws_account_id`, `domain`, `route53_zone_id`, `tf_state_bucket`).
2. Create the S3 state bucket out-of-band (chicken-and-egg with the backend):
   ```bash
   aws s3api create-bucket \
     --bucket "$(terraform output -raw tf_state_bucket || echo aegis-tfstate-CHANGEME)" \
     --region us-west-2 \
     --create-bucket-configuration LocationConstraint=us-west-2
   aws s3api put-bucket-versioning \
     --bucket aegis-tfstate-CHANGEME \
     --versioning-configuration Status=Enabled
   ```
3. `terraform init`
4. `terraform apply -target=module.ecr` — gets the registry up so you can push the bootstrap image.
5. Build + push the bootstrap image (see `phase-1a-deploy.md` §Deploy flow).
6. Populate secrets:
   ```bash
   aws secretsmanager put-secret-value --secret-id aegis/monitor/alchemy_api_key --secret-string '<key>'
   aws secretsmanager put-secret-value --secret-id aegis/monitor/signing_pk_pem  --secret-string file://signing_pk.pem
   aws secretsmanager put-secret-value --secret-id aegis/monitor/irys_pk_pem     --secret-string file://irys_pk.pem
   ```
7. `terraform apply` — provisions everything else.
8. Run migrations as a one-shot Fargate task (see deploy spec).

## Cost estimate

~$90/mo steady state — see `phase-1a-deploy.md` §Resource list.

## What's deliberately NOT in here

- Multi-AZ RDS, multi-region anything, CloudFront, WAF — Phase 1a is a demo, not a production tier.
- HSM/KMS-wrapped signing key — plain Secrets Manager for Phase 1a.
- GitHub Actions OIDC deploy role — Phase 1a.5.
- The CI workflow file itself — that ships in a separate commit by Jonto (PAT scope limitation, see `reference_aegis_project.md` in agent memory).
