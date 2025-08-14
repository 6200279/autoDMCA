"""
Comprehensive Security Monitoring and Incident Response System.

This module provides:
- Real-time security event monitoring
- Automated threat detection
- Incident response automation
- Security metrics collection
- Anomaly detection using behavioral analysis
- Integration with external security tools
"""

import json
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import threading
import asyncio
import hashlib
import ipaddress
from pathlib import Path

import redis
from fastapi import Request, BackgroundTasks
import requests

from app.core.config import settings
from app.core.security import log_security_event


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Security incident status."""
    OPEN = "open"
    INVESTIGATING = "investigating" 
    CONTAINED = "contained"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    timestamp: datetime
    event_type: str
    severity: ThreatLevel
    source_ip: str
    user_id: Optional[str]
    details: Dict[str, Any]
    event_id: str
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['severity'] = self.severity.value
        return data


@dataclass
class SecurityIncident:
    """Security incident data structure."""
    incident_id: str
    title: str
    description: str
    severity: ThreatLevel
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str]
    events: List[SecurityEvent]
    response_actions: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['events'] = [event.to_dict() for event in self.events]
        return data


class SecurityMonitor:
    """Comprehensive security monitoring system."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        
        # Event storage and processing
        self.event_buffer = deque(maxlen=10000)  # In-memory buffer for recent events
        self.active_incidents = {}
        self.threat_intelligence = {}
        
        # Behavioral analysis data
        self.user_baselines = {}  # User behavior baselines
        self.ip_reputation = {}   # IP address reputation scores
        self.attack_patterns = {}  # Known attack patterns
        
        # Monitoring configuration
        self.monitoring_rules = self._load_monitoring_rules()
        self.correlation_rules = self._load_correlation_rules()
        self.response_playbooks = self._load_response_playbooks()
        
        # Background processing
        self._start_background_processing()
    
    def _load_monitoring_rules(self) -> Dict[str, Any]:
        """Load security monitoring rules."""
        return {
            'failed_login_threshold': {
                'events': 5,
                'timeframe': 300,  # 5 minutes
                'severity': ThreatLevel.MEDIUM,
                'action': 'lock_account'
            },
            'brute_force_detection': {
                'events': 10,
                'timeframe': 600,  # 10 minutes
                'severity': ThreatLevel.HIGH,
                'action': 'block_ip'
            },
            'privilege_escalation': {
                'events': 3,
                'timeframe': 1800,  # 30 minutes
                'severity': ThreatLevel.HIGH,
                'action': 'alert_admin'
            },
            'data_exfiltration': {
                'size_threshold': 100 * 1024 * 1024,  # 100MB
                'timeframe': 3600,  # 1 hour
                'severity': ThreatLevel.CRITICAL,
                'action': 'immediate_response'
            },
            'sql_injection_attempts': {
                'events': 1,  # Zero tolerance
                'timeframe': 60,
                'severity': ThreatLevel.HIGH,
                'action': 'block_ip'
            },
            'unauthorized_admin_access': {
                'events': 1,
                'timeframe': 60,
                'severity': ThreatLevel.CRITICAL,
                'action': 'immediate_response'
            }
        }
    
    def _load_correlation_rules(self) -> List[Dict[str, Any]]:
        """Load event correlation rules for incident detection."""
        return [
            {
                'name': 'Coordinated Attack',
                'pattern': ['failed_login', 'privilege_escalation', 'unauthorized_access'],
                'timeframe': 3600,  # 1 hour
                'min_events': 5,
                'severity': ThreatLevel.CRITICAL
            },
            {
                'name': 'Account Takeover',
                'pattern': ['failed_login', 'successful_login', 'password_change'],
                'timeframe': 1800,  # 30 minutes
                'min_events': 3,
                'severity': ThreatLevel.HIGH
            },
            {
                'name': 'Data Breach Attempt',
                'pattern': ['sql_injection', 'unauthorized_access', 'large_data_access'],
                'timeframe': 2400,  # 40 minutes
                'min_events': 3,
                'severity': ThreatLevel.CRITICAL
            },
            {
                'name': 'Insider Threat',
                'pattern': ['after_hours_access', 'unusual_data_access', 'privilege_abuse'],
                'timeframe': 7200,  # 2 hours
                'min_events': 4,
                'severity': ThreatLevel.HIGH
            }
        ]
    
    def _load_response_playbooks(self) -> Dict[str, Dict[str, Any]]:
        """Load incident response playbooks."""
        return {
            'brute_force_attack': {
                'steps': [
                    'block_source_ip',
                    'notify_security_team',
                    'review_logs',
                    'update_firewall_rules'
                ],
                'automated_actions': ['block_source_ip'],
                'escalation_time': 300  # 5 minutes
            },
            'sql_injection': {
                'steps': [
                    'block_source_ip',
                    'isolate_affected_system',
                    'preserve_evidence',
                    'notify_dba_team',
                    'security_audit'
                ],
                'automated_actions': ['block_source_ip', 'preserve_evidence'],
                'escalation_time': 60  # 1 minute
            },
            'data_exfiltration': {
                'steps': [
                    'block_all_connections',
                    'preserve_evidence',
                    'notify_management',
                    'legal_notification',
                    'forensic_analysis'
                ],
                'automated_actions': ['block_all_connections', 'preserve_evidence'],
                'escalation_time': 30  # 30 seconds
            },
            'insider_threat': {
                'steps': [
                    'disable_user_account',
                    'preserve_evidence',
                    'notify_hr_and_legal',
                    'forensic_analysis',
                    'interview_preparation'
                ],
                'automated_actions': ['preserve_evidence'],
                'escalation_time': 120  # 2 minutes
            }
        }
    
    def _start_background_processing(self):
        """Start background processing threads."""
        # Event correlation thread
        correlation_thread = threading.Thread(target=self._correlation_processor, daemon=True)
        correlation_thread.start()
        
        # Behavioral analysis thread
        behavior_thread = threading.Thread(target=self._behavioral_analyzer, daemon=True)
        behavior_thread.start()
        
        # Threat intelligence update thread
        intel_thread = threading.Thread(target=self._threat_intelligence_updater, daemon=True)
        intel_thread.start()
    
    def record_event(
        self,
        event_type: str,
        severity: ThreatLevel,
        source_ip: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> SecurityEvent:
        """Record a security event."""
        # Create security event
        event = SecurityEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_id=user_id,
            details=details or {},
            event_id=hashlib.sha256(
                f"{time.time()}{event_type}{source_ip}{user_id}".encode()
            ).hexdigest()[:16]
        )
        
        # Add request details if available
        if request:
            event.details.update({
                'method': request.method,
                'path': request.url.path,
                'user_agent': request.headers.get('User-Agent'),
                'referer': request.headers.get('Referer')
            })
        
        # Store event
        self.event_buffer.append(event)
        self._store_event_persistent(event)
        
        # Check for immediate response triggers
        self._check_immediate_response(event)
        
        # Update behavioral baselines
        self._update_behavioral_data(event)
        
        return event
    
    def _store_event_persistent(self, event: SecurityEvent):
        """Store event in persistent storage."""
        if self.redis_client:
            # Store individual event
            self.redis_client.hset(
                f"security_event:{event.event_id}",
                mapping=event.to_dict()
            )
            self.redis_client.expire(f"security_event:{event.event_id}", 86400 * 30)  # 30 days
            
            # Add to event stream for processing
            self.redis_client.xadd(
                "security_events_stream",
                event.to_dict(),
                maxlen=100000  # Keep last 100k events
            )
            
            # Update metrics
            self._update_metrics(event)
    
    def _check_immediate_response(self, event: SecurityEvent):
        """Check if event requires immediate response."""
        rule_name = None
        
        # Check monitoring rules
        for rule_name, rule in self.monitoring_rules.items():
            if self._event_matches_rule(event, rule):
                self._trigger_automated_response(event, rule, rule_name)
                break
        
        # Check for critical severity
        if event.severity == ThreatLevel.CRITICAL:
            self._trigger_critical_incident_response(event)
    
    def _event_matches_rule(self, event: SecurityEvent, rule: Dict[str, Any]) -> bool:
        """Check if event matches a monitoring rule."""
        # Count recent similar events
        cutoff_time = event.timestamp - timedelta(seconds=rule['timeframe'])
        similar_events = [
            e for e in self.event_buffer
            if (e.event_type == event.event_type and 
                e.source_ip == event.source_ip and
                e.timestamp > cutoff_time)
        ]
        
        return len(similar_events) >= rule['events']
    
    def _trigger_automated_response(self, event: SecurityEvent, rule: Dict[str, Any], rule_name: str):
        """Trigger automated response based on rule."""
        response_actions = []
        
        if rule['action'] == 'block_ip':
            self._block_ip_address(event.source_ip)
            response_actions.append(f"Blocked IP: {event.source_ip}")
        
        elif rule['action'] == 'lock_account' and event.user_id:
            self._lock_user_account(event.user_id)
            response_actions.append(f"Locked account: {event.user_id}")
        
        elif rule['action'] == 'alert_admin':
            self._send_security_alert(event, rule_name)
            response_actions.append("Admin alert sent")
        
        elif rule['action'] == 'immediate_response':
            incident_id = self._create_security_incident(event, rule_name)
            response_actions.append(f"Security incident created: {incident_id}")
        
        # Log response actions
        log_security_event(
            event_type="automated_response",
            severity="MEDIUM",
            details={
                "trigger_event": event.event_id,
                "rule": rule_name,
                "actions": response_actions
            },
            user_id=event.user_id,
            ip_address=event.source_ip
        )
    
    def _block_ip_address(self, ip_address: str):
        """Block an IP address."""
        if self.redis_client:
            # Add to blocked IPs list
            self.redis_client.sadd("blocked_ips", ip_address)
            self.redis_client.setex(f"ip_blocked:{ip_address}", 86400, "true")  # 24 hour block
            
            # Update IP reputation
            self.ip_reputation[ip_address] = {
                'score': 0,  # Worst score
                'blocked': True,
                'blocked_at': datetime.utcnow().isoformat(),
                'reason': 'Automated security response'
            }
    
    def _lock_user_account(self, user_id: str):
        """Lock a user account."""
        if self.redis_client:
            # Lock account for security review
            self.redis_client.setex(f"account_locked:{user_id}", 3600, "security_lock")  # 1 hour
            
            # Log account lock
            log_security_event(
                event_type="account_locked",
                severity="HIGH",
                details={"reason": "Security threat detected"},
                user_id=user_id
            )
    
    def _send_security_alert(self, event: SecurityEvent, rule_name: str):
        """Send security alert to administrators."""
        alert_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event.event_type,
            'severity': event.severity.value,
            'rule_triggered': rule_name,
            'source_ip': event.source_ip,
            'user_id': event.user_id,
            'details': event.details
        }
        
        # In production, send to alerting system (email, Slack, PagerDuty, etc.)
        self._notify_security_team(alert_data)
    
    def _create_security_incident(self, event: SecurityEvent, incident_type: str) -> str:
        """Create a security incident."""
        incident_id = f"INC-{int(time.time())}-{hashlib.sha256(event.event_id.encode()).hexdigest()[:8]}"
        
        incident = SecurityIncident(
            incident_id=incident_id,
            title=f"{incident_type.replace('_', ' ').title()} - {event.event_type}",
            description=f"Automated incident created for {event.event_type} from {event.source_ip}",
            severity=event.severity,
            status=IncidentStatus.OPEN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            assigned_to=None,
            events=[event],
            response_actions=[]
        )
        
        self.active_incidents[incident_id] = incident
        
        # Store in persistent storage
        if self.redis_client:
            self.redis_client.hset(
                f"security_incident:{incident_id}",
                mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else v 
                        for k, v in incident.to_dict().items()}
            )
        
        # Trigger incident response playbook
        if incident_type in self.response_playbooks:
            self._execute_response_playbook(incident_id, incident_type)
        
        return incident_id
    
    def _execute_response_playbook(self, incident_id: str, playbook_name: str):
        """Execute incident response playbook."""
        playbook = self.response_playbooks.get(playbook_name, {})
        incident = self.active_incidents.get(incident_id)
        
        if not incident or not playbook:
            return
        
        # Execute automated actions
        automated_actions = playbook.get('automated_actions', [])
        for action in automated_actions:
            self._execute_response_action(incident, action)
        
        # Schedule escalation
        escalation_time = playbook.get('escalation_time', 300)
        # In production, use Celery or similar for scheduling
        threading.Timer(escalation_time, self._escalate_incident, args=[incident_id]).start()
    
    def _execute_response_action(self, incident: SecurityIncident, action: str):
        """Execute a specific response action."""
        action_result = {"action": action, "timestamp": datetime.utcnow().isoformat()}
        
        try:
            if action == 'block_source_ip':
                for event in incident.events:
                    self._block_ip_address(event.source_ip)
                action_result["result"] = "success"
                action_result["details"] = "Source IPs blocked"
            
            elif action == 'block_all_connections':
                # Block all connections from user/IP
                for event in incident.events:
                    if event.user_id:
                        self._lock_user_account(event.user_id)
                    self._block_ip_address(event.source_ip)
                action_result["result"] = "success"
                action_result["details"] = "All connections blocked"
            
            elif action == 'preserve_evidence':
                self._preserve_digital_evidence(incident)
                action_result["result"] = "success"
                action_result["details"] = "Evidence preserved"
            
            elif action == 'disable_user_account':
                for event in incident.events:
                    if event.user_id:
                        self._disable_user_account(event.user_id)
                action_result["result"] = "success"
                action_result["details"] = "User accounts disabled"
            
            else:
                action_result["result"] = "skipped"
                action_result["details"] = f"Unknown action: {action}"
        
        except Exception as e:
            action_result["result"] = "error"
            action_result["details"] = str(e)
        
        # Record action
        incident.response_actions.append(action_result)
        incident.updated_at = datetime.utcnow()
    
    def _preserve_digital_evidence(self, incident: SecurityIncident):
        """Preserve digital evidence for forensic analysis."""
        evidence_dir = Path(f"evidence/{incident.incident_id}")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Save incident data
        with open(evidence_dir / "incident.json", "w") as f:
            json.dump(incident.to_dict(), f, indent=2)
        
        # Save related events
        with open(evidence_dir / "events.json", "w") as f:
            events_data = [event.to_dict() for event in incident.events]
            json.dump(events_data, f, indent=2)
        
        # Save system state snapshot
        system_state = {
            "timestamp": datetime.utcnow().isoformat(),
            "active_sessions": len(self.user_baselines),
            "blocked_ips": list(self.ip_reputation.keys()) if self.ip_reputation else [],
            "recent_events_count": len(self.event_buffer)
        }
        
        with open(evidence_dir / "system_state.json", "w") as f:
            json.dump(system_state, f, indent=2)
    
    def _disable_user_account(self, user_id: str):
        """Permanently disable a user account."""
        if self.redis_client:
            # Mark account as disabled
            self.redis_client.setex(f"account_disabled:{user_id}", 86400 * 365, "security_incident")
            
            # Revoke all active sessions
            self.redis_client.delete(f"user_sessions:{user_id}")
    
    def _escalate_incident(self, incident_id: str):
        """Escalate security incident if not resolved."""
        incident = self.active_incidents.get(incident_id)
        
        if incident and incident.status == IncidentStatus.OPEN:
            incident.status = IncidentStatus.INVESTIGATING
            incident.updated_at = datetime.utcnow()
            
            # Notify security team for manual intervention
            self._notify_security_team({
                "incident_id": incident_id,
                "title": incident.title,
                "severity": incident.severity.value,
                "status": "escalated",
                "message": "Incident requires manual investigation"
            })
    
    def _correlation_processor(self):
        """Background process for event correlation."""
        while True:
            try:
                time.sleep(60)  # Run every minute
                
                # Process correlation rules
                for rule in self.correlation_rules:
                    self._check_correlation_rule(rule)
                
            except Exception as e:
                log_security_event(
                    event_type="correlation_error",
                    severity="MEDIUM",
                    details={"error": str(e)}
                )
    
    def _check_correlation_rule(self, rule: Dict[str, Any]):
        """Check if a correlation rule is triggered."""
        pattern = rule['pattern']
        timeframe = rule['timeframe']
        min_events = rule['min_events']
        
        # Look for pattern in recent events
        cutoff_time = datetime.utcnow() - timedelta(seconds=timeframe)
        recent_events = [e for e in self.event_buffer if e.timestamp > cutoff_time]
        
        # Group events by source
        events_by_source = defaultdict(list)
        for event in recent_events:
            key = f"{event.source_ip}:{event.user_id}"
            events_by_source[key].append(event)
        
        # Check each source for pattern match
        for source, events in events_by_source.items():
            if len(events) >= min_events:
                event_types = [e.event_type for e in events]
                
                # Check if pattern is present
                pattern_matches = sum(1 for p in pattern if p in event_types)
                if pattern_matches >= len(pattern) * 0.8:  # 80% pattern match
                    self._create_correlated_incident(rule, events)
    
    def _create_correlated_incident(self, rule: Dict[str, Any], events: List[SecurityEvent]):
        """Create incident from correlated events."""
        incident_id = f"COR-{int(time.time())}-{hashlib.sha256(rule['name'].encode()).hexdigest()[:8]}"
        
        incident = SecurityIncident(
            incident_id=incident_id,
            title=f"Correlated Attack: {rule['name']}",
            description=f"Pattern detected: {', '.join(rule['pattern'])}",
            severity=rule['severity'],
            status=IncidentStatus.OPEN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            assigned_to=None,
            events=events,
            response_actions=[]
        )
        
        # Assign correlation ID to events
        correlation_id = incident_id
        for event in events:
            event.correlation_id = correlation_id
        
        self.active_incidents[incident_id] = incident
        
        # Execute response actions
        if rule['severity'] == ThreatLevel.CRITICAL:
            self._execute_response_playbook(incident_id, 'data_exfiltration')
        elif rule['severity'] == ThreatLevel.HIGH:
            self._execute_response_playbook(incident_id, 'brute_force_attack')
    
    def _behavioral_analyzer(self):
        """Background process for behavioral analysis."""
        while True:
            try:
                time.sleep(300)  # Run every 5 minutes
                
                # Update user behavior baselines
                self._update_user_baselines()
                
                # Analyze IP reputation
                self._analyze_ip_reputation()
                
                # Detect anomalies
                self._detect_behavioral_anomalies()
                
            except Exception as e:
                log_security_event(
                    event_type="behavioral_analysis_error",
                    severity="LOW",
                    details={"error": str(e)}
                )
    
    def _update_user_baselines(self):
        """Update behavioral baselines for users."""
        # Group recent events by user
        recent_events = list(self.event_buffer)[-1000:]  # Last 1000 events
        events_by_user = defaultdict(list)
        
        for event in recent_events:
            if event.user_id:
                events_by_user[event.user_id].append(event)
        
        # Update baselines
        for user_id, events in events_by_user.items():
            baseline = self.user_baselines.get(user_id, {
                'typical_hours': set(),
                'common_ips': set(),
                'usual_actions': set(),
                'avg_session_duration': 0,
                'last_updated': datetime.utcnow()
            })
            
            # Update typical access hours
            for event in events:
                hour = event.timestamp.hour
                baseline['typical_hours'].add(hour)
            
            # Update common IP addresses
            for event in events:
                baseline['common_ips'].add(event.source_ip)
            
            # Update usual actions
            for event in events:
                baseline['usual_actions'].add(event.event_type)
            
            baseline['last_updated'] = datetime.utcnow()
            self.user_baselines[user_id] = baseline
    
    def _analyze_ip_reputation(self):
        """Analyze and update IP address reputation scores."""
        recent_events = list(self.event_buffer)[-500:]  # Last 500 events
        ip_stats = defaultdict(lambda: {'good': 0, 'bad': 0, 'total': 0})
        
        for event in recent_events:
            ip_stats[event.source_ip]['total'] += 1
            
            if event.severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                ip_stats[event.source_ip]['bad'] += 1
            else:
                ip_stats[event.source_ip]['good'] += 1
        
        # Update reputation scores
        for ip, stats in ip_stats.items():
            if stats['total'] >= 5:  # Minimum events for scoring
                score = (stats['good'] - stats['bad']) / stats['total']
                
                self.ip_reputation[ip] = {
                    'score': max(0, min(100, int((score + 1) * 50))),  # 0-100 scale
                    'events_analyzed': stats['total'],
                    'last_updated': datetime.utcnow().isoformat(),
                    'blocked': score < -0.8  # Block if score is very low
                }
    
    def _detect_behavioral_anomalies(self):
        """Detect behavioral anomalies based on baselines."""
        recent_events = [e for e in self.event_buffer if e.timestamp > datetime.utcnow() - timedelta(hours=1)]
        
        for event in recent_events:
            if not event.user_id:
                continue
            
            baseline = self.user_baselines.get(event.user_id)
            if not baseline:
                continue
            
            anomalies = []
            
            # Check unusual access time
            current_hour = event.timestamp.hour
            if current_hour not in baseline['typical_hours']:
                anomalies.append("Unusual access time")
            
            # Check new IP address
            if event.source_ip not in baseline['common_ips']:
                anomalies.append("Access from new IP address")
            
            # Check unusual action
            if event.event_type not in baseline['usual_actions']:
                anomalies.append("Unusual action performed")
            
            # Report anomalies
            if anomalies:
                self.record_event(
                    event_type="behavioral_anomaly",
                    severity=ThreatLevel.MEDIUM,
                    source_ip=event.source_ip,
                    user_id=event.user_id,
                    details={
                        "original_event": event.event_id,
                        "anomalies": anomalies
                    }
                )
    
    def _threat_intelligence_updater(self):
        """Update threat intelligence feeds."""
        while True:
            try:
                time.sleep(3600)  # Update every hour
                
                # Update IP reputation from external sources
                self._update_external_threat_intelligence()
                
            except Exception as e:
                log_security_event(
                    event_type="threat_intel_update_error",
                    severity="LOW",
                    details={"error": str(e)}
                )
    
    def _update_external_threat_intelligence(self):
        """Update threat intelligence from external sources."""
        # In production, integrate with threat intelligence feeds
        # For now, we'll simulate with a basic update
        
        # Update known malicious IPs (example)
        malicious_ips = [
            # Add known malicious IPs here
        ]
        
        for ip in malicious_ips:
            self.ip_reputation[ip] = {
                'score': 0,
                'source': 'threat_intelligence',
                'blocked': True,
                'last_updated': datetime.utcnow().isoformat()
            }
    
    def _notify_security_team(self, alert_data: Dict[str, Any]):
        """Notify security team of critical events."""
        # In production, integrate with notification systems
        # (email, Slack, PagerDuty, etc.)
        
        # Log the alert
        log_security_event(
            event_type="security_team_notification",
            severity="HIGH",
            details=alert_data
        )
        
        # Store notification in Redis for dashboard
        if self.redis_client:
            self.redis_client.lpush("security_notifications", json.dumps(alert_data))
            self.redis_client.ltrim("security_notifications", 0, 99)  # Keep last 100
    
    def _update_behavioral_data(self, event: SecurityEvent):
        """Update behavioral analysis data with new event."""
        # Update IP reputation in real-time for critical events
        if event.severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            current_score = self.ip_reputation.get(event.source_ip, {}).get('score', 50)
            new_score = max(0, current_score - 20)  # Decrease reputation
            
            self.ip_reputation[event.source_ip] = {
                'score': new_score,
                'last_event': event.event_type,
                'last_updated': datetime.utcnow().isoformat(),
                'blocked': new_score == 0
            }
    
    def _update_metrics(self, event: SecurityEvent):
        """Update security metrics."""
        if not self.redis_client:
            return
        
        # Increment event counters
        self.redis_client.incr(f"security_metrics:events_total")
        self.redis_client.incr(f"security_metrics:events_by_type:{event.event_type}")
        self.redis_client.incr(f"security_metrics:events_by_severity:{event.severity.value}")
        
        # Update hourly metrics
        hour_key = event.timestamp.strftime("%Y-%m-%d-%H")
        self.redis_client.incr(f"security_metrics:hourly:{hour_key}")
        self.redis_client.expire(f"security_metrics:hourly:{hour_key}", 86400 * 7)  # 7 days
    
    def get_security_dashboard_data(self) -> Dict[str, Any]:
        """Get security dashboard data."""
        dashboard_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'active_incidents': len([i for i in self.active_incidents.values() 
                                   if i.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]]),
            'blocked_ips': len([ip for ip, data in self.ip_reputation.items() 
                               if data.get('blocked', False)]),
            'recent_events': len([e for e in self.event_buffer 
                                 if e.timestamp > datetime.utcnow() - timedelta(hours=1)]),
            'threat_level': self._calculate_overall_threat_level()
        }
        
        if self.redis_client:
            # Add metrics from Redis
            dashboard_data.update({
                'total_events': int(self.redis_client.get("security_metrics:events_total") or 0),
                'notifications': [
                    json.loads(notif) for notif in 
                    self.redis_client.lrange("security_notifications", 0, 9)
                ]
            })
        
        return dashboard_data
    
    def _calculate_overall_threat_level(self) -> str:
        """Calculate overall system threat level."""
        recent_events = [e for e in self.event_buffer 
                        if e.timestamp > datetime.utcnow() - timedelta(hours=1)]
        
        critical_events = sum(1 for e in recent_events if e.severity == ThreatLevel.CRITICAL)
        high_events = sum(1 for e in recent_events if e.severity == ThreatLevel.HIGH)
        
        if critical_events > 0:
            return "CRITICAL"
        elif high_events > 5:
            return "HIGH"
        elif len(recent_events) > 100:
            return "ELEVATED"
        else:
            return "NORMAL"


# Global security monitor instance
security_monitor = SecurityMonitor()