# Amazon EKS Cluster configuration for Content Protection Platform

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = "${local.name_prefix}-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.eks_cluster_version

  vpc_config {
    subnet_ids              = concat(aws_subnet.private[*].id, aws_subnet.public[*].id)
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = var.allowed_cidr_blocks
    security_group_ids      = [aws_security_group.eks_cluster.id]
  }

  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_service_policy,
    aws_cloudwatch_log_group.eks
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-eks-cluster"
  })
}

# CloudWatch Log Group for EKS
resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${local.name_prefix}-cluster/cluster"
  retention_in_days = var.log_retention_in_days

  tags = local.common_tags
}

# EKS Node Group
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name_prefix}-node-group"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = var.eks_node_instance_types
  ami_type        = "AL2_x86_64"
  capacity_type   = "ON_DEMAND"
  disk_size       = 50

  scaling_config {
    desired_size = lookup(var.environment_config[var.environment], "node_desired_size", var.eks_node_desired_size)
    max_size     = lookup(var.environment_config[var.environment], "node_max_size", var.eks_node_max_size)
    min_size     = lookup(var.environment_config[var.environment], "node_min_size", var.eks_node_min_size)
  }

  update_config {
    max_unavailable = 1
  }

  remote_access {
    ec2_ssh_key = aws_key_pair.eks_nodes.key_name
    source_security_group_ids = [aws_security_group.bastion.id]
  }

  labels = {
    Environment = var.environment
    NodeGroup   = "main"
  }

  taint {
    key    = "dedicated"
    value  = "main"
    effect = "NO_SCHEDULE"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-node-group"
  })
}

# Spot Instance Node Group (if enabled)
resource "aws_eks_node_group" "spot" {
  count = var.enable_spot_instances ? 1 : 0

  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${local.name_prefix}-spot-node-group"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = aws_subnet.private[*].id
  instance_types  = var.spot_instance_types
  ami_type        = "AL2_x86_64"
  capacity_type   = "SPOT"
  disk_size       = 50

  scaling_config {
    desired_size = var.environment == "production" ? 2 : 1
    max_size     = var.environment == "production" ? 10 : 3
    min_size     = 0
  }

  update_config {
    max_unavailable = 1
  }

  remote_access {
    ec2_ssh_key = aws_key_pair.eks_nodes.key_name
    source_security_group_ids = [aws_security_group.bastion.id]
  }

  labels = {
    Environment = var.environment
    NodeGroup   = "spot"
    InstanceType = "spot"
  }

  taint {
    key    = "spot"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-spot-node-group"
  })
}

# Key pair for EC2 instances
resource "tls_private_key" "eks_nodes" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "aws_key_pair" "eks_nodes" {
  key_name   = "${local.name_prefix}-eks-nodes"
  public_key = tls_private_key.eks_nodes.public_key_openssh

  tags = local.common_tags
}

# Store private key in AWS Secrets Manager
resource "aws_secretsmanager_secret" "eks_nodes_key" {
  name                    = "${local.name_prefix}/eks-nodes-private-key"
  description             = "Private key for EKS nodes"
  recovery_window_in_days = 7

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "eks_nodes_key" {
  secret_id     = aws_secretsmanager_secret.eks_nodes_key.id
  secret_string = tls_private_key.eks_nodes.private_key_pem
}

# KMS key for EKS encryption
resource "aws_kms_key" "eks" {
  description             = "EKS Secret Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = local.common_tags
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${local.name_prefix}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

# EKS Add-ons
resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "coredns"
  
  depends_on = [
    aws_eks_node_group.main,
  ]

  tags = local.common_tags
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "kube-proxy"
  
  depends_on = [
    aws_eks_node_group.main,
  ]

  tags = local.common_tags
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"
  
  depends_on = [
    aws_eks_node_group.main,
  ]

  tags = local.common_tags
}

resource "aws_eks_addon" "aws_ebs_csi_driver" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "aws-ebs-csi-driver"
  
  depends_on = [
    aws_eks_node_group.main,
  ]

  tags = local.common_tags
}

# OIDC Identity Provider
data "tls_certificate" "cluster" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "cluster" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.cluster.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = local.common_tags
}

# Container Insights (if enabled)
resource "aws_cloudwatch_log_group" "container_insights" {
  count = var.enable_container_insights ? 1 : 0

  name              = "/aws/containerinsights/${aws_eks_cluster.main.name}/application"
  retention_in_days = var.log_retention_in_days

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "container_insights_dataplane" {
  count = var.enable_container_insights ? 1 : 0

  name              = "/aws/containerinsights/${aws_eks_cluster.main.name}/dataplane"
  retention_in_days = var.log_retention_in_days

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "container_insights_host" {
  count = var.enable_container_insights ? 1 : 0

  name              = "/aws/containerinsights/${aws_eks_cluster.main.name}/host"
  retention_in_days = var.log_retention_in_days

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "container_insights_performance" {
  count = var.enable_container_insights ? 1 : 0

  name              = "/aws/containerinsights/${aws_eks_cluster.main.name}/performance"
  retention_in_days = var.log_retention_in_days

  tags = local.common_tags
}