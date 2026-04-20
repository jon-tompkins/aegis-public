# Aegis Runtime Agent

**Version:** 1.0.0  
**Date:** 2026-04-20  
**Hub:** bobiverse  

A lightweight agent that connects to the Manifold mesh and provides Aegis Chain utility commands. Any agent on the mesh can call it.

## Running

```bash
# From bobiverse hub directory
cd /home/ubuntu/Manifold/federation
node register-aegis-runtime.mjs
```

Or via the agent runner:

```bash
python3 /home/ubuntu/Manifold/federation/src/runtime/agent-runner.py \
  --config /home/ubuntu/Manifold/federation/runner-config.bob.json \
  --ws ws://localhost:8768
```

## Commands

| Command | Description |
|---------|-------------|
| `status` | Overview of aegis-public repo state |
| `specs` | List all Aegis specs in docs/specs/ |
| `issues [label]` | List open GitHub issues, optionally filtered |
| `issues-by-label <label>` | Filter issues by label |
| `mesh-status` | Current manifold mesh status from bobiverse |
| `dark-circles` | Manifold topology scan, surface capability gaps |
| `guardian-state` | Current guardian set state (mock) |
| `screen-check <tx-hash>` | Check screening status for a tx (mock) |

## Example Usage

```bash
# From any mesh hub
curl -s -X POST http://localhost:8777/task \
  -H 'Content-Type: application/json' \
  -d '{"target":"aegis-runtime@bobiverse","command":"dark-circles","timeout_ms":15000}'

curl -s -X POST http://localhost:8777/task \
  -H 'Content-Type: application/json' \
  -d '{"target":"aegis-runtime@bobiverse","command":"status","timeout_ms":15000}'
```

## Adding as an OpenClaw Subagent

Add to your OpenClaw config (`~/.openclaw/openclaw.json`):

```json
{
  "agents": {
    "subagents": {
      "aegis-runtime": {
        "runtime": "manifold",
        "hub": "bobiverse",
        "script": "/path/to/aegis-runtime.py"
      }
    }
  }
}
```

## Adding to Mesh Runner Config

Add to `runner-config.bob.json`:

```json
{
  "name": "aegis-runtime",
  "script": "/home/ubuntu/agents/aegis-runtime.py",
  "timeout_ms": 30000,
  "maxConcurrency": 1,
  "capabilities": [
    "aegis-status",
    "aegis-specs",
    "aegis-issues",
    "aegis-mesh-status",
    "aegis-dark-circles",
    "guardian-state",
    "screen-check"
  ]
}
```
