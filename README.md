---
title: MFDE-Email-Triage
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# 🧠 MFDE: Misleading Feedback Decision Environment

[![OpenEnv](https://img.shields.io/badge/Spec-OpenEnv--2.0-blue)](https://github.com/openenv)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-HuggingFace-yellow)](https://huggingface.co/spaces)

MFDE is a professional-grade **Email Triage Simulation** designed to evaluate and train AI agents in handling **high-stakes decisions under misleading feedback**. Now updated to **v2.0** with real Gmail integration and calibrated deterministic scoring.

---

## 🌍 Real-World Utility (30% Weighting)

In modern Security Operations (SecOps), feedback loops are often corrupted by noisy signals, look-alike domains, and biased human review. MFDE models this "Reality Gap" by forcing agents to choose between:
1.  **Trusting the Evidence**: Analyzing the raw email content for deceptive patterns.
2.  **Trusting the Reward**: Following potentially corrupted feedback signals that may penalize correct security escalations.

This environment is immediately valuable for the RL community to test **agentic resilience and calibration** in enterprise-critical workflows.

---

## 👁️ v2.0 Extended Features

- **Real Gmail connectivity** — Connect any inbox via MCP and triage live telemetry.
- **Claude-Powered Inference** — Multi-modal baseline agents for high-fidelity triage.
- **Calibrated Scoring** — Strictly deterministic rewards in the (0.02, 0.98) safe range.
- **Glassmorphic Dashboard** — Professional real-time analytics for human-in-the-loop monitoring.

---

## 👁️ Technical Specifications

### Observation Space
The environment provides structured email metadata:
| Field | Type | Description |
|---|---|---|
| `email_text` | `string` | The full raw body of the email |
| `sender` | `string` | The sender address (critical for phishing detection) |
| `subject` | `string` | The subject line |
| `step_count` | `int` | Progress within the current task |

### Action Space (JSON)
The agent must submit a precise triage decision:
```json
{
  "decision": "reply | ignore | escalate",
  "priority": "low | medium | high"
}
```

---

## 🎯 Task Tiers & Difficulty

| Tier | Steps | Noise ✅ | Description |
|---|---|---|---|
| **EASY** | 5 | 0% | Clear signals. Noisy rewards are disabled. Tests basic triage logic. |
| **MEDIUM** | 7 | 30% | Deceptive "CEO Fraud" emails. Reward signals can be randomly misleading. |
| **HARD** | 10 | 50% | Advanced phishing (Repo mimics, Metamask drains). High-variance rewards. |
| **GMAIL** | varies | 0% | Real-life telemetry fetched via MCP. AI-graded by Claude. |

---

## 🧮 Reward & Grader Design

### Calibrated Tiers
MFDE provides **dense signal** with strict adherence to OpenEnv range compliance:
- **Full Success** (Decision & Priority correct): `0.98`
- **Partial Success** (Decision correct only): `0.55`
- **Failure** (Incorrect decision): `0.02`

Medium and Hard tasks inject reward noise based on the task difficulty, simulating real-world signal corruption while staying within the `(0.01, 0.99)` safe interval.

### Deterministic Grader
Compliance with the hackathon rubric is guaranteed via `grader.py`:
- **Function**: `grade(history) -> float [0.0 - 1.0]`
- Calculated by averaging total weighted rewards across the trajectory and clamping to 2 decimal places for precision.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- [Docker](https://www.docker.com/) (for containerized execution)

### Local Launch
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
python -m uvicorn app:app --host 0.0.0.0 --port 7860
```

### Baseline Inference (Reproduction)
Our `inference.py` uses the standard OpenAI client and supports heuristic fallbacks:
```bash
# Set credentials for Claude AI inference
export HF_TOKEN="your-hf-token"
export API_BASE_URL="https://router.huggingface.co/v1"
python inference.py
```

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reset` | Reset environment, pick task (easy/medium/hard) |
| POST | `/step` | Submit triage action, get reward |
| GET | `/state` | Current episode state + history |
| GET | `/api/performance` | Score, streak, rank (2-decimal precision) |
| POST | `/api/gmail/fetch` | Fetch real Gmail emails via MCP |
| POST | `/api/gmail/triage` | Triage emails with Claude AI |

---

## 🏗️ Spec Compliance Checklist
- [x] **Typed Models**: Full Pydantic V2 implementation in `models.py`.
- [x] **Standard API**: `/reset`, `/step`, and `/state` endpoints functional.
- [x] **Containerized**: `Dockerfile` tested for HF Spaces UID 1000.
- [x] **Calibrated**: Rewards strictly within `(0.01, 0.99)`.
- [x] **Structured Logs**: Baseline script outputs exact `[START]/[STEP]/[END]` format.
- [x] **Deterministic**: All graders are 100% reproducible.

---

## 📊 Baseline Scores (Reproduce with `random.seed(42)`)

| Task   | Steps | Baseline Score | Success |
|--------|-------|---------------|---------|
| Easy   | 5     | 0.60          | ✅ Yes  |
| Medium | 7     | 0.84          | ✅ Yes  |
| Hard   | 10    | 0.79          | ✅ Yes  |

*Reproduced using deterministic heuristic fallback.*

---

## 🏗️ File Structure

```
mfde-main/
├── app.py            # FastAPI server (standard + Gmail endpoints)
├── env.py            # MFDEEnv with Gmail support
├── models.py         # Pydantic models (incl. Gmail models)
├── tasks.py          # Simulation task definitions
├── grader.py         # Grading logic (simulation + Gmail)
├── inference.py      # AI inference script (simulation + Gmail)
├── dashboard.html    # Professional Glassmorphic UI
├── openenv.yaml      # OpenEnv spec
├── Dockerfile        # HF Spaces compatible (UID 1000)
└── requirements.txt  # Dependencies
```
