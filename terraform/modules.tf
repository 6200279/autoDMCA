# Enhanced Infrastructure Modules for AutoDMCA Platform

# VPC Module with high availability and security
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.name_prefix}-vpc"
  cidr = local.vpc_cidr

  azs             = local.azs
  private_subnets = local.private_subnets
  public_subnets  = local.public_subnets
  database_subnets = local.database_subnets
  elasticache_subnets = local.elasticache_subnets

  # High Availability Configuration
  enable_nat_gateway   = var.enable_nat_gateway
  single_nat_gateway   = var.single_nat_gateway
  enable_vpn_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Security enhancements
  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  flow_log_destination_type            = "cloud-watch-logs"

  # Database subnet group
  create_database_subnet_group = true
  create_database_subnet_route_table = true
  create_database_internet_gateway_route = false

  # ElastiCache subnet group
  create_elasticache_subnet_group = true
  create_elasticache_subnet_route_table = true

  # Network ACLs for additional security
  manage_default_network_acl = true
  default_network_acl_tags   = { Name = "${local.name_prefix}-default" }
  
  manage_default_route_table = true
  default_route_table_tags   = { Name = "${local.name_prefix}-default" }

  manage_default_security_group = true
  default_security_group_tags   = { Name = "${local.name_prefix}-default" }

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
    Tier = "Public"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
    Tier = "Private"
  }

  database_subnet_tags = {
    Tier = "Database"
  }

  elasticache_subnet_tags = {
    Tier = "Cache"
  }

  tags = local.common_tags
}

# EKS Module with advanced configuration
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "${local.name_prefix}-eks"
  cluster_version = var.eks_cluster_version

  vpc_id                         = module.vpc.vpc_id
  subnet_ids                     = module.vpc.private_subnets
  control_plane_subnet_ids       = module.vpc.private_subnets

  # Security and access
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access_cidrs = var.allowed_cidr_blocks

  # Logging configuration
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  cloudwatch_log_group_retention_in_days = var.log_retention_in_days

  # Encryption
  cluster_encryption_config = {
    provider_key_arn = aws_kms_key.eks.arn
    resources        = ["secrets"]
  }

  # Add-ons with specific versions for stability
  cluster_addons = {
    coredns = {
      most_recent = true
      resolve_conflicts_on_create = "OVERWRITE"
      resolve_conflicts_on_update = "OVERWRITE"
    }
    kube-proxy = {
      most_recent = true
      resolve_conflicts_on_create = "OVERWRITE"
      resolve_conflicts_on_update = "OVERWRITE"
    }
    vpc-cni = {
      most_recent = true
      resolve_conflicts_on_create = "OVERWRITE"
      resolve_conflicts_on_update = "OVERWRITE"
      configuration_values = jsonencode({
        env = {
          ENABLE_PREFIX_DELEGATION = "true"
          WARM_PREFIX_TARGET       = "1"
        }
      })
    }
    aws-ebs-csi-driver = {
      most_recent = true
      resolve_conflicts_on_create = "OVERWRITE"
      resolve_conflicts_on_update = "OVERWRITE"
    }
    aws-efs-csi-driver = {
      most_recent = true
      resolve_conflicts_on_create = "OVERWRITE"
      resolve_conflicts_on_update = "OVERWRITE"
    }
  }

  # Managed Node Groups with multiple instance types for high availability
  eks_managed_node_groups = {
    # General purpose nodes for application workloads
    general = {
      name = "general"
      instance_types = var.eks_node_instance_types
      capacity_type  = "ON_DEMAND"

      min_size     = local.env_config.node_min_size
      max_size     = local.env_config.node_max_size
      desired_size = local.env_config.node_desired_size

      ami_type = "AL2_x86_64"
      platform = "linux"

      # Advanced configuration
      enable_bootstrap_user_data = false
      pre_bootstrap_user_data = <<-EOT
        export CONTAINER_RUNTIME="containerd"
        export USE_MAX_PODS=false
        export KUBELET_EXTRA_ARGS="--max-pods=110"
      EOT

      # Security
      remote_access = {
        ec2_ssh_key = aws_key_pair.eks_nodes.key_name
        source_security_group_ids = [aws_security_group.eks_remote_access.id]
      }

      # Monitoring
      enable_monitoring = true

      # Update configuration
      update_config = {
        max_unavailable_percentage = 33
      }

      # Labels and taints
      labels = {
        Environment = var.environment
        NodeGroup   = "general"
      }

      tags = merge(local.common_tags, {
        Name = "${local.name_prefix}-general-node"
      })
    }

    # High-memory nodes for image processing workloads
    high_memory = {
      name = "high-memory"
      instance_types = ["r5.large", "r5.xlarge"]
      capacity_type  = "ON_DEMAND"

      min_size     = 0
      max_size     = 5
      desired_size = 1

      ami_type = "AL2_x86_64"
      platform = "linux"

      # Taints for dedicated workloads
      taints = [
        {
          key    = "high-memory"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      ]

      labels = {
        Environment = var.environment
        NodeGroup   = "high-memory"
        Workload    = "image-processing"
      }

      tags = merge(local.common_tags, {
        Name = "${local.name_prefix}-high-memory-node"
      })
    }
  }

  # Spot instances for cost optimization (if enabled)
  dynamic "eks_managed_node_groups" {
    for_each = var.enable_spot_instances ? ["spot"] : []
    content {
      spot = {
        name = "spot"
        instance_types = var.spot_instance_types
        capacity_type  = "SPOT"

        min_size     = 0
        max_size     = 10
        desired_size = 2

        # Spot configuration
        spot_max_price = "0.05"

        labels = {
          Environment = var.environment
          NodeGroup   = "spot"
          CapacityType = "spot"
        }

        taints = [
          {
            key    = "spot-instance"
            value  = "true"
            effect = "NO_SCHEDULE"
          }
        ]

        tags = merge(local.common_tags, {
          Name = "${local.name_prefix}-spot-node"
        })
      }
    }
  }

  # IRSA (IAM Roles for Service Accounts) configuration
  enable_irsa = true

  # Cluster security group rules
  cluster_security_group_additional_rules = {
    ingress_nodes_443 = {
      description                = "Node groups to cluster API"
      protocol                   = "tcp"
      from_port                  = 443
      to_port                    = 443
      type                       = "ingress"
      source_node_security_group = true
    }
  }

  # Node security group rules
  node_security_group_additional_rules = {
    ingress_cluster_443 = {
      description                   = "Cluster API to node groups"
      protocol                      = "tcp"
      from_port                     = 443
      to_port                       = 443
      type                          = "ingress"
      source_cluster_security_group = true
    }
    ingress_cluster_kubelet = {
      description                   = "Cluster API to node kubelets"
      protocol                      = "tcp"
      from_port                     = 10250
      to_port                       = 10250
      type                          = "ingress"
      source_cluster_security_group = true
    }
    ingress_self_coredns_tcp = {
      description = "Node to node CoreDNS"
      protocol    = "tcp"
      from_port   = 53
      to_port     = 53
      type        = "ingress"
      self        = true
    }
    ingress_self_coredns_udp = {
      description = "Node to node CoreDNS UDP"
      protocol    = "udp"
      from_port   = 53
      to_port     = 53
      type        = "ingress"
      self        = true
    }
  }

  tags = local.common_tags
}

# Enhanced RDS with Multi-AZ and read replicas
module "rds" {
  source = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"

  identifier = "${local.name_prefix}-postgres"

  # Database configuration
  engine               = "postgres"
  engine_version       = "15.3"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = local.env_config.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_throughput    = 125
  storage_iops          = 3000
  storage_encrypted     = true
  kms_key_id           = aws_kms_key.rds.arn

  # Database credentials
  db_name  = var.database_name
  username = var.database_username
  password = random_password.db_password.result
  port     = local.db_port

  # High Availability
  multi_az               = var.environment == "production" ? true : false
  create_db_subnet_group = true
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Backup configuration
  backup_retention_period   = var.db_backup_retention_period
  backup_window            = var.db_backup_window
  maintenance_window       = var.db_maintenance_window
  delete_automated_backups = false
  deletion_protection      = var.db_deletion_protection
  skip_final_snapshot      = var.db_skip_final_snapshot
  final_snapshot_identifier = "${local.name_prefix}-postgres-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"

  # Monitoring and Performance
  monitoring_interval    = 60
  monitoring_role_arn   = aws_iam_role.rds_monitoring.arn
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  performance_insights_enabled = var.enable_performance_insights
  performance_insights_kms_key_id = aws_kms_key.rds.arn

  # Parameter group for optimization
  create_db_parameter_group = true
  parameter_group_name     = "${local.name_prefix}-postgres-params"
  parameters = [
    {
      name  = "log_statement"
      value = "all"
    },
    {
      name  = "log_min_duration_statement"
      value = "1000" # Log queries taking more than 1 second
    },
    {
      name  = "shared_preload_libraries"
      value = "pg_stat_statements"
    },
    {
      name  = "track_activity_query_size"
      value = "2048"
    },
    {
      name  = "wal_buffers"
      value = "16384" # 16MB
    },
    {
      name  = "checkpoint_completion_target"
      value = "0.9"
    }
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres"
    Component = "database"
  })
}

# ElastiCache Redis with clustering
module "redis" {
  source = "terraform-aws-modules/elasticache/aws"
  version = "~> 1.0"

  cluster_id           = "${local.name_prefix}-redis"
  description          = "Redis cluster for AutoDMCA platform"

  # Engine configuration
  engine               = "redis"
  engine_version       = "7.0"
  port                 = local.redis_port
  parameter_group_name = var.redis_parameter_group_name
  node_type           = local.env_config.redis_node_type

  # High availability configuration
  num_cache_nodes     = var.environment == "production" ? 3 : var.redis_num_cache_nodes
  availability_zones  = local.azs

  # Security
  subnet_group_name   = module.vpc.elasticache_subnet_group_name
  security_group_ids  = [aws_security_group.redis.id]

  # Encryption
  at_rest_encryption_enabled = true
  in_transit_encryption_enabled = true
  kms_key_id = aws_kms_key.elasticache.arn

  # Auth token if auth is enabled
  auth_token = var.enable_elasticache_auth ? random_password.redis_auth_token[0].result : null

  # Backup configuration
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:06:00"

  # Notifications
  notification_topic_arn = aws_sns_topic.alerts.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis"
    Component = "cache"
  })
}

# Application Load Balancer with WAF
module "alb" {
  source = "terraform-aws-modules/alb/aws"
  version = "~> 8.0"

  name = "${local.name_prefix}-alb"

  load_balancer_type = var.load_balancer_type
  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.public_subnets
  security_groups    = [aws_security_group.alb.id]

  # SSL/TLS Configuration
  target_groups = [
    {
      name                 = "${local.name_prefix}-backend"
      backend_protocol     = "HTTP"
      backend_port         = local.backend_port
      target_type          = "ip"
      deregistration_delay = 30
      health_check = {
        enabled             = true
        healthy_threshold   = 2
        unhealthy_threshold = 3
        timeout             = 10
        interval            = 30
        path                = "/health"
        matcher             = "200"
        port                = "traffic-port"
        protocol            = "HTTP"
      }
    },
    {
      name                 = "${local.name_prefix}-frontend"
      backend_protocol     = "HTTP"
      backend_port         = local.frontend_port
      target_type          = "ip"
      deregistration_delay = 10
      health_check = {
        enabled             = true
        healthy_threshold   = 2
        unhealthy_threshold = 3
        timeout             = 5
        interval            = 30
        path                = "/health"
        matcher             = "200"
        port                = "traffic-port"
        protocol            = "HTTP"
      }
    }
  ]

  # HTTP to HTTPS redirect
  http_tcp_listeners = [
    {
      port               = 80
      protocol           = "HTTP"
      action_type        = "redirect"
      redirect = {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  ]

  # HTTPS listeners
  https_listeners = [
    {
      port               = 443
      protocol           = "HTTPS"
      certificate_arn    = var.domain_name != "" ? aws_acm_certificate.main[0].arn : null
      target_group_index = 0
    }
  ]

  # Advanced features
  enable_deletion_protection = var.enable_deletion_protection
  enable_http2              = true
  enable_cross_zone_load_balancing = true
  idle_timeout             = 60

  # Access logging
  access_logs = {
    bucket  = aws_s3_bucket.alb_logs.id
    prefix  = "alb-access-logs"
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb"
    Component = "load-balancer"
  })
}

# S3 buckets for different purposes
module "s3_uploads" {
  source = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 3.0"

  bucket = "${local.name_prefix}-uploads-${random_suffix.this.result}"

  # Security
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  # Versioning and lifecycle
  versioning = {
    enabled = var.s3_versioning_enabled
  }

  lifecycle_configuration = {
    rule = {
      id     = "lifecycle"
      status = "Enabled"

      transition = [
        {
          days          = var.s3_lifecycle_transition_days
          storage_class = "STANDARD_IA"
        },
        {
          days          = var.s3_lifecycle_transition_days * 2
          storage_class = "GLACIER"
        }
      ]

      expiration = {
        days = var.s3_lifecycle_expiration_days
      }

      noncurrent_version_expiration = {
        noncurrent_days = 30
      }
    }
  }

  # Encryption
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = aws_kms_key.s3.arn
        sse_algorithm     = "aws:kms"
      }
      bucket_key_enabled = true
    }
  }

  # CORS for web uploads
  cors_rule = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["PUT", "POST", "GET", "DELETE", "HEAD"]
      allowed_origins = var.domain_name != "" ? ["https://${var.domain_name}", "https://app.${var.domain_name}"] : ["*"]
      expose_headers  = ["ETag"]
      max_age_seconds = 3000
    }
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-uploads"
    Component = "storage"
    Purpose = "user-uploads"
  })
}

# CloudFront distribution (if enabled)
resource "aws_cloudfront_distribution" "main" {
  count = var.enable_cloudfront ? 1 : 0

  origin {
    domain_name = module.alb.lb_dns_name
    origin_id   = "ALB-${module.alb.lb_id}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # S3 origin for static assets
  origin {
    domain_name = module.s3_uploads.s3_bucket_bucket_regional_domain_name
    origin_id   = "S3-${module.s3_uploads.s3_bucket_id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main[0].cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"

  # Caching behavior
  default_cache_behavior {
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "ALB-${module.alb.lb_id}"
    compress               = true
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      headers      = ["Host", "Origin", "Authorization"]
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  # API cache behavior
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "ALB-${module.alb.lb_id}"
    compress         = true

    forwarded_values {
      query_string = true
      headers      = ["*"]
      cookies {
        forward = "all"
      }
    }

    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    viewer_protocol_policy = "https-only"
  }

  # Static assets cache behavior
  ordered_cache_behavior {
    path_pattern     = "/uploads/*"
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${module.s3_uploads.s3_bucket_id}"
    compress         = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl                = 0
    default_ttl            = 86400
    max_ttl                = 31536000
    viewer_protocol_policy = "redirect-to-https"
  }

  # Geographic restrictions
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # SSL certificate
  viewer_certificate {
    acm_certificate_arn      = var.domain_name != "" ? aws_acm_certificate.main[0].arn : null
    ssl_support_method       = var.domain_name != "" ? "sni-only" : null
    minimum_protocol_version = "TLSv1.2_2021"
    cloudfront_default_certificate = var.domain_name == "" ? true : false
  }

  # Domain aliases
  aliases = var.domain_name != "" ? [var.domain_name, "app.${var.domain_name}", "api.${var.domain_name}"] : []

  # WAF association
  web_acl_id = var.enable_waf ? aws_wafv2_web_acl.main[0].arn : null

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cloudfront"
    Component = "cdn"
  })
}