# DNS and SSL Configuration for AutoDMCA Platform

# ACM Certificate for HTTPS
resource "aws_acm_certificate" "main" {
  count = var.domain_name != "" ? 1 : 0

  domain_name               = var.domain_name
  subject_alternative_names = [
    "*.${var.domain_name}",
    "app.${var.domain_name}",
    "api.${var.domain_name}",
    "grafana.${var.domain_name}",
    "prometheus.${var.domain_name}"
  ]

  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ssl-certificate"
    Component = "security"
  })
}

# Route53 records for certificate validation
resource "aws_route53_record" "cert_validation" {
  count = var.domain_name != "" ? length(aws_acm_certificate.main[0].domain_validation_options) : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = tolist(aws_acm_certificate.main[0].domain_validation_options)[count.index].resource_record_name
  type    = tolist(aws_acm_certificate.main[0].domain_validation_options)[count.index].resource_record_type
  records = [tolist(aws_acm_certificate.main[0].domain_validation_options)[count.index].resource_record_value]
  ttl     = 60

  depends_on = [aws_acm_certificate.main]
}

# Certificate validation
resource "aws_acm_certificate_validation" "main" {
  count = var.domain_name != "" ? 1 : 0

  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = aws_route53_record.cert_validation[*].fqdn

  timeouts {
    create = "5m"
  }

  depends_on = [aws_route53_record.cert_validation]
}

# Route53 records for the main application
resource "aws_route53_record" "main" {
  count = var.domain_name != "" ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.enable_cloudfront ? aws_cloudfront_distribution.main[0].domain_name : module.alb.lb_dns_name
    zone_id                = var.enable_cloudfront ? aws_cloudfront_distribution.main[0].hosted_zone_id : module.alb.lb_zone_id
    evaluate_target_health = false
  }

  depends_on = [
    aws_acm_certificate_validation.main,
    module.alb
  ]
}

# Route53 record for app subdomain
resource "aws_route53_record" "app" {
  count = var.domain_name != "" ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "app.${var.domain_name}"
  type    = "A"

  alias {
    name                   = var.enable_cloudfront ? aws_cloudfront_distribution.main[0].domain_name : module.alb.lb_dns_name
    zone_id                = var.enable_cloudfront ? aws_cloudfront_distribution.main[0].hosted_zone_id : module.alb.lb_zone_id
    evaluate_target_health = false
  }

  depends_on = [
    aws_acm_certificate_validation.main,
    module.alb
  ]
}

# Route53 record for API subdomain
resource "aws_route53_record" "api" {
  count = var.domain_name != "" ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "api.${var.domain_name}"
  type    = "A"

  alias {
    name                   = module.alb.lb_dns_name
    zone_id                = module.alb.lb_zone_id
    evaluate_target_health = true
  }

  depends_on = [
    aws_acm_certificate_validation.main,
    module.alb
  ]
}

# Route53 record for Grafana monitoring
resource "aws_route53_record" "grafana" {
  count = var.domain_name != "" ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "grafana.${var.domain_name}"
  type    = "A"

  alias {
    name                   = module.alb.lb_dns_name
    zone_id                = module.alb.lb_zone_id
    evaluate_target_health = true
  }

  depends_on = [
    aws_acm_certificate_validation.main,
    module.alb
  ]
}

# Route53 record for Prometheus (internal access only)
resource "aws_route53_record" "prometheus" {
  count = var.domain_name != "" && var.environment != "production" ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "prometheus.${var.domain_name}"
  type    = "A"

  alias {
    name                   = module.alb.lb_dns_name
    zone_id                = module.alb.lb_zone_id
    evaluate_target_health = true
  }

  depends_on = [
    aws_acm_certificate_validation.main,
    module.alb
  ]
}

# Health check for the main domain
resource "aws_route53_health_check" "main" {
  count = var.domain_name != "" && var.environment == "production" ? 1 : 0

  fqdn                            = var.domain_name
  port                            = 443
  type                            = "HTTPS_STR_MATCH"
  resource_path                   = "/health"
  failure_threshold               = "3"
  request_interval                = "30"
  search_string                   = "healthy"
  cloudwatch_alarm_region         = var.aws_region
  cloudwatch_alarm_name           = "${local.name_prefix}-health-check-failed"
  insufficient_data_health_status = "Failure"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-check"
  })
}

# CloudWatch alarm for health check failure
resource "aws_cloudwatch_metric_alarm" "health_check_failed" {
  count = var.domain_name != "" && var.environment == "production" ? 1 : 0

  alarm_name          = "${local.name_prefix}-health-check-failed"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HealthCheckStatus"
  namespace           = "AWS/Route53"
  period              = "60"
  statistic           = "Minimum"
  threshold           = "1"
  alarm_description   = "This metric monitors the health check status"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    HealthCheckId = aws_route53_health_check.main[0].id
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-health-check-alarm"
  })
}

# Route53 query logging (for production environments)
resource "aws_route53_query_log" "main" {
  count = var.domain_name != "" && var.environment == "production" ? 1 : 0

  depends_on = [aws_cloudwatch_log_group.route53_query_log]

  zone_id                  = data.aws_route53_zone.main[0].zone_id
  cloudwatch_log_group_arn = aws_cloudwatch_log_group.route53_query_log[0].arn
}

resource "aws_cloudwatch_log_group" "route53_query_log" {
  count = var.domain_name != "" && var.environment == "production" ? 1 : 0

  name              = "/aws/route53/${var.domain_name}"
  retention_in_days = var.log_retention_in_days
  kms_key_id        = aws_kms_key.main.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-route53-query-logs"
    Component = "dns"
  })
}

# Local zones optimization (if available in region)
data "aws_availability_zones" "local_zones" {
  all_availability_zones = true

  filter {
    name   = "opt-in-status"
    values = ["opted-in", "opt-in-not-required"]
  }

  filter {
    name   = "zone-type"
    values = ["local-zone"]
  }
}

# Create additional ALB in local zone for ultra-low latency (production only)
resource "aws_lb" "local_zone" {
  count = var.environment == "production" && length(data.aws_availability_zones.local_zones.names) > 0 ? 1 : 0

  name               = "${local.name_prefix}-local-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = module.vpc.public_subnets

  enable_deletion_protection       = var.enable_deletion_protection
  enable_cross_zone_load_balancing = true
  enable_http2                     = true

  access_logs {
    bucket  = aws_s3_bucket.alb_logs.id
    prefix  = "local-zone-alb"
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-local-zone-alb"
    Component = "load-balancer"
    Zone = "local"
  })
}

# Route53 weighted routing for traffic distribution
resource "aws_route53_record" "weighted_main" {
  count = var.domain_name != "" && var.environment == "production" && length(data.aws_availability_zones.local_zones.names) > 0 ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "api-weighted.${var.domain_name}"
  type    = "A"

  set_identifier = "main-region"
  
  weighted_routing_policy {
    weight = 80
  }

  alias {
    name                   = module.alb.lb_dns_name
    zone_id                = module.alb.lb_zone_id
    evaluate_target_health = true
  }

  health_check_id = aws_route53_health_check.main[0].id
}

resource "aws_route53_record" "weighted_local" {
  count = var.domain_name != "" && var.environment == "production" && length(data.aws_availability_zones.local_zones.names) > 0 ? 1 : 0

  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "api-weighted.${var.domain_name}"
  type    = "A"

  set_identifier = "local-zone"
  
  weighted_routing_policy {
    weight = 20
  }

  alias {
    name                   = aws_lb.local_zone[0].dns_name
    zone_id                = aws_lb.local_zone[0].zone_id
    evaluate_target_health = true
  }
}