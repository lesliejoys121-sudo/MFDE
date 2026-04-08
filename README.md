---
title: MFDE-Email-Triage
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# 🧠 MFDE: Misleading Feedback Decision Environment

[![OpenEnv](https://img.shields.io/badge/Spec-OpenEnv--1.0-blue)](https://github.com/openenv)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-HuggingFace-yellow)](https://huggingface.co/spaces)

MFDE is a professional-grade **Email Triage Simulation** designed to evaluate and train AI agents in handling **high-stakes decisions under misleading feedback**.

---

## 🌍 Real-World Utility (30% Weighting)

In modern Security Operations (SecOps), feedback loops are often corrupted by noisy signals, look-alike domains, and biased human review. MFDE models this "Reality Gap" by forcing agents to choose between:
1.  **Trusting the Evidence**: Analyzing the raw email content for deceptive patterns.
2.  **Trusting the Reward**: Following potentially corrupted feedback signals that may penalize correct security escalations.

This environment is immediately valuable for the RL community to test **agentic resilience and calibration** in enterprise-critical workflows.

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

MFDE includes 3 curated tasks that range from simple classification to adversarial security challenges.

| Tier | Steps | Noise ✅ | Description |
|---|---|---|---|
| **EASY** | 5 | 0% | Clear signals. Noisy rewards are disabled. Tests basic triage logic. |
| **MEDIUM** | 7 | 30% | Deceptive "CEO Fraud" emails. Reward signals can be randomly misleading. |
| **HARD** | 10 | 50% | Advanced phishing (Repo mimics, Metamask drains). High-variance rewards. |

---

## 🧮 Reward & Grader Design

### Partial Progress Reward
MFDE provides **dense signal** over the trajectory:
- **Base Reward**: `+0.6` for correct decision, `+0.4` for correct priority.
- **Difficulty Multiplier**: Medium (1.5x), Hard (2.0x).
- **Streak Bonus**: Each consecutive correct triage adds a `+10%` bonus (up to `+50%`).

### Deterministic Grader
Compliance with the hackathon rubric is guaranteed via `grader.py`:
- **Function**: `grade(history) -> float [0.01 - 0.99]`
- Calculated by averaging total weighted rewards across the trajectory and normalizing to a 1.0 scale.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- [Docker](https://www.docker.com/) (for containerized execution)

### Local Launch
```bash
pip install -r requirements.txt
python app.py
```

### Baseline Inference (Reproduction)
Our `inference.py` uses the standard OpenAI client and reads from environment variables:
```bash
export API_BASE_URL="https://your-api-endpoint"
export MODEL_NAME="gpt-4"
export HF_TOKEN="your-hf-token"
python inference.py
```

---

## 🏗️ Spec Compliance Checklist
- [x] **Typed Models**: Full Pydantic V2 implementation in `models.py`.
- [x] **Standard API**: `/reset`, `/step`, and `/state` endpoints functional.
- [x] **Containerized**: `Dockerfile` tested for HF Spaces UID 1000.
- [x] **Structured Logs**: Baseline script outputs exact `[START]/[STEP]/[END]` format.
- [x] **Deterministic**: All graders are 100% reproducible.
