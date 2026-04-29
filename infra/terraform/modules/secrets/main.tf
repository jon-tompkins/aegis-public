variable "service_name" { type = string }

# Secret containers only — values are populated out-of-band via
# `aws secretsmanager put-secret-value` so they never enter terraform state.
# See README.md §First-time setup.

resource "aws_secretsmanager_secret" "alchemy" {
  name        = "aegis/monitor/alchemy_api_key"
  description = "Alchemy API key for the pending-tx WebSocket + JSON-RPC fallback."
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "signing_pk" {
  name        = "aegis/monitor/signing_pk_pem"
  description = "EIP-191 signing private key (PEM) for flag attestations. Rotated via scripts/rotate-agent-key.sh."
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "irys_pk" {
  name        = "aegis/monitor/irys_pk_pem"
  description = "Irys/Arweave bundler hot wallet private key (PEM)."
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "db_password" {
  name        = "aegis/monitor/db_password"
  description = "RDS Postgres master password."
  recovery_window_in_days = 7
}

output "alchemy_arn"     { value = aws_secretsmanager_secret.alchemy.arn }
output "signing_pk_arn"  { value = aws_secretsmanager_secret.signing_pk.arn }
output "irys_pk_arn"     { value = aws_secretsmanager_secret.irys_pk.arn }
output "db_password_arn" { value = aws_secretsmanager_secret.db_password.arn }
