#!/bin/bash

# Security Checks Runner Script for Content Protection Platform
# This script runs various security tools and generates a comprehensive report

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="${PROJECT_ROOT}/security_reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Create reports directory
mkdir -p "${REPORTS_DIR}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python security tools
install_python_security_tools() {
    log "Installing Python security tools..."
    
    if command_exists pip; then
        pip install --upgrade pip-audit safety bandit semgrep
        success "Python security tools installed"
    else
        error "pip not found. Please install Python and pip first."
        exit 1
    fi
}

# Function to run dependency vulnerability scan
run_dependency_scan() {
    log "Running dependency vulnerability scan..."
    
    cd "${PROJECT_ROOT}/backend"
    
    # pip-audit (preferred)
    if command_exists pip-audit; then
        log "Running pip-audit..."
        pip-audit --format=json --output="${REPORTS_DIR}/pip_audit_${TIMESTAMP}.json" || true
        pip-audit --format=text --output="${REPORTS_DIR}/pip_audit_${TIMESTAMP}.txt" || true
    fi
    
    # safety (fallback)
    if command_exists safety; then
        log "Running safety check..."
        safety check --json --output="${REPORTS_DIR}/safety_${TIMESTAMP}.json" || true
        safety check --output="${REPORTS_DIR}/safety_${TIMESTAMP}.txt" || true
    fi
    
    success "Dependency scan completed"
}

# Function to run static code analysis
run_static_analysis() {
    log "Running static code analysis..."
    
    cd "${PROJECT_ROOT}/backend"
    
    # Bandit for Python security issues
    if command_exists bandit; then
        log "Running Bandit security scan..."
        bandit -r app/ -f json -o "${REPORTS_DIR}/bandit_${TIMESTAMP}.json" || true
        bandit -r app/ -f txt -o "${REPORTS_DIR}/bandit_${TIMESTAMP}.txt" || true
    fi
    
    # Semgrep for additional security patterns
    if command_exists semgrep; then
        log "Running Semgrep security scan..."
        semgrep --config=auto --json --output="${REPORTS_DIR}/semgrep_${TIMESTAMP}.json" app/ || true
        semgrep --config=auto --output="${REPORTS_DIR}/semgrep_${TIMESTAMP}.txt" app/ || true
    fi
    
    success "Static analysis completed"
}

# Function to run Docker security scan
run_docker_scan() {
    log "Running Docker security scan..."
    
    cd "${PROJECT_ROOT}"
    
    # Docker scout (if available)
    if command_exists docker && docker scout --help >/dev/null 2>&1; then
        log "Running Docker Scout..."
        docker scout cves --format=json --output="${REPORTS_DIR}/docker_scout_${TIMESTAMP}.json" . || true
    fi
    
    # Trivy (if available)
    if command_exists trivy; then
        log "Running Trivy container scan..."
        trivy fs --format=json --output="${REPORTS_DIR}/trivy_${TIMESTAMP}.json" . || true
        trivy fs --format=table --output="${REPORTS_DIR}/trivy_${TIMESTAMP}.txt" . || true
    fi
    
    success "Docker scan completed"
}

# Function to run configuration security check
run_config_security_check() {
    log "Running configuration security check..."
    
    cd "${PROJECT_ROOT}"
    
    # Check for sensitive files
    find . -name "*.env*" -o -name "*.key" -o -name "*.pem" -o -name "*.p12" -o -name "*.jks" | \
        while read -r file; do
            echo "Found sensitive file: $file" >> "${REPORTS_DIR}/sensitive_files_${TIMESTAMP}.txt"
        done
    
    # Check file permissions
    find . -type f \( -name "*.key" -o -name "*.pem" -o -name ".env*" \) -exec ls -la {} \; > \
        "${REPORTS_DIR}/file_permissions_${TIMESTAMP}.txt" 2>/dev/null || true
    
    # Check for hardcoded secrets (basic patterns)
    grep -r -i -E "(password|secret|key|token).*=.*['\"][^'\"]{8,}['\"]" \
        --include="*.py" --include="*.js" --include="*.ts" --include="*.json" --include="*.yaml" --include="*.yml" \
        --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=venv --exclude-dir=__pycache__ \
        . > "${REPORTS_DIR}/potential_secrets_${TIMESTAMP}.txt" 2>/dev/null || true
    
    success "Configuration security check completed"
}

# Function to run SSL/TLS security check
run_ssl_check() {
    log "Running SSL/TLS security check..."
    
    local domain="${1:-localhost}"
    local port="${2:-443}"
    
    # testssl.sh (if available)
    if command_exists testssl.sh; then
        log "Running testssl.sh..."
        testssl.sh --jsonfile="${REPORTS_DIR}/testssl_${TIMESTAMP}.json" "${domain}:${port}" || true
    fi
    
    # nmap SSL scripts (if available)
    if command_exists nmap; then
        log "Running nmap SSL scan..."
        nmap --script ssl-enum-ciphers -p "${port}" "${domain}" > \
            "${REPORTS_DIR}/nmap_ssl_${TIMESTAMP}.txt" 2>/dev/null || true
    fi
    
    # OpenSSL cipher check
    if command_exists openssl; then
        log "Running OpenSSL cipher check..."
        {
            echo "=== SSL/TLS Cipher Check ==="
            echo "Connecting to ${domain}:${port}"
            echo
            
            # Test TLS versions
            for tls_version in tls1 tls1_1 tls1_2 tls1_3; do
                echo "Testing ${tls_version}:"
                timeout 10 openssl s_client -connect "${domain}:${port}" \
                    -"${tls_version}" -verify_return_error </dev/null 2>/dev/null && \
                    echo "  ${tls_version}: SUPPORTED" || echo "  ${tls_version}: NOT SUPPORTED"
            done
        } > "${REPORTS_DIR}/openssl_cipher_check_${TIMESTAMP}.txt" 2>/dev/null || true
    fi
    
    success "SSL/TLS check completed"
}

# Function to run custom security audit
run_custom_audit() {
    log "Running custom security audit..."
    
    if [[ -f "${PROJECT_ROOT}/scripts/security_audit.py" ]]; then
        cd "${PROJECT_ROOT}"
        python scripts/security_audit.py --output="${REPORTS_DIR}" || true
    else
        warn "Custom security audit script not found"
    fi
    
    success "Custom audit completed"
}

# Function to generate summary report
generate_summary_report() {
    log "Generating summary report..."
    
    local summary_file="${REPORTS_DIR}/security_summary_${TIMESTAMP}.md"
    
    {
        echo "# Security Scan Summary Report"
        echo
        echo "**Generated:** $(date)"
        echo "**Project:** Content Protection Platform"
        echo
        echo "## Scans Performed"
        echo
        
        # List all generated reports
        find "${REPORTS_DIR}" -name "*_${TIMESTAMP}.*" -type f | while read -r file; do
            local basename=$(basename "$file")
            echo "- $basename"
        done
        
        echo
        echo "## Quick Analysis"
        echo
        
        # Count potential issues
        local total_files=$(find "${REPORTS_DIR}" -name "*_${TIMESTAMP}.*" -type f | wc -l)
        echo "- Total report files: $total_files"
        
        # Check for high-priority issues
        if [[ -f "${REPORTS_DIR}/bandit_${TIMESTAMP}.json" ]]; then
            local high_issues=$(jq -r '.results[] | select(.issue_severity == "HIGH") | .issue_text' \
                "${REPORTS_DIR}/bandit_${TIMESTAMP}.json" 2>/dev/null | wc -l || echo "0")
            echo "- Bandit high-severity issues: $high_issues"
        fi
        
        if [[ -f "${REPORTS_DIR}/pip_audit_${TIMESTAMP}.json" ]]; then
            local vuln_count=$(jq '. | length' "${REPORTS_DIR}/pip_audit_${TIMESTAMP}.json" 2>/dev/null || echo "0")
            echo "- Dependency vulnerabilities: $vuln_count"
        fi
        
        echo
        echo "## Recommendations"
        echo
        echo "1. Review all HIGH and CRITICAL severity findings"
        echo "2. Update vulnerable dependencies immediately"
        echo "3. Fix any hardcoded secrets or credentials"
        echo "4. Ensure proper file permissions on sensitive files"
        echo "5. Configure SSL/TLS with strong cipher suites"
        echo
        echo "## Files Location"
        echo
        echo "All detailed reports are available in: \`${REPORTS_DIR}\`"
        
    } > "$summary_file"
    
    success "Summary report generated: $summary_file"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check for Python
    if ! command_exists python && ! command_exists python3; then
        missing_tools+=("python")
    fi
    
    # Check for pip
    if ! command_exists pip && ! command_exists pip3; then
        missing_tools+=("pip")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        error "Missing required tools: ${missing_tools[*]}"
        error "Please install the missing tools and try again."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Main execution function
main() {
    echo "Content Protection Platform Security Checks"
    echo "=========================================="
    echo
    
    # Parse command line arguments
    local install_tools=false
    local skip_docker=false
    local target_domain="localhost"
    local target_port="443"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --install-tools)
                install_tools=true
                shift
                ;;
            --skip-docker)
                skip_docker=true
                shift
                ;;
            --domain)
                target_domain="$2"
                shift 2
                ;;
            --port)
                target_port="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo
                echo "Options:"
                echo "  --install-tools    Install required security tools"
                echo "  --skip-docker     Skip Docker security scans"
                echo "  --domain DOMAIN   Target domain for SSL checks (default: localhost)"
                echo "  --port PORT       Target port for SSL checks (default: 443)"
                echo "  --help            Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Install tools if requested
    if [[ "$install_tools" == true ]]; then
        install_python_security_tools
    fi
    
    # Run security scans
    log "Starting security scans..."
    echo
    
    run_dependency_scan
    run_static_analysis
    run_config_security_check
    run_ssl_check "$target_domain" "$target_port"
    run_custom_audit
    
    if [[ "$skip_docker" != true ]]; then
        run_docker_scan
    fi
    
    # Generate summary
    generate_summary_report
    
    echo
    success "All security checks completed!"
    success "Reports saved to: ${REPORTS_DIR}"
    
    # Show summary file
    if [[ -f "${REPORTS_DIR}/security_summary_${TIMESTAMP}.md" ]]; then
        echo
        log "Security Summary:"
        cat "${REPORTS_DIR}/security_summary_${TIMESTAMP}.md"
    fi
}

# Run main function with all arguments
main "$@"