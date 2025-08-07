# Variables for Content Protection Platform infrastructure

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "content-protection"
}

variable "owner" {
  description = "Project owner"
  type        = string
  default     = "platform-team"
}

# Terraform state configuration
variable "terraform_state_bucket" {
  description = "S3 bucket for Terraform state"
  type        = string
}

variable "terraform_lock_table" {
  description = "DynamoDB table for Terraform state locking"
  type        = string
}

# Network configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use single NAT Gateway (cost optimization for non-production)"
  type        = bool
  default     = false
}

# EKS configuration
variable "eks_cluster_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.28"
}

variable "eks_node_instance_types" {
  description = "Instance types for EKS worker nodes"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "eks_node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "eks_node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 10
}

variable "eks_node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

# RDS configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage for RDS instance (GB)"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for RDS autoscaling (GB)"
  type        = number
  default     = 100
}

variable "db_backup_retention_period" {
  description = "Database backup retention period (days)"
  type        = number
  default     = 7
}

variable "db_backup_window" {
  description = "Database backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Database maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "db_deletion_protection" {
  description = "Enable RDS deletion protection"
  type        = bool
  default     = true
}

variable "db_skip_final_snapshot" {
  description = "Skip final snapshot when destroying"
  type        = bool
  default     = false
}

# ElastiCache configuration
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1
}

variable "redis_parameter_group_name" {
  description = "Redis parameter group"
  type        = string
  default     = "default.redis7"
}

# Load balancer configuration
variable "load_balancer_type" {
  description = "Type of load balancer (application or network)"
  type        = string
  default     = "application"
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for ALB"
  type        = bool
  default     = true
}

# SSL/TLS configuration
variable "domain_name" {
  description = "Domain name for SSL certificate"
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
  default     = ""
}

# S3 configuration
variable "s3_versioning_enabled" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "s3_lifecycle_transition_days" {
  description = "Days to transition to IA storage class"
  type        = number
  default     = 30
}

variable "s3_lifecycle_expiration_days" {
  description = "Days to expire objects"
  type        = number
  default     = 90
}

# CloudWatch configuration
variable "log_retention_in_days" {
  description = "CloudWatch log retention period"
  type        = number
  default     = 30
}

# Auto scaling configuration
variable "enable_cluster_autoscaler" {
  description = "Enable cluster autoscaler"
  type        = bool
  default     = true
}

variable "enable_horizontal_pod_autoscaler" {
  description = "Enable horizontal pod autoscaler"
  type        = bool
  default     = true
}

# Monitoring and observability
variable "enable_container_insights" {
  description = "Enable Container Insights for EKS"
  type        = bool
  default     = true
}

variable "enable_performance_insights" {
  description = "Enable Performance Insights for RDS"
  type        = bool
  default     = true
}

# Security configuration
variable "enable_security_groups_with_name_regex_all" {
  description = "Enable security groups with name regex"
  type        = bool
  default     = false
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the infrastructure"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Cost optimization
variable "enable_spot_instances" {
  description = "Enable spot instances for worker nodes"
  type        = bool
  default     = false
}

variable "spot_instance_types" {
  description = "Instance types for spot instances"
  type        = list(string)
  default     = ["t3.medium", "t3a.medium", "t2.medium"]
}

# Backup configuration
variable "backup_schedule" {
  description = "Backup schedule expression"
  type        = string
  default     = "cron(0 1 * * ? *)"
}

variable "backup_retention_days" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

# Secrets and configuration
variable "database_name" {
  description = "Database name"
  type        = string
  default     = "contentprotection"
}

variable "database_username" {
  description = "Database username"
  type        = string
  default     = "dbadmin"
}

# Feature flags
variable "enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = true
}

variable "enable_cloudfront" {
  description = "Enable CloudFront CDN"
  type        = bool
  default     = true
}

variable "enable_ses" {
  description = "Enable Amazon SES for email"
  type        = bool
  default     = true
}

variable "enable_elasticache_auth" {
  description = "Enable ElastiCache auth"
  type        = bool
  default     = true
}

# Environment specific scaling
variable "environment_config" {
  description = "Environment specific configuration"
  type = map(object({
    node_min_size     = number
    node_max_size     = number
    node_desired_size = number
    db_instance_class = string
    redis_node_type   = string
  }))
  default = {
    dev = {
      node_min_size     = 1
      node_max_size     = 3
      node_desired_size = 1
      db_instance_class = "db.t3.micro"
      redis_node_type   = "cache.t3.micro"
    }
    staging = {
      node_min_size     = 1
      node_max_size     = 5
      node_desired_size = 2
      db_instance_class = "db.t3.small"
      redis_node_type   = "cache.t3.small"
    }
    production = {
      node_min_size     = 2
      node_max_size     = 20
      node_desired_size = 3
      db_instance_class = "db.t3.medium"
      redis_node_type   = "cache.t3.medium"
    }
  }
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}