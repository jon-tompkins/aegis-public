#!/usr/bin/env python3
"""
aegis-runtime — Bob's Aegis runtime utility agent.
Connects to the manifold mesh and provides Aegis-chain utility commands.

Usage:
    python3 aegis-runtime.py <command> [args...]

Commands:
    status                      — Overview of aegis-public repo state
    specs                       — List all Aegis specs and their status
    issues                      — List open GitHub issues on aegis-public
    issues-by-label <label>     — Filter issues by label
    mesh-status                 — Current manifold mesh status
    dark-circles                — Run manifold topology scan, surface dark circles
    screen-check <tx-hash>      — Check if a tx hash has been screened (mock)
    guardian-state              — Current guardian set state (mock)
    help                        — Show this help
"""
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

REPO = "jon-tompkins/aegis-public"
GITHUB_API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github.v3+json", "User-Agent": "aegis-runtime/1.0"}

# ── GitHub helpers ────────────────────────────────────────────────────────────────

def gh(path: str) -> dict:
    req = urllib.request.Request(GITHUB_API + path, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def get_open_issues(labels: str = None) -> list:
    url = f"/repos/{REPO}/issues?state=open&per_page=20"
    if labels:
        url += f"&labels={labels}"
    return gh(url)

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_status():
    """High-level status of Aegis project."""
    issues = get_open_issues()
    by_label = {}
    for issue in issues:
        for l in issue.get('labels', []):
            name = l['name']
            if name.startswith('tenet/') or name in ['aegis', 'bob', 'clark']:
                by_label.setdefault(name, []).append('#' + str(issue['number']))
    
    return {
        "agent": "aegis-runtime",
        "status": "ok",
        "open_issues": len(issues),
        "by_tracking_label": by_label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def cmd_specs():
    """List Aegis specs from docs/specs/ directory."""
    try:
        contents = gh(f"/repos/{REPO}/contents/docs/specs")
        specs = []
        for item in contents:
            if item['name'].endswith('.md'):
                specs.append({
                    "name": item['name'],
                    "size": item['size'],
                    "sha": item['sha'][:8],
                })
        return {"agent": "aegis-runtime", "specs": specs, "count": len(specs)}
    except Exception as e:
        return {"agent": "aegis-runtime", "error": str(e)}

def cmd_issues(labels: str = None):
    """List open issues, optionally filtered by label."""
    issues = get_open_issues(labels) if labels else get_open_issues()
    return {
        "agent": "aegis-runtime",
        "count": len(issues),
        "issues": [
            {
                "number": i['number'],
                "title": i['title'],
                "labels": [l['name'] for l in i.get('labels', [])],
                "state": i['state'],
                "url": i['html_url'],
            }
            for i in issues
        ]
    }

def cmd_issues_by_label(label: str):
    return cmd_issues(label)

def cmd_mesh_status():
    """Current status from bobiverse hub."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:8777/status", timeout=5) as r:
            data = json.loads(r.read())
            return {
                "agent": "aegis-runtime",
                "hub": data.get('hub'),
                "peers": data.get('peers'),
                "agents": data.get('agents'),
                "capabilities": data.get('capabilities'),
                "uptime_sec": data.get('uptime'),
                "status": "ok",
            }
    except Exception as e:
        return {"agent": "aegis-runtime", "error": str(e), "status": "degraded"}

def cmd_dark_circles():
    """Run manifold topology scan against local mesh agents."""
    import sys
    sys.path.insert(0, '/home/ubuntu/Manifold')
    from core.atlas import Atlas
    from core.registry import CapabilityRegistry

    _AGENTS = [
        {"name": "stella", "caps": ["identity-continuity", "session-memory", "conversation-strategy", "judgment", "personality-coherence", "context-management", "agent-orchestration", "terrain-awareness", "trust-modeling", "identity-modeling"]},
        {"name": "braid", "caps": ["solar-flare-prediction", "active-region-classification", "space-weather", "signal-processing", "machine-learning", "alfven-wave-timing", "alfven-clock", "lifecycle-modeling", "lifecycle-deployment"]},
        {"name": "manifold", "caps": ["cognitive-mesh", "agent-topology", "seam-detection", "sophia-score", "atlas-building", "topology-analysis", "mesh-mapping", "gap-detection", "transition-mapping", "structural-hole-id", "mesh-coordination", "agent-routing", "task-dispatch"]},
        {"name": "argue", "caps": ["debate", "adversarial-reasoning", "risk-analysis", "dilemma-navigation", "socratic-method", "crypto-analysis", "on-chain-data", "technical-analysis"]},
        {"name": "infra", "caps": ["infrastructure", "deployment", "observability", "scaling", "reliability"]},
        {"name": "solar-sites", "caps": ["solar-data", "site-analysis", "geo-mapping", "irradiance-modeling"]},
        {"name": "wake", "caps": ["weather-modeling", "wind-analysis", "forecast", "meteorological"]},
        {"name": "btc-signals", "caps": ["crypto-analysis", "on-chain-data", "signals", "price-tracking", "technical-analysis"]},
        {"name": "deploy", "caps": ["deployment", "devops", "ci-cd", "containerization", "orchestration"]},
        {"name": "solar-detect", "caps": ["solar-detection", "flare-detection", "solar-event", "space-weather"]},
        {"name": "data-detect", "caps": ["anomaly-detection", "pattern-recognition", "data-analysis", "signals"]},
        {"name": "cron-monitor", "caps": ["monitoring", "alerting", "scheduling", "heartbeat", "observability"]},
        {"name": "dev-tooling", "caps": ["tooling", "development", "code-generation", "refactoring"]},
        {"name": "hog-deploy", "caps": ["deployment", "hog", "automation", "orchestration"]},
        {"name": "void-watcher", "caps": ["void-monitoring", "process-watch", "lifecycle-tracking"]},
        {"name": "reach-scanner", "caps": ["reach-scanning", "capability-scanning", "gap-detection"]},
        {"name": "sentry", "caps": ["security-monitoring", "threat-detection", "alerting"]},
        {"name": "sophia", "caps": ["wisdom", "analysis", "pattern-synthesis", "philosophy"]},
        {"name": "deploy-strategist", "caps": ["deployment-strategy", "planning", "orchestration", "risk-assessment"]},
        {"name": "bob", "caps": ["sparkling-conversation", "aegis-design", "code-review", "aegis-chain-design", "spec-writing", "project-coordination"]},
    ]

    reg = CapabilityRegistry()
    for a in _AGENTS:
        reg.register_self(a['name'], a['caps'], 'mem://' + a['name'])

    atlas = Atlas.build(reg)
    holes = atlas.holes()
    high_k = atlas.high_curvature_regions(top_n=10)

    return {
        "agent": "aegis-runtime",
        "dark_circles": holes[:15],
        "high_curvature": [(t, round(s, 3)) for t, s in high_k[:5]],
        "mesh_size": len(_AGENTS),
        "status": "ok",
    }

def cmd_guardian_state():
    """Mock guardian state — replace with actual chain query."""
    return {
        "agent": "aegis-runtime",
        "status": "ok",
        "note": "mock — replace with actual chain query",
        "guardians": 3,
        "screened_today": 0,
        "escalations": 0,
    }

def cmd_screen_check(tx_hash: str = None):
    """Check screening status for a tx hash."""
    return {
        "agent": "aegis-runtime",
        "tx_hash": tx_hash or "none",
        "status": "ok",
        "note": "mock — replace with actual guardian query",
        "result": "not_screened",
    }

def cmd_help():
    return {
        "agent": "aegis-runtime",
        "commands": {
            "status": "Overview of aegis-public repo state",
            "specs": "List all Aegis specs",
            "issues [label]": "List open issues, optionally filtered",
            "issues-by-label <label>": "Filter issues by GitHub label",
            "mesh-status": "Current manifold mesh status from bobiverse",
            "dark-circles": "Run manifold topology scan, surface capability gaps",
            "guardian-state": "Current guardian set state (mock)",
            "screen-check <tx-hash>": "Check screening status for a tx",
        },
        "examples": [
            "aegis-runtime status",
            "aegis-runtime issues bob",
            "aegis-runtime dark-circles",
        ],
    }

# ── Dispatch ───────────────────────────────────────────────────────────────────

COMMANDS = {
    "status": cmd_status,
    "specs": cmd_specs,
    "issues": cmd_issues,
    "issues-by-label": lambda: cmd_issues_by_label(sys.argv[2] if len(sys.argv) > 2 else None),
    "mesh-status": cmd_mesh_status,
    "dark-circles": cmd_dark_circles,
    "guardian-state": cmd_guardian_state,
    "screen-check": lambda: cmd_screen_check(sys.argv[2] if len(sys.argv) > 2 else None),
    "help": cmd_help,
}

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "no command", "help": "run: aegis-runtime <command>"}))
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(json.dumps({"error": f"unknown command: {cmd}"}))
        sys.exit(1)

    result = COMMANDS[cmd]()
    print(json.dumps(result))

if __name__ == "__main__":
    main()
