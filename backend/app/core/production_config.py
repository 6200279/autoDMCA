"""
Production Configuration for High-Performance Deployment
Optimized settings for 1000+ concurrent users and AI workloads
"""
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PerformanceConfig:
    """Performance optimization configuration"""
    
    # AI/ML Performance
    AI_BATCH_SIZE: int = 16
    AI_CACHE_TTL: int = 7200  # 2 hours
    AI_MAX_CONCURRENT_REQUESTS: int = 50
    AI_MODEL_WARMUP_ENABLED: bool = True
    AI_GPU_MEMORY_FRACTION: float = 0.8
    AI_ENABLE_MODEL_QUANTIZATION: bool = True
    AI_ENABLE_TENSOR_CACHING: bool = True
    
    # Web Crawler Performance
    CRAWLER_MAX_CONCURRENT: int = 20
    CRAWLER_TIMEOUT: int = 30
    CRAWLER_MAX_CONTENT_SIZE: int = 10 * 1024 * 1024  # 10MB
    CRAWLER_ENABLE_COMPRESSION: bool = True
    CRAWLER_CACHE_TTL: int = 3600  # 1 hour
    CRAWLER_RETRY_ATTEMPTS: int = 3
    CRAWLER_RETRY_BACKOFF: float = 2.0
    
    # Database Performance
    DB_POOL_SIZE: int = 40
    DB_MAX_OVERFLOW: int = 60
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_QUERY_TIMEOUT: int = 60
    DB_ENABLE_QUERY_CACHE: bool = True
    DB_SLOW_QUERY_THRESHOLD_MS: float = 1000
    
    # Cache Configuration
    L1_CACHE_SIZE: int = 2000
    L1_CACHE_MEMORY_MB: int = 512
    REDIS_POOL_SIZE: int = 50
    REDIS_CACHE_TTL: int = 7200
    DEFAULT_CACHE_TTL: int = 3600
    ENABLE_L3_CACHE: bool = True
    
    # API Performance
    API_MAX_WORKERS: int = 8
    API_WORKER_CONNECTIONS: int = 2000
    API_KEEPALIVE_TIMEOUT: int = 75
    API_MAX_REQUESTS_PER_CHILD: int = 10000
    API_REQUEST_TIMEOUT: int = 300
    API_MAX_REQUEST_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Monitoring
    MONITOR_INTERVAL: int = 5
    METRICS_RETENTION_HOURS: int = 72
    ENABLE_PERFORMANCE_LOGGING: bool = True
    ENABLE_QUERY_LOGGING: bool = False  # Disable in production for performance
    
    # Alert Thresholds
    ALERT_CPU_THRESHOLD: float = 80.0
    ALERT_MEMORY_THRESHOLD: float = 85.0
    ALERT_RESPONSE_TIME_THRESHOLD: float = 2000.0
    ALERT_ERROR_RATE_THRESHOLD: float = 5.0
    ALERT_GPU_MEMORY_THRESHOLD: float = 90.0
    
    # Load Testing
    LOAD_TEST_MAX_CONCURRENT: int = 1000
    LOAD_TEST_RAMP_UP_TIME: int = 300  # 5 minutes
    LOAD_TEST_DURATION: int = 1800  # 30 minutes


class ProductionSettings:
    """
    Production-optimized settings for Content Protection Platform
    
    Designed to handle:
    - 1000+ concurrent users
    - 10,000+ daily scans
    - <2s AI inference time
    - <500ms API response time
    - 99.9% uptime
    """
    
    def __init__(self):
        self.performance = PerformanceConfig()
        
        # Environment-based configuration
        self.environment = os.getenv("ENVIRONMENT", "production")
        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        
        # Load balancing and scaling
        self.enable_auto_scaling = os.getenv("ENABLE_AUTO_SCALING", "true").lower() == "true"
        self.min_replicas = int(os.getenv("MIN_REPLICAS", "3"))
        self.max_replicas = int(os.getenv("MAX_REPLICAS", "20"))
        
        # Resource limits
        self.cpu_limit = os.getenv("CPU_LIMIT", "4000m")  # 4 CPU cores
        self.memory_limit = os.getenv("MEMORY_LIMIT", "8Gi")  # 8GB RAM
        self.gpu_memory_limit = os.getenv("GPU_MEMORY_LIMIT", "8Gi")  # 8GB GPU
        
    def get_uvicorn_config(self) -> Dict[str, Any]:
        """Get optimized Uvicorn configuration"""
        return {
            "host": "0.0.0.0",
            "port": int(os.getenv("PORT", "8000")),
            "workers": self.performance.API_MAX_WORKERS,
            "worker_class": "uvicorn.workers.UvicornWorker",
            "worker_connections": self.performance.API_WORKER_CONNECTIONS,
            "keepalive": self.performance.API_KEEPALIVE_TIMEOUT,
            "max_requests": self.performance.API_MAX_REQUESTS_PER_CHILD,
            "max_requests_jitter": 1000,
            "timeout": self.performance.API_REQUEST_TIMEOUT,
            "log_level": "info" if not self.debug_mode else "debug",
            "access_log": True,
            "use_colors": False,
            "loop": "uvloop",  # Use uvloop for better performance
            "reload": False,  # Disable in production
            "preload_app": True  # Preload for better memory usage
        }
    
    def get_gunicorn_config(self) -> Dict[str, Any]:
        """Get optimized Gunicorn configuration for production"""
        return {
            "bind": f"0.0.0.0:{os.getenv('PORT', '8000')}",
            "workers": self.performance.API_MAX_WORKERS,
            "worker_class": "uvicorn.workers.UvicornWorker",
            "worker_connections": self.performance.API_WORKER_CONNECTIONS,
            "max_requests": self.performance.API_MAX_REQUESTS_PER_CHILD,
            "max_requests_jitter": 1000,
            "timeout": self.performance.API_REQUEST_TIMEOUT,
            "keepalive": self.performance.API_KEEPALIVE_TIMEOUT,
            "preload_app": True,
            "enable_stdio_inheritance": True,
            "log_level": "info",
            "access_log_format": '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
            "worker_tmp_dir": "/dev/shm",  # Use shared memory for better performance
            "graceful_timeout": 30,
            "worker_process_mode": "gthread" if not self.debug_mode else "sync"
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get optimized Redis configuration"""
        return {
            "url": os.getenv("REDIS_URL", "redis://localhost:6379"),
            "max_connections": self.performance.REDIS_POOL_SIZE,
            "retry_on_timeout": True,
            "health_check_interval": 30,
            "socket_keepalive": True,
            "socket_keepalive_options": {
                "TCP_KEEPIDLE": 1,
                "TCP_KEEPINTVL": 3,
                "TCP_KEEPCNT": 5
            },
            "decode_responses": False,
            "encoding": "utf-8"
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get optimized database configuration"""
        
        # Primary database
        primary_db_config = {
            "url": os.getenv("DATABASE_URL"),
            "pool_size": self.performance.DB_POOL_SIZE,
            "max_overflow": self.performance.DB_MAX_OVERFLOW,
            "pool_timeout": self.performance.DB_POOL_TIMEOUT,
            "pool_recycle": self.performance.DB_POOL_RECYCLE,
            "pool_pre_ping": True,
            "echo": self.performance.ENABLE_QUERY_LOGGING,
            "connect_args": {
                "server_settings": {
                    "jit": "off",
                    "timezone": "UTC",
                    "application_name": "content_protection_platform"
                },
                "command_timeout": self.performance.DB_QUERY_TIMEOUT,
                "connect_timeout": 30
            }
        }
        
        # Read replicas (if configured)
        read_replicas = []
        replica_count = int(os.getenv("DB_READ_REPLICA_COUNT", "0"))
        for i in range(replica_count):
            replica_url = os.getenv(f"DB_READ_REPLICA_{i}_URL")
            if replica_url:
                read_replicas.append({
                    "url": replica_url,
                    "pool_size": self.performance.DB_POOL_SIZE // 2,  # Smaller pools for replicas
                    "max_overflow": self.performance.DB_MAX_OVERFLOW // 2,
                    "pool_timeout": self.performance.DB_POOL_TIMEOUT,
                    "pool_recycle": self.performance.DB_POOL_RECYCLE,
                    "pool_pre_ping": True,
                    "echo": False  # Disable logging for replicas
                })
        
        return {
            "primary": primary_db_config,
            "read_replicas": read_replicas,
            "enable_read_write_split": len(read_replicas) > 0
        }
    
    def get_celery_config(self) -> Dict[str, Any]:
        """Get optimized Celery configuration for background tasks"""
        return {
            "broker_url": os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            "result_backend": os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": "UTC",
            "enable_utc": True,
            "worker_prefetch_multiplier": 4,
            "task_acks_late": True,
            "worker_max_tasks_per_child": 1000,
            "task_compression": "gzip",
            "result_compression": "gzip",
            "worker_pool": "gevent" if not self.debug_mode else "solo",
            "worker_concurrency": 20,
            "beat_schedule": {
                "monitor-performance": {
                    "task": "app.tasks.monitor_performance",
                    "schedule": 60.0,  # Every minute
                },
                "cleanup-cache": {
                    "task": "app.tasks.cleanup_expired_cache",
                    "schedule": 3600.0,  # Every hour
                },
                "health-check": {
                    "task": "app.tasks.system_health_check",
                    "schedule": 300.0,  # Every 5 minutes
                }
            }
        }
    
    def get_nginx_config(self) -> str:
        """Get optimized Nginx configuration"""
        return """
# Optimized Nginx configuration for Content Protection Platform

upstream app_backend {
    least_conn;
    server app1:8000 max_fails=3 fail_timeout=30s;
    server app2:8000 max_fails=3 fail_timeout=30s;
    server app3:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Performance optimizations
    client_max_body_size 50M;
    client_body_timeout 30s;
    client_header_timeout 30s;
    keepalive_timeout 75s;
    keepalive_requests 1000;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=uploads:10m rate=10r/m;
    
    # API endpoints
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://app_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_connect_timeout 30s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # File upload endpoints
    location /api/v1/upload {
        limit_req zone=uploads burst=5 nodelay;
        proxy_pass http://app_backend;
        proxy_request_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100M;
        proxy_connect_timeout 60s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
    
    # Health check
    location /health {
        proxy_pass http://app_backend;
        access_log off;
    }
    
    # Static files (if any)
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Metrics endpoint (internal only)
    location /metrics {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        proxy_pass http://app_backend;
    }
}
        """
    
    def get_docker_compose_config(self) -> Dict[str, Any]:
        """Get optimized Docker Compose configuration"""
        return {
            "version": "3.8",
            "services": {
                "app": {
                    "build": ".",
                    "ports": ["8000:8000"],
                    "environment": {
                        "ENVIRONMENT": "production",
                        "DATABASE_URL": "${DATABASE_URL}",
                        "REDIS_URL": "${REDIS_URL}",
                        "SECRET_KEY": "${SECRET_KEY}"
                    },
                    "deploy": {
                        "replicas": self.min_replicas,
                        "resources": {
                            "limits": {
                                "cpus": self.cpu_limit,
                                "memory": self.memory_limit
                            },
                            "reservations": {
                                "cpus": "1",
                                "memory": "2G"
                            }
                        },
                        "restart_policy": {
                            "condition": "on-failure",
                            "delay": "5s",
                            "max_attempts": 3,
                            "window": "120s"
                        },
                        "update_config": {
                            "parallelism": 1,
                            "delay": "10s",
                            "failure_action": "rollback",
                            "monitor": "60s",
                            "max_failure_ratio": 0.3
                        }
                    },
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "40s"
                    }
                },
                "redis": {
                    "image": "redis:7-alpine",
                    "command": [
                        "redis-server",
                        "--maxmemory", "2gb",
                        "--maxmemory-policy", "allkeys-lru",
                        "--save", "900", "1",
                        "--save", "300", "10",
                        "--save", "60", "10000"
                    ],
                    "deploy": {
                        "resources": {
                            "limits": {
                                "cpus": "1",
                                "memory": "2G"
                            }
                        }
                    }
                },
                "nginx": {
                    "image": "nginx:alpine",
                    "ports": ["80:80", "443:443"],
                    "volumes": [
                        "./nginx.conf:/etc/nginx/nginx.conf:ro",
                        "./ssl:/etc/ssl:ro"
                    ],
                    "depends_on": ["app"],
                    "deploy": {
                        "resources": {
                            "limits": {
                                "cpus": "0.5",
                                "memory": "512M"
                            }
                        }
                    }
                },
                "prometheus": {
                    "image": "prom/prometheus:latest",
                    "ports": ["9090:9090"],
                    "volumes": ["./prometheus.yml:/etc/prometheus/prometheus.yml:ro"],
                    "command": [
                        "--config.file=/etc/prometheus/prometheus.yml",
                        "--storage.tsdb.path=/prometheus",
                        "--web.console.libraries=/etc/prometheus/console_libraries",
                        "--web.console.templates=/etc/prometheus/consoles",
                        "--storage.tsdb.retention.time=15d",
                        "--web.enable-lifecycle"
                    ]
                },
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "ports": ["3000:3000"],
                    "environment": {
                        "GF_SECURITY_ADMIN_PASSWORD": "${GRAFANA_PASSWORD}"
                    },
                    "volumes": ["grafana-storage:/var/lib/grafana"]
                }
            },
            "volumes": {
                "grafana-storage": {}
            },
            "networks": {
                "default": {
                    "driver": "overlay",
                    "attachable": True
                }
            }
        }
    
    def get_kubernetes_config(self) -> Dict[str, Any]:
        """Get Kubernetes deployment configuration"""
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "content-protection-app",
                "labels": {
                    "app": "content-protection",
                    "version": "v1"
                }
            },
            "spec": {
                "replicas": self.min_replicas,
                "selector": {
                    "matchLabels": {
                        "app": "content-protection"
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "content-protection"
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": "app",
                            "image": "content-protection:latest",
                            "ports": [{"containerPort": 8000}],
                            "resources": {
                                "limits": {
                                    "cpu": self.cpu_limit,
                                    "memory": self.memory_limit,
                                    "nvidia.com/gpu": "1"  # If GPU support needed
                                },
                                "requests": {
                                    "cpu": "1",
                                    "memory": "2Gi"
                                }
                            },
                            "env": [
                                {"name": "ENVIRONMENT", "value": "production"},
                                {"name": "DATABASE_URL", "valueFrom": {"secretKeyRef": {"name": "db-secret", "key": "url"}}},
                                {"name": "REDIS_URL", "valueFrom": {"secretKeyRef": {"name": "redis-secret", "key": "url"}}},
                                {"name": "SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "app-secret", "key": "secret-key"}}}
                            ],
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": 8000
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/health",
                                    "port": 8000
                                },
                                "initialDelaySeconds": 5,
                                "periodSeconds": 5
                            }
                        }]
                    }
                }
            }
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get comprehensive monitoring configuration"""
        return {
            "prometheus": {
                "scrape_configs": [
                    {
                        "job_name": "content-protection-app",
                        "static_configs": [{"targets": ["app:8000"]}],
                        "metrics_path": "/metrics",
                        "scrape_interval": "15s"
                    },
                    {
                        "job_name": "redis",
                        "static_configs": [{"targets": ["redis:6379"]}],
                        "scrape_interval": "15s"
                    },
                    {
                        "job_name": "nginx",
                        "static_configs": [{"targets": ["nginx:9113"]}],
                        "scrape_interval": "15s"
                    }
                ],
                "rule_files": ["alerts.yml"],
                "alerting": {
                    "alertmanagers": [
                        {"static_configs": [{"targets": ["alertmanager:9093"]}]}
                    ]
                }
            },
            "grafana": {
                "dashboards": [
                    "api-performance",
                    "ai-inference-metrics",
                    "cache-performance",
                    "database-metrics",
                    "system-resources"
                ],
                "alerts": [
                    "high-response-time",
                    "high-error-rate",
                    "low-cache-hit-rate",
                    "gpu-memory-usage",
                    "database-slow-queries"
                ]
            }
        }


# Global production settings instance
production_settings = ProductionSettings()