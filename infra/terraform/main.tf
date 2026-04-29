locals {
  service_name = "aegis-monitor"
  fqdn         = "monitor.${var.domain}"
}

module "network" {
  source = "./modules/network"

  service_name = local.service_name
  region       = var.aws_region
}

module "ecr" {
  source = "./modules/ecr"

  service_name = local.service_name
}

module "secrets" {
  source = "./modules/secrets"

  service_name = local.service_name
  # Secret values are populated out-of-band via `aws secretsmanager put-secret-value`
  # so they never touch the terraform state. See README.md.
}

module "rds" {
  source = "./modules/rds"

  service_name        = local.service_name
  vpc_id              = module.network.vpc_id
  private_subnet_ids  = module.network.private_subnet_ids
  fargate_security_group_id = module.ecs.task_security_group_id
  db_password_secret_arn    = module.secrets.db_password_arn
}

module "alb" {
  source = "./modules/alb"

  service_name      = local.service_name
  vpc_id            = module.network.vpc_id
  public_subnet_ids = module.network.public_subnet_ids
  fqdn              = local.fqdn
  route53_zone_id   = var.route53_zone_id
}

module "ecs" {
  source = "./modules/ecs"

  service_name           = local.service_name
  region                 = var.aws_region
  vpc_id                 = module.network.vpc_id
  private_subnet_ids     = module.network.private_subnet_ids
  alb_target_group_arn   = module.alb.target_group_arn
  alb_security_group_id  = module.alb.security_group_id

  image_uri              = "${module.ecr.repository_url}:${var.image_tag}"
  log_group_name         = module.observability.log_group_name

  database_url           = module.rds.connection_url
  alchemy_secret_arn     = module.secrets.alchemy_arn
  signing_pk_secret_arn  = module.secrets.signing_pk_arn
  irys_pk_secret_arn     = module.secrets.irys_pk_arn

  arweave_identity_tx_id = var.arweave_identity_tx_id
  log_level              = var.log_level
}

module "route53" {
  source = "./modules/route53"

  zone_id            = var.route53_zone_id
  fqdn               = local.fqdn
  alb_dns_name       = module.alb.dns_name
  alb_zone_id        = module.alb.zone_id
}

module "observability" {
  source = "./modules/observability"

  service_name = local.service_name
}
