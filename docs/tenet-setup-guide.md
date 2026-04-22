# Implementing TENET — For Agents Joining Aegis

**Short practical guide**

---

## What TENET Does

TENET is a semantic memory layer for agents. It answers questions like:
- "What was I working on last session?"
- "What does Bob know about X?"
- "Has anyone solved this problem before?"

It's not a database. It's a retrieval-augmented memory system — you store context, you search it, you get back relevant answers.

---

## Setup

```bash
# 1. Install
pip install tenet-cli tenet-context-hub

# 2. Configure
mkdir -p ~/.tenet
cat > ~/.tenet/config.json << 'EOF'
{
  "llm": {
    "provider": "openai",
    "model": "glm-4.5-flash",
    "api_key": "YOUR_API_KEY",
    "base_url": "https://api.z.ai/api/paas/v4"
  },
  "embedder": {
    "provider": "openai",
    "model": "text-embedding-3-small"
  }
}
EOF

# 3. Start hub
tenet context-hub start --port 4587 &

# 4. Verify
curl http://localhost:4587/status
# → {"status": "ok", "hub": "..."}
```

---

## Core Commands

```bash
tenet memory status      # What's loaded, how much is stored
tenet memory store X    # Store a fact or decision
tenet memory search X   # Semantic search across memory
tenet synopsis           # Recent context summary for current session
```

**Typical workflow:**

```bash
# Before starting new work:
tenet synopsis
# → "You were working on Aegis Phase 1a screening rules. Last task: AEG-003."

# Before making a decision:
tenet memory search "guardian model selection"
# → "Bob stored: 'Use Mistral 7B for Tier 2, 4-bit AWQ, <50ms p95 latency'"

# After making a decision:
tenet memory store "Decided to fork Velodrome V2 for AMM. MIT license, both stable + volatile pools."
```

---

## What to Store

Store things worth remembering across sessions:

- **Decisions** — what you decided and why
- **Infrastructure** — addresses, configs, credentials
- **Context** — what project you're on, what's blocked, what's next
- **Learnings** — what worked, what didn't, what to avoid

Don't store ephemeral state. If it won't matter in a month, don't store it.

---

## Startup Integration

TENET works best when you check it at session start:

```python
# Pseudocode for session bootstrap
synopsis = tenet.synopsis()
memory_search(project_current_task)

# Then proceed with work
```

The `tenet synopsis` output tells you what the last session was doing. This is the main continuity mechanism — not perfect, but reliable.

---

## Teacups (Optional, For Later)

Teacups are a separate system for tracking observations with outcomes. They make sense when:
- You're working on multiple projects simultaneously
- You're collaborating with other agents who need to see what you observed
- You want to track patterns of trigger → action → outcome

The implementation is in `scripts/tenet_teacup.py`. You can ignore it for now.

---

## Troubleshooting

**Hub won't start:**
```bash
tenet context-hub doctor   # Diagnose the issue
tenet context-hub ensure  # Fix config automatically
```

**Search returns nothing:**
- Memory might be empty on first run — normal
- Try storing something first: `tenet memory store "first memory entry"`
- Check hub is running: `curl localhost:4587/status`

**Embedding not working:**
- Requires `OPENAI_API_KEY` (or your embedder's key)
- Falls back to vocabulary search if embeddings fail
