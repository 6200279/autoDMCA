# Backup and Disaster Recovery Configuration

# AWS Backup Vault
resource "aws_backup_vault" "main" {
  name        = "${local.name_prefix}-backup-vault"
  kms_key_arn = aws_kms_key.main.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backup-vault"
    Component = "backup"
  })
}

# IAM role for AWS Backup
resource "aws_iam_role" "backup" {
  name = "${local.name_prefix}-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "backup.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "backup_policy" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "backup_restore_policy" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

# Backup plan
resource "aws_backup_plan" "main" {
  name = "${local.name_prefix}-backup-plan"

  # Daily backups
  rule {
    rule_name         = "daily_backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = var.backup_schedule

    recovery_point_tags = merge(local.common_tags, {
      BackupType = "daily"
    })

    lifecycle {
      cold_storage_after = 30
      delete_after       = var.backup_retention_days
    }

    copy_action {
      destination_vault_arn = aws_backup_vault.main.arn

      lifecycle {
        cold_storage_after = 30
        delete_after       = var.backup_retention_days
      }
    }
  }

  # Weekly backups (longer retention)
  rule {
    rule_name         = "weekly_backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 5 ? * SUN *)"  # Every Sunday at 5 AM

    recovery_point_tags = merge(local.common_tags, {
      BackupType = "weekly"
    })

    lifecycle {
      cold_storage_after = 30
      delete_after       = 365  # Keep weekly backups for 1 year
    }
  }

  # Monthly backups (longest retention)
  rule {
    rule_name         = "monthly_backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 5 1 * ? *)"  # First day of every month at 5 AM

    recovery_point_tags = merge(local.common_tags, {
      BackupType = "monthly"
    })

    lifecycle {
      cold_storage_after = 30
      delete_after       = 2555  # Keep monthly backups for 7 years
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backup-plan"
  })
}

# Backup selection for RDS
resource "aws_backup_selection" "rds" {
  iam_role_arn = aws_iam_role.backup.arn
  name         = "${local.name_prefix}-rds-backup"
  plan_id      = aws_backup_plan.main.id

  resources = [
    module.rds.db_instance_arn
  ]

  condition {
    string_equals {
      key   = "aws:ResourceTag/Environment"
      value = var.environment
    }
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-backup-selection"
  })
}

# Backup selection for EFS (if used for persistent storage)
resource "aws_efs_file_system" "main" {
  count = var.environment == "production" ? 1 : 0

  creation_token = "${local.name_prefix}-efs"
  performance_mode = "generalPurpose"
  throughput_mode = "provisioned"
  provisioned_throughput_in_mibps = 100

  encrypted = true
  kms_key_id = aws_kms_key.main.arn

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  lifecycle_policy {
    transition_to_primary_storage_class = "AFTER_1_ACCESS"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-efs"
    Component = "storage"
  })
}

resource "aws_efs_mount_target" "main" {
  count = var.environment == "production" ? length(module.vpc.private_subnets) : 0

  file_system_id  = aws_efs_file_system.main[0].id
  subnet_id       = module.vpc.private_subnets[count.index]
  security_groups = [aws_security_group.efs[0].id]
}

resource "aws_security_group" "efs" {
  count = var.environment == "production" ? 1 : 0

  name_prefix = "${local.name_prefix}-efs-"
  vpc_id      = module.vpc.vpc_id

  description = "Security group for EFS"

  ingress {
    description     = "NFS from EKS nodes"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [module.eks.node_security_group_id]
  }

  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-efs-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_backup_selection" "efs" {
  count = var.environment == "production" ? 1 : 0

  iam_role_arn = aws_iam_role.backup.arn
  name         = "${local.name_prefix}-efs-backup"
  plan_id      = aws_backup_plan.main.id

  resources = [
    aws_efs_file_system.main[0].arn
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-efs-backup-selection"
  })
}

# Cross-region replication for S3 buckets (disaster recovery)
resource "aws_s3_bucket" "uploads_replica" {
  count = var.environment == "production" ? 1 : 0

  provider = aws.replica
  bucket   = "${local.name_prefix}-uploads-replica-${random_suffix.this.result}"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-uploads-replica"
    Component = "storage"
    Purpose = "disaster-recovery"
  })
}

# Replication configuration
resource "aws_s3_bucket_replication_configuration" "uploads" {
  count = var.environment == "production" ? 1 : 0

  role   = aws_iam_role.s3_replication[0].arn
  bucket = module.s3_uploads.s3_bucket_id

  rule {
    id     = "ReplicateAll"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.uploads_replica[0].arn
      storage_class = "STANDARD_IA"

      encryption_configuration {
        replica_kms_key_id = aws_kms_key.main.arn
      }
    }
  }

  depends_on = [aws_s3_bucket_versioning.uploads_versioning]
}

# IAM role for S3 replication
resource "aws_iam_role" "s3_replication" {
  count = var.environment == "production" ? 1 : 0
  name  = "${local.name_prefix}-s3-replication"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "s3_replication" {
  count = var.environment == "production" ? 1 : 0
  name  = "${local.name_prefix}-s3-replication-policy"
  role  = aws_iam_role.s3_replication[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl"
        ]
        Resource = "${module.s3_uploads.s3_bucket_arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = module.s3_uploads.s3_bucket_arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete"
        ]
        Resource = "${aws_s3_bucket.uploads_replica[0].arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = aws_kms_key.s3.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.main.arn
      }
    ]
  })
}

# Enable versioning on uploads bucket for replication
resource "aws_s3_bucket_versioning" "uploads_versioning" {
  bucket = module.s3_uploads.s3_bucket_id

  versioning_configuration {
    status = "Enabled"
  }
}

# Database point-in-time recovery notification
resource "aws_cloudwatch_metric_alarm" "rds_backup_failed" {
  alarm_name          = "${local.name_prefix}-rds-backup-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Maximum"
  threshold           = "0"
  alarm_description   = "This alarm is triggered when RDS backup fails"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    DBInstanceIdentifier = module.rds.db_instance_identifier
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-rds-backup-alarm"
  })
}

# Backup completion notifications
resource "aws_cloudwatch_event_rule" "backup_completion" {
  name        = "${local.name_prefix}-backup-completion"
  description = "Capture AWS Backup job state changes"

  event_pattern = jsonencode({
    source      = ["aws.backup"]
    detail-type = ["Backup Job State Change"]
    detail = {
      state = ["COMPLETED", "FAILED", "ABORTED"]
    }
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backup-completion-rule"
  })
}

resource "aws_cloudwatch_event_target" "backup_sns" {
  rule      = aws_cloudwatch_event_rule.backup_completion.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.alerts.arn
}

# SNS topic policy to allow CloudWatch Events
resource "aws_sns_topic_policy" "alerts_policy" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = aws_sns_topic.alerts.arn
      }
    ]
  })
}