# ElastiCache Redis configuration for caching and session management

# ElastiCache subnet group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-cache-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-cache-subnet-group"
  })
}

# ElastiCache parameter group
resource "aws_elasticache_parameter_group" "main" {
  name   = "${local.name_prefix}-redis-params"
  family = "redis7.x"

  # Optimized Redis parameters
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }

  parameter {
    name  = "maxclients"
    value = "65000"
  }

  tags = local.common_tags
}

# Generate auth token for Redis
resource "random_password" "redis_auth_token" {
  count   = var.enable_elasticache_auth ? 1 : 0
  length  = 32
  special = false
}

# Store Redis auth token in Secrets Manager
resource "aws_secretsmanager_secret" "redis_auth_token" {
  count                   = var.enable_elasticache_auth ? 1 : 0
  name                    = "${local.name_prefix}/redis-auth-token"
  description             = "Redis authentication token"
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "redis_auth_token" {
  count     = var.enable_elasticache_auth ? 1 : 0
  secret_id = aws_secretsmanager_secret.redis_auth_token[0].id
  secret_string = jsonencode({
    auth_token = random_password.redis_auth_token[0].result
    endpoint   = aws_elasticache_replication_group.main.configuration_endpoint_address
    port       = aws_elasticache_replication_group.main.port
  })
}

# Primary ElastiCache Redis replication group
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${local.name_prefix}-redis"
  description                = "Redis cluster for ${local.name_prefix}"
  
  # Configuration
  node_type                  = lookup(var.environment_config[var.environment], "redis_node_type", var.redis_node_type)
  port                       = local.redis_port
  parameter_group_name       = aws_elasticache_parameter_group.main.name
  
  # Multi-AZ configuration
  num_cache_clusters         = var.environment == "production" ? 3 : 2
  automatic_failover_enabled = var.environment == "production" ? true : false
  multi_az_enabled           = var.environment == "production" ? true : false
  
  # Security
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.elasticache.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = var.enable_elasticache_auth
  auth_token                 = var.enable_elasticache_auth ? random_password.redis_auth_token[0].result : null
  kms_key_id                = aws_kms_key.application.arn
  
  # Maintenance and backup
  maintenance_window         = "sun:03:00-sun:04:00"
  snapshot_retention_limit   = var.environment == "production" ? 5 : 1
  snapshot_window           = "02:00-03:00"
  auto_minor_version_upgrade = true
  
  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-redis"
  })
}

# CloudWatch log group for Redis
resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/redis/${local.name_prefix}/slow-log"
  retention_in_days = var.log_retention_in_days

  tags = local.common_tags
}

# ElastiCache user group (for RBAC if using Redis 6+)
resource "aws_elasticache_user_group" "main" {
  count           = var.enable_elasticache_auth ? 1 : 0
  engine          = "REDIS"
  user_group_id   = "${local.name_prefix}-user-group"
  user_ids        = [aws_elasticache_user.default[0].user_id]

  lifecycle {
    ignore_changes = [user_ids]
  }

  tags = local.common_tags
}

# ElastiCache user for authentication
resource "aws_elasticache_user" "default" {
  count         = var.enable_elasticache_auth ? 1 : 0
  user_id       = "${local.name_prefix}-default-user"
  user_name     = "default"
  access_string = "on ~* +@all"
  engine        = "REDIS"
  passwords     = [random_password.redis_auth_token[0].result]

  tags = local.common_tags
}

# CloudWatch alarms for Redis
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${local.name_prefix}-redis-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors Redis CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${local.name_prefix}-redis-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Redis memory utilization"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "redis_connections" {
  alarm_name          = "${local.name_prefix}-redis-current-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "500"
  alarm_description   = "This metric monitors Redis connection count"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = local.common_tags
}

# Redis cluster for session storage (separate from main cache)
resource "aws_elasticache_replication_group" "sessions" {
  replication_group_id       = "${local.name_prefix}-sessions"
  description                = "Redis cluster for session storage"
  
  # Smaller configuration for sessions
  node_type                  = "cache.t3.micro"
  port                       = local.redis_port
  parameter_group_name       = aws_elasticache_parameter_group.main.name
  
  # Single node for non-production, multi-node for production
  num_cache_clusters         = var.environment == "production" ? 2 : 1
  automatic_failover_enabled = var.environment == "production" ? true : false
  multi_az_enabled           = var.environment == "production" ? true : false
  
  # Security
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.elasticache.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = var.enable_elasticache_auth
  auth_token                 = var.enable_elasticache_auth ? random_password.redis_auth_token[0].result : null
  kms_key_id                = aws_kms_key.application.arn
  
  # Maintenance and backup
  maintenance_window         = "sun:04:00-sun:05:00"
  snapshot_retention_limit   = 1
  snapshot_window           = "03:00-04:00"
  auto_minor_version_upgrade = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-sessions"
    Purpose = "session-storage"
  })
}