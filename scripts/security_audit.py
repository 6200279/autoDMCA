#!/usr/bin/env python3
"""
Security Audit Script for Content Protection Platform

This script performs comprehensive security checks and generates audit reports.
It validates security configurations, checks for vulnerabilities, and provides
recommendations for security improvements.

Usage:
    python scripts/security_audit.py [--config CONFIG_FILE] [--output OUTPUT_DIR]
"""

import os
import sys
import json
import yaml
import subprocess
import hashlib
import ssl
import socket
import requests
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import pkg_resources
import psutil

class SecurityAuditor:
    """Comprehensive security audit system."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'findings': [],
            'summary': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'passed': 0
            }
        }
    
    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load audit configuration."""
        default_config = {
            'target_host': 'localhost',
            'target_port': 8000,
            'api_endpoints': [
                '/api/v1/health',
                '/api/v1/auth/login',
                '/api/v1/users',
                '/api/v1/admin'
            ],
            'check_ssl': True,
            'check_headers': True,
            'check_dependencies': True,
            'check_configurations': True,
            'check_permissions': True,
            'output_formats': ['json', 'html']
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                if config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    user_config = yaml.safe_load(f)
                else:
                    user_config = json.load(f)
            default_config.update(user_config)
        
        return default_config
    
    def add_finding(self, category: str, severity: str, title: str, description: str, 
                   recommendation: str, evidence: Dict[str, Any] = None):
        """Add a security finding."""
        finding = {
            'category': category,
            'severity': severity.upper(),
            'title': title,
            'description': description,
            'recommendation': recommendation,
            'evidence': evidence or {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.results['findings'].append(finding)
        
        if severity.upper() in self.results['summary']:
            self.results['summary'][severity.lower()] += 1
        
        # Print finding for immediate feedback
        print(f"[{severity.upper()}] {category}: {title}")
    
    def audit_ssl_tls(self):
        """Audit SSL/TLS configuration."""
        print("Auditing SSL/TLS configuration...")
        
        try:
            # Check SSL certificate
            context = ssl.create_default_context()
            
            with socket.create_connection((self.config['target_host'], 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=self.config['target_host']) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    
                    # Check certificate expiration
                    expiry_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (expiry_date - datetime.utcnow()).days
                    
                    if days_until_expiry < 30:
                        self.add_finding(
                            'SSL/TLS',
                            'HIGH' if days_until_expiry < 7 else 'MEDIUM',
                            'SSL Certificate Expiring Soon',
                            f'SSL certificate expires in {days_until_expiry} days',
                            'Renew SSL certificate before expiration',
                            {'expiry_date': cert['notAfter'], 'days_until_expiry': days_until_expiry}
                        )
                    else:
                        self.results['summary']['passed'] += 1
                    
                    # Check cipher suite
                    if cipher:
                        cipher_name = cipher[0]
                        cipher_version = cipher[1]
                        
                        weak_ciphers = ['RC4', 'DES', '3DES', 'MD5', 'SHA1']
                        if any(weak in cipher_name for weak in weak_ciphers):
                            self.add_finding(
                                'SSL/TLS',
                                'HIGH',
                                'Weak Cipher Suite',
                                f'Weak cipher suite detected: {cipher_name}',
                                'Configure strong cipher suites (AES-256, ECDHE)',
                                {'cipher': cipher_name, 'version': cipher_version}
                            )
                        
                        # Check TLS version
                        if cipher_version < 'TLSv1.2':
                            self.add_finding(
                                'SSL/TLS',
                                'HIGH',
                                'Outdated TLS Version',
                                f'Using TLS version: {cipher_version}',
                                'Upgrade to TLS 1.2 or higher',
                                {'tls_version': cipher_version}
                            )
        
        except Exception as e:
            self.add_finding(
                'SSL/TLS',
                'MEDIUM',
                'SSL/TLS Check Failed',
                f'Unable to verify SSL/TLS configuration: {str(e)}',
                'Verify SSL/TLS is properly configured and accessible',
                {'error': str(e)}
            )
    
    def audit_security_headers(self):
        """Audit HTTP security headers."""
        print("Auditing HTTP security headers...")
        
        try:
            url = f"https://{self.config['target_host']}"
            response = requests.get(url, timeout=10, verify=False)
            headers = response.headers
            
            required_headers = {
                'Strict-Transport-Security': 'HSTS not configured',
                'X-Content-Type-Options': 'MIME sniffing protection missing',
                'X-Frame-Options': 'Clickjacking protection missing',
                'X-XSS-Protection': 'XSS protection missing',
                'Content-Security-Policy': 'CSP not configured',
                'Referrer-Policy': 'Referrer policy not configured'
            }
            
            for header, issue in required_headers.items():
                if header not in headers:
                    self.add_finding(
                        'Security Headers',
                        'MEDIUM',
                        f'Missing Security Header: {header}',
                        issue,
                        f'Add {header} security header to server configuration',
                        {'missing_header': header}
                    )
                else:
                    self.results['summary']['passed'] += 1
            
            # Check for information disclosure
            info_headers = ['Server', 'X-Powered-By', 'X-AspNet-Version']
            for header in info_headers:
                if header in headers:
                    self.add_finding(
                        'Information Disclosure',
                        'LOW',
                        f'Information Disclosure: {header}',
                        f'Server information disclosed in {header} header',
                        f'Remove or obscure {header} header',
                        {'header': header, 'value': headers[header]}
                    )
        
        except Exception as e:
            self.add_finding(
                'Security Headers',
                'MEDIUM',
                'Security Headers Check Failed',
                f'Unable to check security headers: {str(e)}',
                'Verify application is accessible and properly configured',
                {'error': str(e)}
            )
    
    def audit_dependencies(self):
        """Audit Python dependencies for known vulnerabilities."""
        print("Auditing dependencies for vulnerabilities...")
        
        try:
            # Check for pip-audit tool
            result = subprocess.run(['pip-audit', '--format=json'], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                vulnerabilities = json.loads(result.stdout)
                
                for vuln in vulnerabilities:
                    severity = vuln.get('severity', 'UNKNOWN')
                    if severity == 'UNKNOWN':
                        severity = 'MEDIUM'
                    
                    self.add_finding(
                        'Dependencies',
                        severity,
                        f"Vulnerable Dependency: {vuln['package']}",
                        f"Vulnerability in {vuln['package']} {vuln['installed_version']}: {vuln['summary']}",
                        f"Update {vuln['package']} to version {vuln.get('fixed_versions', ['latest'])[0]}",
                        vuln
                    )
            else:
                # Fallback to safety check
                result = subprocess.run(['safety', 'check', '--json'], 
                                      capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    vulns = json.loads(result.stdout)
                    for vuln in vulns:
                        self.add_finding(
                            'Dependencies',
                            'HIGH',
                            f"Vulnerable Dependency: {vuln[0]}",
                            f"Vulnerability in {vuln[0]}: {vuln[2]}",
                            "Update to a secure version",
                            {'package': vuln[0], 'version': vuln[1], 'advisory': vuln[2]}
                        )
        
        except subprocess.TimeoutExpired:
            self.add_finding(
                'Dependencies',
                'MEDIUM',
                'Dependency Check Timeout',
                'Dependency vulnerability scan timed out',
                'Run manual vulnerability scan with pip-audit or safety',
                {'timeout': 60}
            )
        except Exception as e:
            self.add_finding(
                'Dependencies',
                'MEDIUM',
                'Dependency Check Failed',
                f'Unable to check dependencies: {str(e)}',
                'Install pip-audit or safety and run manual scan',
                {'error': str(e)}
            )
    
    def audit_configurations(self):
        """Audit security configurations."""
        print("Auditing security configurations...")
        
        # Check environment variables
        critical_env_vars = [
            'SECRET_KEY', 'ENCRYPTION_KEY', 'DATABASE_PASSWORD',
            'REDIS_PASSWORD', 'STRIPE_SECRET_KEY'
        ]
        
        for var in critical_env_vars:
            value = os.getenv(var)
            if not value:
                self.add_finding(
                    'Configuration',
                    'CRITICAL',
                    f'Missing Environment Variable: {var}',
                    f'Critical environment variable {var} is not set',
                    f'Set {var} environment variable with a secure value',
                    {'variable': var}
                )
            elif var == 'SECRET_KEY' and value == 'dev-secret-key-change-in-production':
                self.add_finding(
                    'Configuration',
                    'CRITICAL',
                    'Default Secret Key',
                    'Using default development secret key in production',
                    'Generate a strong, random secret key for production',
                    {'variable': var}
                )
            elif len(value) < 32:
                self.add_finding(
                    'Configuration',
                    'HIGH',
                    f'Weak {var}',
                    f'{var} is less than 32 characters',
                    f'Use a stronger {var} (32+ characters)',
                    {'variable': var, 'length': len(value)}
                )
        
        # Check Docker configurations
        docker_compose_files = [
            'docker-compose.yml',
            'docker-compose.prod.yml',
            'docker-compose.production.yml',
            'docker-compose.secure.yml'
        ]
        
        for compose_file in docker_compose_files:
            if os.path.exists(compose_file):
                with open(compose_file, 'r') as f:
                    try:
                        config = yaml.safe_load(f)
                        self._audit_docker_compose(config, compose_file)
                    except yaml.YAMLError as e:
                        self.add_finding(
                            'Configuration',
                            'LOW',
                            f'Invalid Docker Compose: {compose_file}',
                            f'Unable to parse Docker Compose file: {str(e)}',
                            'Fix YAML syntax errors in Docker Compose file',
                            {'file': compose_file, 'error': str(e)}
                        )
    
    def _audit_docker_compose(self, config: Dict[str, Any], filename: str):
        """Audit Docker Compose configuration."""
        services = config.get('services', {})
        
        for service_name, service_config in services.items():
            # Check for privileged containers
            if service_config.get('privileged'):
                self.add_finding(
                    'Container Security',
                    'HIGH',
                    f'Privileged Container: {service_name}',
                    f'Service {service_name} runs in privileged mode',
                    'Remove privileged mode unless absolutely necessary',
                    {'service': service_name, 'file': filename}
                )
            
            # Check for root user
            user = service_config.get('user')
            if not user or user == 'root' or user == '0':
                self.add_finding(
                    'Container Security',
                    'MEDIUM',
                    f'Root User: {service_name}',
                    f'Service {service_name} may run as root user',
                    'Configure service to run as non-root user',
                    {'service': service_name, 'file': filename}
                )
            
            # Check for host network mode
            network_mode = service_config.get('network_mode')
            if network_mode == 'host':
                self.add_finding(
                    'Container Security',
                    'MEDIUM',
                    f'Host Network Mode: {service_name}',
                    f'Service {service_name} uses host network mode',
                    'Use custom networks instead of host networking',
                    {'service': service_name, 'file': filename}
                )
            
            # Check for volume mounts
            volumes = service_config.get('volumes', [])
            for volume in volumes:
                if isinstance(volume, str) and ':/var/run/docker.sock' in volume:
                    self.add_finding(
                        'Container Security',
                        'HIGH',
                        f'Docker Socket Mount: {service_name}',
                        f'Service {service_name} mounts Docker socket',
                        'Avoid mounting Docker socket unless absolutely necessary',
                        {'service': service_name, 'volume': volume, 'file': filename}
                    )
    
    def audit_file_permissions(self):
        """Audit file and directory permissions."""
        print("Auditing file permissions...")
        
        sensitive_files = [
            '.env',
            'config/production.py',
            'ssl/private.key',
            'backup/database.sql',
            'logs/app.log'
        ]
        
        for file_path in sensitive_files:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                mode = stat.st_mode
                permissions = oct(mode)[-3:]
                
                # Check if file is readable by others
                if int(permissions[2]) >= 4:
                    self.add_finding(
                        'File Permissions',
                        'HIGH',
                        f'World-Readable File: {file_path}',
                        f'Sensitive file {file_path} is readable by all users',
                        f'Change permissions to 600 or 640: chmod 600 {file_path}',
                        {'file': file_path, 'permissions': permissions}
                    )
                
                # Check if file is writable by group/others
                if int(permissions[1]) >= 2 or int(permissions[2]) >= 2:
                    self.add_finding(
                        'File Permissions',
                        'MEDIUM',
                        f'Overly Permissive File: {file_path}',
                        f'File {file_path} has overly permissive permissions',
                        f'Restrict permissions: chmod 600 {file_path}',
                        {'file': file_path, 'permissions': permissions}
                    )
    
    def audit_network_services(self):
        """Audit running network services."""
        print("Auditing network services...")
        
        try:
            # Get listening ports
            connections = psutil.net_connections(kind='inet')
            listening_ports = {}
            
            for conn in connections:
                if conn.status == 'LISTEN':
                    port = conn.laddr.port
                    if port not in listening_ports:
                        listening_ports[port] = []
                    listening_ports[port].append(conn)
            
            # Check for dangerous services
            dangerous_ports = {
                21: 'FTP',
                23: 'Telnet',
                53: 'DNS',
                135: 'RPC',
                139: 'NetBIOS',
                445: 'SMB',
                1433: 'SQL Server',
                3389: 'RDP',
                5432: 'PostgreSQL',
                6379: 'Redis'
            }
            
            for port, service in dangerous_ports.items():
                if port in listening_ports:
                    # Check if service is bound to all interfaces
                    for conn in listening_ports[port]:
                        if conn.laddr.ip in ['0.0.0.0', '::']:
                            self.add_finding(
                                'Network Security',
                                'HIGH' if port in [21, 23, 135, 3389] else 'MEDIUM',
                                f'Service Exposed: {service}',
                                f'{service} service is listening on all interfaces (port {port})',
                                f'Bind {service} to localhost or use firewall rules',
                                {'port': port, 'service': service, 'address': conn.laddr.ip}
                            )
        
        except Exception as e:
            self.add_finding(
                'Network Security',
                'LOW',
                'Network Audit Failed',
                f'Unable to audit network services: {str(e)}',
                'Manually check listening services with netstat or ss',
                {'error': str(e)}
            )
    
    def audit_api_endpoints(self):
        """Audit API endpoint security."""
        print("Auditing API endpoints...")
        
        base_url = f"http://{self.config['target_host']}:{self.config['target_port']}"
        
        for endpoint in self.config['api_endpoints']:
            url = base_url + endpoint
            
            try:
                # Test without authentication
                response = requests.get(url, timeout=10)
                
                # Check for information disclosure in error messages
                if response.status_code >= 400:
                    response_text = response.text.lower()
                    
                    disclosure_patterns = [
                        'stack trace', 'exception', 'error:', 'warning:',
                        'debug', 'traceback', 'file not found',
                        'permission denied', 'access denied'
                    ]
                    
                    for pattern in disclosure_patterns:
                        if pattern in response_text:
                            self.add_finding(
                                'Information Disclosure',
                                'MEDIUM',
                                f'Detailed Error Message: {endpoint}',
                                f'Endpoint {endpoint} returns detailed error information',
                                'Configure generic error messages for production',
                                {'endpoint': endpoint, 'status': response.status_code}
                            )
                            break
                
                # Check for missing authentication on protected endpoints
                protected_endpoints = ['/api/v1/users', '/api/v1/admin']
                if any(protected in endpoint for protected in protected_endpoints):
                    if response.status_code == 200:
                        self.add_finding(
                            'Authentication',
                            'CRITICAL',
                            f'Missing Authentication: {endpoint}',
                            f'Protected endpoint {endpoint} accessible without authentication',
                            'Implement proper authentication checks',
                            {'endpoint': endpoint, 'status': response.status_code}
                        )
            
            except requests.RequestException as e:
                # This is expected for many endpoints
                pass
    
    def generate_report(self, output_dir: str = 'audit_reports'):
        """Generate security audit report."""
        print(f"Generating security audit report...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate JSON report
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        json_file = os.path.join(output_dir, f'security_audit_{timestamp}.json')
        
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Generate HTML report
        html_file = os.path.join(output_dir, f'security_audit_{timestamp}.html')
        self._generate_html_report(html_file)
        
        # Generate summary
        summary = self.results['summary']
        total_findings = sum(summary[k] for k in ['critical', 'high', 'medium', 'low'])
        
        print(f"\nSecurity Audit Complete!")
        print(f"Report saved to: {json_file}")
        print(f"HTML report saved to: {html_file}")
        print(f"\nSummary:")
        print(f"  Critical: {summary['critical']}")
        print(f"  High:     {summary['high']}")
        print(f"  Medium:   {summary['medium']}")
        print(f"  Low:      {summary['low']}")
        print(f"  Passed:   {summary['passed']}")
        print(f"  Total:    {total_findings} findings")
        
        # Return exit code based on findings
        if summary['critical'] > 0:
            return 3
        elif summary['high'] > 0:
            return 2
        elif summary['medium'] > 0:
            return 1
        else:
            return 0
    
    def _generate_html_report(self, filename: str):
        """Generate HTML audit report."""
        findings_by_category = {}
        for finding in self.results['findings']:
            category = finding['category']
            if category not in findings_by_category:
                findings_by_category[category] = []
            findings_by_category[category].append(finding)
        
        html_template = '''<!DOCTYPE html>
<html>
<head>
    <title>Security Audit Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f4f4f4; padding: 20px; border-radius: 5px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .summary-box { padding: 15px; border-radius: 5px; text-align: center; min-width: 100px; }
        .critical { background-color: #ffebee; border: 2px solid #f44336; }
        .high { background-color: #fff3e0; border: 2px solid #ff9800; }
        .medium { background-color: #fffde7; border: 2px solid #ffc107; }
        .low { background-color: #e8f5e8; border: 2px solid #4caf50; }
        .passed { background-color: #e3f2fd; border: 2px solid #2196f3; }
        .finding { margin: 10px 0; padding: 15px; border-left: 4px solid; border-radius: 5px; }
        .finding.CRITICAL { border-color: #f44336; background-color: #ffebee; }
        .finding.HIGH { border-color: #ff9800; background-color: #fff3e0; }
        .finding.MEDIUM { border-color: #ffc107; background-color: #fffde7; }
        .finding.LOW { border-color: #4caf50; background-color: #e8f5e8; }
        .evidence { background-color: #f5f5f5; padding: 10px; margin-top: 10px; border-radius: 3px; font-size: 0.9em; }
        h1, h2 { color: #333; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Security Audit Report</h1>
        <p class="timestamp">Generated: {timestamp}</p>
        <p>Content Protection Platform Security Audit</p>
    </div>
    
    <div class="summary">
        <div class="summary-box critical">
            <h3>Critical</h3>
            <div>{critical}</div>
        </div>
        <div class="summary-box high">
            <h3>High</h3>
            <div>{high}</div>
        </div>
        <div class="summary-box medium">
            <h3>Medium</h3>
            <div>{medium}</div>
        </div>
        <div class="summary-box low">
            <h3>Low</h3>
            <div>{low}</div>
        </div>
        <div class="summary-box passed">
            <h3>Passed</h3>
            <div>{passed}</div>
        </div>
    </div>
    
    {findings_html}
</body>
</html>'''
        
        findings_html = ""
        for category, findings in findings_by_category.items():
            findings_html += f"<h2>{category}</h2>"
            for finding in findings:
                evidence_html = ""
                if finding['evidence']:
                    evidence_html = f"<div class='evidence'><strong>Evidence:</strong><br><pre>{json.dumps(finding['evidence'], indent=2)}</pre></div>"
                
                findings_html += f'''
                <div class="finding {finding['severity']}">
                    <h3>[{finding['severity']}] {finding['title']}</h3>
                    <p><strong>Description:</strong> {finding['description']}</p>
                    <p><strong>Recommendation:</strong> {finding['recommendation']}</p>
                    <p class="timestamp">Time: {finding['timestamp']}</p>
                    {evidence_html}
                </div>
                '''
        
        html_content = html_template.format(
            timestamp=self.results['timestamp'],
            critical=self.results['summary']['critical'],
            high=self.results['summary']['high'],
            medium=self.results['summary']['medium'],
            low=self.results['summary']['low'],
            passed=self.results['summary']['passed'],
            findings_html=findings_html
        )
        
        with open(filename, 'w') as f:
            f.write(html_content)
    
    def run_audit(self) -> int:
        """Run comprehensive security audit."""
        print("Starting Content Protection Platform Security Audit")
        print("=" * 60)
        
        # Run all audit checks
        if self.config['check_ssl']:
            self.audit_ssl_tls()
        
        if self.config['check_headers']:
            self.audit_security_headers()
        
        if self.config['check_dependencies']:
            self.audit_dependencies()
        
        if self.config['check_configurations']:
            self.audit_configurations()
        
        if self.config['check_permissions']:
            self.audit_file_permissions()
        
        self.audit_network_services()
        self.audit_api_endpoints()
        
        # Generate report
        return self.generate_report()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Content Protection Platform Security Audit')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--output', default='audit_reports', help='Output directory')
    parser.add_argument('--host', default='localhost', help='Target host')
    parser.add_argument('--port', type=int, default=8000, help='Target port')
    
    args = parser.parse_args()
    
    # Create auditor
    auditor = SecurityAuditor(args.config)
    
    # Override config with command line arguments
    if args.host:
        auditor.config['target_host'] = args.host
    if args.port:
        auditor.config['target_port'] = args.port
    
    # Run audit
    try:
        exit_code = auditor.run_audit()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nAudit interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Audit failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()