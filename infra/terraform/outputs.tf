output "monitor_url" {
  description = "Public HTTPS URL for the monitor API."
  value       = "https://${local.fqdn}"
}

output "ecr_repository_url" {
  description = "ECR URI to push the aegis-monitor image to."
  value       = module.ecr.repository_url
}

output "rds_endpoint" {
  description = "RDS Postgres endpoint (private — only reachable from Fargate task SG)."
  value       = module.rds.endpoint
  sensitive   = true
}

output "log_group_name" {
  description = "CloudWatch log group for application logs."
  value       = module.observability.log_group_name
}
