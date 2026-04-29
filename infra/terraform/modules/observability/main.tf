variable "service_name" { type = string }

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.service_name}"
  retention_in_days = 30
}

# Phase 1a alarms: 5xx burst from ALB, RDS CPU sustained, ECS task crash loop.
# Custom app metrics (arweave_writer_queue_depth, arweave_wallet_balance_usd)
# are emitted from app code via embedded metric format and get their own alarms
# in a follow-up commit once the app is publishing them.

# TODO(bob): wire 5xx alarm to ALB target group ARN once ECS module exposes it back.
# TODO(bob): wire RDS CPU alarm to db_instance_identifier from RDS module.

output "log_group_name" {
  value = aws_cloudwatch_log_group.app.name
}

output "log_group_arn" {
  value = aws_cloudwatch_log_group.app.arn
}
