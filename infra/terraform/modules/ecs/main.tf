variable "service_name"           { type = string }
variable "region"                 { type = string }
variable "vpc_id"                 { type = string }
variable "private_subnet_ids"     { type = list(string) }
variable "alb_target_group_arn"   { type = string }
variable "alb_security_group_id"  { type = string }
variable "image_uri"              { type = string }
variable "log_group_name"         { type = string }
variable "database_url" {
  type      = string
  sensitive = true
}
variable "alchemy_secret_arn"     { type = string }
variable "signing_pk_secret_arn"  { type = string }
variable "irys_pk_secret_arn"     { type = string }
variable "arweave_identity_tx_id" { type = string }
variable "log_level"              { type = string }

resource "aws_ecs_cluster" "this" {
  name = var.service_name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_security_group" "task" {
  name        = "${var.service_name}-task"
  description = "Fargate task — accept 8000 from ALB only."
  vpc_id      = var.vpc_id
}

resource "aws_security_group_rule" "task_ingress_alb" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  security_group_id        = aws_security_group.task.id
  source_security_group_id = var.alb_security_group_id
}

resource "aws_security_group_rule" "task_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.task.id
  cidr_blocks       = ["0.0.0.0/0"]
}

# IAM — execution role pulls image + secrets at task boot.
resource "aws_iam_role" "exec" {
  name = "${var.service_name}-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "exec_managed" {
  role       = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "exec_secrets" {
  role = aws_iam_role.exec.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        var.alchemy_secret_arn,
        var.signing_pk_secret_arn,
        var.irys_pk_secret_arn,
      ]
    }]
  })
}

# Task role — what the running app can do at runtime. Phase 1a: nothing AWS-side.
resource "aws_iam_role" "task" {
  name = "${var.service_name}-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_ecs_task_definition" "this" {
  family                   = var.service_name
  cpu                      = "512"   # 0.5 vCPU
  memory                   = "1024"  # 1 GB
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.exec.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = var.service_name
    image     = var.image_uri
    essential = true
    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "DATABASE_URL",            value = var.database_url },
      { name = "LOG_LEVEL",               value = var.log_level },
      { name = "AWS_REGION",              value = var.region },
      { name = "ARWEAVE_IDENTITY_TX_ID",  value = var.arweave_identity_tx_id },
    ]
    secrets = [
      { name = "ALCHEMY_API_KEY",          valueFrom = var.alchemy_secret_arn },
      { name = "SIGNING_PRIVATE_KEY_PEM",  valueFrom = var.signing_pk_secret_arn },
      { name = "IRYS_PRIVATE_KEY_PEM",     valueFrom = var.irys_pk_secret_arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = var.log_group_name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = var.service_name
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 30
    }
  }])
}

resource "aws_ecs_service" "this" {
  name            = var.service_name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = var.service_name
    container_port   = 8000
  }

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  lifecycle {
    # CI rolls the task def via aws ecs update-service; ignore the drift.
    ignore_changes = [task_definition]
  }
}

output "task_security_group_id" {
  value = aws_security_group.task.id
}
