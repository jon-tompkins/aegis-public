# S3 backend for terraform state.
# The bucket itself is created out-of-band before `terraform init` — see README.md.
terraform {
  required_version = ">= 1.6"

  backend "s3" {
    # NOTE: backend config can't reference vars. Override at init time:
    #   terraform init -backend-config="bucket=<your-tf-state-bucket>"
    bucket  = "aegis-tfstate-CHANGEME"
    key     = "phase-1a/terraform.tfstate"
    region  = "us-west-2"
    encrypt = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
