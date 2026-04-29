variable "service_name" { type = string }
variable "region"       { type = string }

# Single VPC, two AZs, single NAT — Phase 1a cost-conscious topology.
# When we want HA we add a NAT per AZ and flip RDS to multi-AZ.
#
# This skeleton uses the well-maintained terraform-aws-modules/vpc community
# module instead of hand-rolling subnets/NAT/route tables. Pin the version.

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.13"

  name = "${var.service_name}-vpc"
  cidr = "10.20.0.0/16"

  azs             = ["${var.region}a", "${var.region}b"]
  public_subnets  = ["10.20.0.0/24", "10.20.1.0/24"]
  private_subnets = ["10.20.10.0/24", "10.20.11.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = true   # Phase 1a: single NAT in one AZ. Cost > HA at this stage.
  one_nat_gateway_per_az = false

  enable_dns_hostnames = true
  enable_dns_support   = true
}

output "vpc_id"             { value = module.vpc.vpc_id }
output "public_subnet_ids"  { value = module.vpc.public_subnets }
output "private_subnet_ids" { value = module.vpc.private_subnets }
