#!/usr/bin/env python3
"""
Skill Security Module
Unified interface for skill security: scanning, sandboxing, policies, and auditing.
"""

from pathlib import Path
from typing import Dict, List, Optional
import json

# Import components — try package-relative first (normal import), fall back
# to bare imports so this still works when run as a script from inside the
# skill-security/ directory.
try:
    from .scanner.skill_scanner import SkillScanner, scan_skill
    from .monitor.audit_logger import AuditLogger, SkillAuditContext, get_audit_logger
except ImportError:
    from scanner.skill_scanner import SkillScanner, scan_skill
    from monitor.audit_logger import AuditLogger, SkillAuditContext, get_audit_logger

# Policy loading — yaml is optional; without it, YAML policies can't be loaded
# but the rest of the module still works.
try:
    import yaml
    _HAS_YAML = True
except ImportError:
    yaml = None
    _HAS_YAML = False


def load_policy(policy_path: str) -> Dict:
    """Load a skill policy from YAML file. Requires PyYAML."""
    if not _HAS_YAML:
        raise ImportError("PyYAML is required to load policy files; pip install pyyaml")
    with open(policy_path) as f:
        return yaml.safe_load(f) or {}


def check_policy_compliance(skill_path: str, policy: Dict) -> Dict:
    """Check if a skill complies with its declared policy.

    Verifies:
      - A manifest exists (manifest.yaml preferred, SKILL.md frontmatter as fallback).
      - Declared permissions are a subset of policy['allowed_permissions'] (if set).
      - Declared capabilities are a subset of policy['allowed_capabilities'] (if set).

    Returns {"compliant": bool, "issues": [str, ...]}. An empty allow-list in
    the policy means "no restriction on that field" — only declared values
    above the listed allow-set produce violations.
    """
    skill_dir = Path(skill_path)
    issues: List[str] = []
    manifest: Dict = {}

    manifest_yaml = skill_dir / "manifest.yaml"
    manifest_md = skill_dir / "SKILL.md"

    if manifest_yaml.exists():
        if not _HAS_YAML:
            issues.append("manifest.yaml present but PyYAML not installed")
        else:
            try:
                with open(manifest_yaml) as f:
                    manifest = yaml.safe_load(f) or {}
            except Exception as e:
                issues.append(f"manifest.yaml unreadable: {e}")
    elif manifest_md.exists():
        # Best-effort YAML frontmatter parse from SKILL.md.
        text = manifest_md.read_text(encoding="utf-8", errors="replace")
        if text.startswith("---") and _HAS_YAML:
            try:
                _, fm, _ = text.split("---", 2)
                manifest = yaml.safe_load(fm) or {}
            except Exception:
                pass
    else:
        issues.append("no manifest found (manifest.yaml or SKILL.md)")

    declared_perms = set(manifest.get("permissions", []) or [])
    allowed_perms = set(policy.get("allowed_permissions", []) or [])
    if allowed_perms and not declared_perms.issubset(allowed_perms):
        issues.append(f"permissions exceed policy: {sorted(declared_perms - allowed_perms)}")

    declared_caps = set(manifest.get("capabilities", []) or [])
    allowed_caps = set(policy.get("allowed_capabilities", []) or [])
    if allowed_caps and not declared_caps.issubset(allowed_caps):
        issues.append(f"capabilities exceed policy: {sorted(declared_caps - allowed_caps)}")

    return {"compliant": len(issues) == 0, "issues": issues}

class SkillSecurityManager:
    """Main manager for skill security."""
    
    def __init__(self):
        self.scanner = SkillScanner()
        self.audit = AuditLogger()
    
    def pre_install_scan(self, skill_path: str) -> Dict:
        """Scan a skill before installation."""
        result = scan_skill(skill_path)
        
        if not result["safe"]:
            self.audit.logger.warning(
                f"BLOCKED: Skill {skill_path} failed security scan. "
                f"Issues: {len(result['issues'])}"
            )
        
        return result
    
    def enforce_policy(self, skill_id: str, policy: Dict) -> bool:
        """Enforce policy during skill execution."""
        # Check circuit breaker
        if self.audit.should_circuit_break(skill_id):
            self.audit.logger.error(f"CIRCUIT BREAKER: {skill_id}")
            return False
        
        return True
    
    def log_event(self, skill_id: str, event: str, data: Dict = None):
        """Log a skill event."""
        self.audit.log(skill_id, event, data or {})

# Default configuration
DEFAULT_CONFIG = {
    "sandbox": {
        "enabled": True,
        "network_mode": "none",
        "readonly_fs": True,
        "tmpfs": ["/tmp", "/workspace"]
    },
    "scanner": {
        "block_critical": True,
        "block_high": True,
        "min_score": 70
    },
    "circuit_breaker": {
        "failure_threshold": 5,
        "blocked_threshold": 10,
        "cooldown_seconds": 300
    },
    "audit": {
        "enabled": True,
        "log_dir": "~/.agent/logs"
    }
}

def get_default_config() -> Dict:
    """Get default security configuration."""
    return DEFAULT_CONFIG.copy()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Skill Security Module")
        print("Usage:")
        print("  python security.py scan <skill_path>   # Pre-install scan")
        print("  python security.py audit <skill_id>     # Get audit logs")
        print("  python security.py config               # Show default config")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "scan" and len(sys.argv) >= 3:
        result = scan_skill(sys.argv[2])
        print(json.dumps(result, indent=2))
    
    elif cmd == "audit" and len(sys.argv) >= 3:
        logger = get_audit_logger()
        events = logger.get_skill_events(sys.argv[2])
        print(json.dumps(events, indent=2))
    
    elif cmd == "config":
        print(json.dumps(get_default_config(), indent=2))
    
    else:
        print("Unknown command")
        sys.exit(1)
