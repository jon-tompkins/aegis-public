provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "aegis"
      Phase     = "1a"
      ManagedBy = "terraform"
      Repo      = "jon-tompkins/aegis-public"
    }
  }
}
