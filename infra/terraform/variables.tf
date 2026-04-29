# Operator inputs — set in terraform.tfvars (gitignored).
variable "aws_account_id" {
  description = "AWS account that owns the deploy. Used in IAM policy ARNs."
  type        = string
}

variable "aws_region" {
  description = "AWS region. us-west-2 default — close to Alchemy us-west endpoints + Jonto PT timezone."
  type        = string
  default     = "us-west-2"
}

variable "domain" {
  description = "Base domain for the public URL (e.g. \"aegischain.xyz\"). Monitor will be served at monitor.<domain>."
  type        = string
}

variable "route53_zone_id" {
  description = "Existing Route 53 hosted-zone ID for `var.domain`. Hosted zone is assumed pre-created so this skeleton doesn't have to register a domain."
  type        = string
}

variable "image_tag" {
  description = "ECR image tag to deploy. Defaults to `bootstrap` for the first apply; CI rolls this on every push."
  type        = string
  default     = "bootstrap"
}

variable "log_level" {
  description = "Application log level."
  type        = string
  default     = "INFO"
}

variable "arweave_identity_tx_id" {
  description = "Arweave tx id of the agent's signed identity statement (from scripts/upload-agent-identity.py). Surfaced via /agent-identity."
  type        = string
  default     = ""  # set after first identity upload
}
