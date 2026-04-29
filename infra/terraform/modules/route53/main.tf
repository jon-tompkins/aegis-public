variable "zone_id"      { type = string }
variable "fqdn"         { type = string }
variable "alb_dns_name" { type = string }
variable "alb_zone_id"  { type = string }

resource "aws_route53_record" "monitor" {
  zone_id = var.zone_id
  name    = var.fqdn
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}
