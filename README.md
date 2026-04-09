# 🧠 MFDE: Misleading Feedback Decision Environment — v2.0

[![OpenEnv](https://img.shields.io/badge/Spec-OpenEnv--2.0-blue)](https://github.com/openenv)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-HuggingFace-yellow)](https://huggingface.co/spaces)

MFDE is a professional-grade **Email Triage Simulation** that evaluates AI agents on high-stakes decisions under misleading feedback — now extended with **real Gmail inbox integration**.

---

## What's New in v2.0

- **Real Gmail support** — connect any Gmail account via MCP and triage real emails
- **AI-powered inference** — `inference.py` now uses Claude instead of keyword heuristics
- **Two new API endpoints** — `/api/gmail/fetch` and `/api/gmail/triage`
- **Standalone triage script** — `gmail_triage.py` for CLI-only Gmail triage
- **No ground-truth required** — Gmail emails are graded by pattern analysis, not labels

---

## Quick Start

### 1. Install & run locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### 2. Run simulation inference (easy/medium/hard tasks)

```bash
python inference.py --task easy
python inference.py --task hard
```

### 3. Triage your real Gmail inbox

```bash
# Via the server API (server must be running)
python inference.py --gmail --max-emails 15

# Standalone (no server needed)
python gmail_triage.py
```

### 4. Docker

```bash
docker build -t mfde .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY="your-key-here" \
  mfde
```

---

## API Endpoints

### Standard OpenEnv

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reset` | Reset environment, pick task (easy/medium/hard) |
| POST | `/step` | Submit triage action, get reward |
| GET | `/state` | Current episode state + history |
| GET | `/api/performance` | Score, streak, rank |
| POST | `/api/scan` | Stateless scam scanner |

### Gmail Integration

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/gmail/fetch` | Fetch real Gmail emails via MCP, load into env |
| POST | `/api/gmail/triage` | Triage a list of emails with Claude AI |

#### Example: Fetch Gmail

```bash
curl -X POST http://localhost:8000/api/gmail/fetch \
  -H "Content-Type: application/json" \
  -d '{"max_emails": 10}'
```

#### Example: Triage emails

```bash
curl -X POST http://localhost:8000/api/gmail/triage \
  -H "Content-Type: application/json" \
  -d '{
    "emails": [
      {
        "from": "boss@company.com",
        "from_name": "Alice",
        "subject": "Urgent: server down",
        "snippet": "Production is offline. Need immediate help."
      }
    ]
  }'
```

Response:
```json
{
  "results": [
    {
      "email_index": 0,
      "from_address": "boss@company.com",
      "subject": "Urgent: server down",
      "decision": "escalate",
      "priority": "high",
      "reason": "Production outage requires immediate escalation.",
      "score": 0.5
    }
  ],
  "summary": {
    "total": 1,
    "by_decision": {"escalate": 1, "reply": 0, "ignore": 0},
    "by_priority": {"high": 1, "medium": 0, "low": 0}
  }
}
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key (required for Gmail + AI triage) | — |
| `GMAIL_MCP_URL` | Gmail MCP server URL | `https://gmail.mcp.claude.com/mcp` |
| `API_BASE_URL` | MFDE server URL (for inference.py) | `http://localhost:8000` |
| `MODEL_NAME` | Claude model for inference | `claude-sonnet-4-20250514` |

---

## Task Tiers

| Tier | Steps | Noise | Description |
|------|-------|-------|-------------|
| easy | 5 | 0% | Clear signals, basic triage |
| medium | 7 | 30% | CEO fraud, deceptive emails |
| hard | 10 | 50% | Advanced phishing, high variance |
| gmail | varies | 0% | Real inbox, AI-graded |

---

## Reward Design

- `escalate + high` (both correct) → **0.99**
- Decision correct only → **0.30**
- Decision wrong → **0.01**
- Medium/Hard tasks inject reward noise to simulate corrupted feedback loops
- Gmail mode: no noise, heuristic scoring since there are no ground-truth labels

---

## File Structure

```
mfde-gmail/
├── app.py            # FastAPI server (standard + Gmail endpoints)
├── env.py            # MFDEEnv with Gmail support
├── models.py         # Pydantic models (incl. Gmail models)
├── tasks.py          # Simulation task definitions
├── grader.py         # Grading logic (simulation + Gmail)
├── inference.py      # AI inference script (simulation + Gmail)
├── gmail_triage.py   # Standalone CLI Gmail triage tool
├── openenv.yaml      # OpenEnv spec
├── Dockerfile        # HF Spaces compatible (UID 1000)
└── requirements.txt  # Dependencies
```
