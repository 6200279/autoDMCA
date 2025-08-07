# Main Terraform configuration for Content Protection Platform
# Scalable AWS infrastructure supporting development to enterprise levels

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = var.terraform_state_bucket
    key            = "content-protection/terraform.tfstate"
    region         = var.aws_region
    dynamodb_table = var.terraform_lock_table
    encrypt        = true
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "content-protection-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = var.owner
    }
  }
}

# Data sources for existing resources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# Random suffix for unique naming
resource "random_suffix" "this" {
  length  = 8
  special = false
  upper   = false
}

# Local variables
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = var.owner
  }
  
  # AZ selection based on region
  azs = slice(data.aws_availability_zones.available.names, 0, min(length(data.aws_availability_zones.available.names), 3))
  
  # Database configuration
  db_port = 5432
  redis_port = 6379
  
  # Application ports
  backend_port = 8000
  frontend_port = 8080
  
  # CIDR blocks
  vpc_cidr = var.vpc_cidr
  private_subnets = [
    cidrsubnet(local.vpc_cidr, 4, 1),
    cidrsubnet(local.vpc_cidr, 4, 2),
    cidrsubnet(local.vpc_cidr, 4, 3)
  ]
  public_subnets = [
    cidrsubnet(local.vpc_cidr, 4, 4),
    cidrsubnet(local.vpc_cidr, 4, 5),
    cidrsubnet(local.vpc_cidr, 4, 6)
  ]
  database_subnets = [
    cidrsubnet(local.vpc_cidr, 4, 7),
    cidrsubnet(local.vpc_cidr, 4, 8),
    cidrsubnet(local.vpc_cidr, 4, 9)
  ]
}