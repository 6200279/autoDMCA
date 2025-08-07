# S3 buckets for application storage and backups

# Application storage bucket
resource "aws_s3_bucket" "app_storage" {
  bucket = "${local.name_prefix}-app-storage-${random_suffix.this.result}"

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-app-storage"
    Purpose     = "application-data"
    Environment = var.environment
  })
}

# Enable versioning for application storage
resource "aws_s3_bucket_versioning" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id
  versioning_configuration {
    status = var.s3_versioning_enabled ? "Enabled" : "Disabled"
  }
}

# Encryption for application storage
resource "aws_s3_bucket_server_side_encryption_configuration" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.application.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle configuration for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id

  rule {
    id     = "transition_to_ia"
    status = "Enabled"

    transition {
      days          = var.s3_lifecycle_transition_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.s3_lifecycle_transition_days * 2
      storage_class = "GLACIER"
    }

    expiration {
      days = var.s3_lifecycle_expiration_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "delete_incomplete_multipart_uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Backup bucket
resource "aws_s3_bucket" "backups" {
  bucket = "${local.name_prefix}-backups-${random_suffix.this.result}"

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-backups"
    Purpose     = "backup-storage"
    Environment = var.environment
  })
}

# Enable versioning for backups
resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption for backups
resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.application.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# Block public access for backups
resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle configuration for backups
resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "backup_lifecycle"
    status = "Enabled"

    # Keep daily backups for 30 days
    filter {
      prefix = "database/daily/"
    }

    transition {
      days          = 7
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 30
      storage_class = "GLACIER"
    }

    expiration {
      days = 90
    }
  }

  rule {
    id     = "weekly_backup_lifecycle"
    status = "Enabled"

    # Keep weekly backups for 1 year
    filter {
      prefix = "database/weekly/"
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 2555 # 7 years
    }
  }

  rule {
    id     = "cleanup_multipart_uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Static assets bucket for CloudFront
resource "aws_s3_bucket" "static_assets" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = "${local.name_prefix}-static-assets-${random_suffix.this.result}"

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-static-assets"
    Purpose     = "static-content"
    Environment = var.environment
  })
}

# Enable versioning for static assets
resource "aws_s3_bucket_versioning" "static_assets" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = aws_s3_bucket.static_assets[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption for static assets
resource "aws_s3_bucket_server_side_encryption_configuration" "static_assets" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = aws_s3_bucket.static_assets[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# CORS configuration for static assets
resource "aws_s3_bucket_cors_configuration" "static_assets" {
  count  = var.enable_cloudfront ? 1 : 0
  bucket = aws_s3_bucket.static_assets[0].id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# CloudWatch logs bucket (for centralized logging)
resource "aws_s3_bucket" "logs" {
  bucket = "${local.name_prefix}-logs-${random_suffix.this.result}"

  tags = merge(local.common_tags, {
    Name        = "${local.name_prefix}-logs"
    Purpose     = "log-storage"
    Environment = var.environment
  })
}

# Encryption for logs
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.application.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# Lifecycle for logs
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "log_lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# Block public access for logs
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket notifications for automated processing
resource "aws_s3_bucket_notification" "app_storage_notifications" {
  bucket = aws_s3_bucket.app_storage.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.file_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
    filter_suffix       = ""
  }

  depends_on = [aws_lambda_permission.s3_invoke_file_processor]
}

# Lambda function for file processing
resource "aws_lambda_function" "file_processor" {
  filename         = "file_processor.zip"
  function_name    = "${local.name_prefix}-file-processor"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "index.handler"
  source_code_hash = data.archive_file.file_processor_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = 300

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.app_storage.id
      KMS_KEY_ID  = aws_kms_key.application.id
    }
  }

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  tags = local.common_tags
}

# Lambda deployment package
data "archive_file" "file_processor_zip" {
  type        = "zip"
  output_path = "file_processor.zip"
  source {
    content = <<EOF
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info('File processing event: %s', json.dumps(event))
    # Add your file processing logic here
    return {
        'statusCode': 200,
        'body': json.dumps('File processed successfully')
    }
EOF
    filename = "index.py"
  }
}

# Lambda execution role
resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${local.name_prefix}-lambda-s3-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.app_storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [
          aws_kms_key.application.arn
        ]
      }
    ]
  })
}

# Lambda permission for S3
resource "aws_lambda_permission" "s3_invoke_file_processor" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.file_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.app_storage.arn
}