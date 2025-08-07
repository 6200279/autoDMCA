# Outputs for AutoDMCA Infrastructure

# Network outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "database_subnets" {
  description = "Database subnet IDs"
  value       = module.vpc.database_subnets
}

# EKS outputs
output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
  sensitive   = true
}

output "eks_cluster_version" {
  description = "EKS cluster version"
  value       = module.eks.cluster_version
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = module.eks.cluster_arn
}

output "eks_cluster_certificate_authority_data" {
  description = "EKS cluster certificate authority data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "eks_cluster_oidc_issuer_url" {
  description = "EKS cluster OIDC issuer URL"
  value       = module.eks.cluster_oidc_issuer_url
}

output "eks_node_groups" {
  description = "EKS node group details"
  value       = module.eks.eks_managed_node_groups
}

# Database outputs
output "rds_instance_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
  sensitive   = true
}

output "rds_instance_port" {
  description = "RDS instance port"
  value       = module.rds.db_instance_port
}

output "rds_instance_identifier" {
  description = "RDS instance identifier"
  value       = module.rds.db_instance_identifier
}

output "rds_instance_arn" {
  description = "RDS instance ARN"
  value       = module.rds.db_instance_arn
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.db_instance_name
}

output "rds_username" {
  description = "RDS master username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

# Redis outputs
output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = module.redis.cluster_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = module.redis.port
}

output "redis_cluster_id" {
  description = "Redis cluster ID"
  value       = module.redis.cluster_id
}

# Load Balancer outputs
output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.lb_dns_name
}

output "alb_zone_id" {
  description = "ALB zone ID"
  value       = module.alb.lb_zone_id
}

output "alb_arn" {
  description = "ALB ARN"
  value       = module.alb.lb_arn
}

output "alb_target_groups" {
  description = "ALB target group ARNs"
  value       = module.alb.target_group_arns
}

# S3 outputs
output "s3_uploads_bucket_name" {
  description = "S3 uploads bucket name"
  value       = module.s3_uploads.s3_bucket_id
}

output "s3_uploads_bucket_arn" {
  description = "S3 uploads bucket ARN"
  value       = module.s3_uploads.s3_bucket_arn
}

output "s3_uploads_bucket_domain_name" {
  description = "S3 uploads bucket domain name"
  value       = module.s3_uploads.s3_bucket_bucket_domain_name
}

output "s3_alb_logs_bucket_name" {
  description = "S3 ALB logs bucket name"
  value       = aws_s3_bucket.alb_logs.id
}

# CloudFront outputs
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.main[0].id : null
}

output "cloudfront_distribution_domain_name" {
  description = "CloudFront distribution domain name"
  value       = var.enable_cloudfront ? aws_cloudfront_distribution.main[0].domain_name : null
}

# SSL Certificate outputs
output "acm_certificate_arn" {
  description = "ACM certificate ARN"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].arn : null
}

output "acm_certificate_status" {
  description = "ACM certificate validation status"
  value       = var.domain_name != "" ? aws_acm_certificate_validation.main[0].certificate_arn : null
}

# Security outputs
output "kms_key_arns" {
  description = "KMS key ARNs"
  value = {
    main        = aws_kms_key.main.arn
    rds         = aws_kms_key.rds.arn
    elasticache = aws_kms_key.elasticache.arn
    s3          = aws_kms_key.s3.arn
    eks         = aws_kms_key.eks.arn
  }
  sensitive = true
}

output "security_group_ids" {
  description = "Security group IDs"
  value = {
    alb        = aws_security_group.alb.id
    rds        = aws_security_group.rds.id
    redis      = aws_security_group.redis.id
    bastion    = aws_security_group.bastion.id
    eks_remote = aws_security_group.eks_remote_access.id
  }
}

# Monitoring outputs
output "sns_topic_arn" {
  description = "SNS topic ARN for alerts"
  value       = aws_sns_topic.alerts.arn
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    application = aws_cloudwatch_log_group.application.name
    alb         = aws_cloudwatch_log_group.alb.name
    rds         = aws_cloudwatch_log_group.rds.name
  }
}

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

# Backup outputs
output "backup_vault_arn" {
  description = "AWS Backup vault ARN"
  value       = aws_backup_vault.main.arn
}

output "backup_plan_arn" {
  description = "AWS Backup plan ARN"
  value       = aws_backup_plan.main.arn
}

# EFS outputs (if enabled)
output "efs_id" {
  description = "EFS file system ID"
  value       = var.environment == "production" ? aws_efs_file_system.main[0].id : null
}

output "efs_dns_name" {
  description = "EFS DNS name"
  value       = var.environment == "production" ? aws_efs_file_system.main[0].dns_name : null
}

# WAF outputs
output "waf_web_acl_arn" {
  description = "WAF web ACL ARN"
  value       = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : null
}

# Secrets Manager / Systems Manager outputs
output "parameter_store_keys" {
  description = "Systems Manager Parameter Store keys for secrets"
  value = {
    db_password     = aws_ssm_parameter.db_password.name
    redis_auth      = var.enable_elasticache_auth ? aws_ssm_parameter.redis_auth_token[0].name : null
    eks_private_key = aws_ssm_parameter.eks_nodes_private_key.name
  }
  sensitive = true
}

# Useful connection information
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "database_connection_string" {
  description = "Database connection string template"
  value       = "postgresql://${module.rds.db_instance_username}:PASSWORD@${module.rds.db_instance_endpoint}:${module.rds.db_instance_port}/${module.rds.db_instance_name}"
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string template"
  value       = var.enable_elasticache_auth ? "redis://AUTH_TOKEN@${module.redis.cluster_address}:${module.redis.port}" : "redis://${module.redis.cluster_address}:${module.redis.port}"
  sensitive   = true
}

# Environment-specific information
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

# Resource naming
output "name_prefix" {
  description = "Naming prefix used for resources"
  value       = local.name_prefix
}

output "common_tags" {
  description = "Common tags applied to all resources"
  value       = local.common_tags
}