variable "service_name"              { type = string }
variable "vpc_id"                    { type = string }
variable "private_subnet_ids"        { type = list(string) }
variable "fargate_security_group_id" { type = string }
variable "db_password_secret_arn"    { type = string }

# Pull the password value from Secrets Manager so it never lives in tfvars/state.
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = var.db_password_secret_arn
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.service_name}-db"
  subnet_ids = var.private_subnet_ids
}

resource "aws_security_group" "rds" {
  name        = "${var.service_name}-rds"
  description = "RDS Postgres — accept 5432 from Fargate task SG only."
  vpc_id      = var.vpc_id
}

resource "aws_security_group_rule" "rds_ingress_fargate" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = var.fargate_security_group_id
}

resource "aws_db_instance" "this" {
  identifier             = "${var.service_name}-pg"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  storage_type           = "gp3"
  storage_encrypted      = true
  db_name                = "aegis"
  username               = "aegis"
  password               = data.aws_secretsmanager_secret_version.db_password.secret_string
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false
  backup_retention_period = 7
  skip_final_snapshot    = false
  final_snapshot_identifier = "${var.service_name}-pg-final"
  deletion_protection    = true

  # Phase 1a: single AZ. Flip to true when we care about RDS HA.
  multi_az = false
}

output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "connection_url" {
  # Used by ECS task-def. Note the password is interpolated from the SM data
  # source, so it lives in state — acceptable for Phase 1a; Phase 1b should
  # pass the URL through Secrets Manager too.
  value     = "postgresql://${aws_db_instance.this.username}:${data.aws_secretsmanager_secret_version.db_password.secret_string}@${aws_db_instance.this.endpoint}/${aws_db_instance.this.db_name}"
  sensitive = true
}
