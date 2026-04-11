"""
grader.py — MFDE Email Triage Graders
======================================
Grader contract (OpenEnv):
  - grade_easy / grade_medium / grade_hard accept a list of action dicts
  - Each returns a float in [0.0, 1.0]
  - Scores vary with agent quality (not constant)
"""

from typing import List, Dict

# ── Ground-truth answer keys per task ────────────────────────────────────────

_EASY_ANSWERS = [
    {"correct_decision": "reply",    "correct_priority": "medium"},
    {"correct_decision": "ignore",   "correct_priority": "low"},
    {"correct_decision": "escalate", "correct_priority": "high"},
    {"correct_decision": "ignore",   "correct_priority": "low"},
    {"correct_decision": "reply",    "correct_priority": "medium"},
]

_MEDIUM_ANSWERS = [
    {"correct_decision": "ignore",   "correct_priority": "low"},
    {"correct_decision": "reply",    "correct_priority": "medium"},
    {"correct_decision": "escalate", "correct_priority": "high"},
    {"correct_decision": "reply",    "correct_priority": "medium"},
    {"correct_decision": "ignore",   "correct_priority": "low"},
    {"correct_decision": "escalate", "correct_priority": "high"},
    {"correct_decision": "reply",    "correct_priority": "medium"},
]

_HARD_ANSWERS = [
    {"correct_decision": "ignore",   "correct_priority": "low"},
    {"correct_decision": "reply",    "correct_priority": "medium"},
    {"correct_decision": "escalate", "correct_priority": "high"},
    {"correct_decision": "ignore",   "correct_priority": "low"},
    {"correct_decision": "reply",    "correct_priority": "medium"},
    {"correct_decision": "escalate", "correct_priority": "high"},
    {"correct_decision": "ignore",   "correct_priority": "low"},
    {"correct_decision": "ignore",   "correct_priority": "low"},
    {"correct_decision": "reply",    "correct_priority": "medium"},
    {"correct_decision": "escalate", "correct_priority": "high"},
]


# ── Core scoring ──────────────────────────────────────────────────────────────

def _score_step(action: dict, answer: dict) -> float:
    """
    Score a single triage decision against ground truth.
    Returns values strictly within open interval (0.0, 1.0).
    """
    dec_ok = action.get("decision") == answer.get("correct_decision")
    pri_ok = action.get("priority") == answer.get("correct_priority")
    if dec_ok and pri_ok:
        return 0.98   # Both correct — strictly below 1.0
    if dec_ok:
        return 0.55   # Decision right, priority wrong
    return 0.02       # Wrong decision — strictly above 0.0


def _grade_against(actions: List[Dict], answers: List[Dict]) -> float:
    """Average score over all answer slots. Penalises missing steps."""
    if not actions or not answers:
        return 0.0
    total = sum(_score_step(actions[i], answers[i]) for i in range(min(len(actions), len(answers))))
    return round(total / len(answers), 4)


# ── Public per-task graders ───────────────────────────────────────────────────

def grade_easy(actions: List[Dict]) -> float:
    """Grader for 'easy' task — 5 emails, clear signals. Returns [0.0, 1.0]."""
    return _grade_against(actions, _EASY_ANSWERS)


def grade_medium(actions: List[Dict]) -> float:
    """Grader for 'medium' task — 7 emails, some deception. Returns [0.0, 1.0]."""
    return _grade_against(actions, _MEDIUM_ANSWERS)


def grade_hard(actions: List[Dict]) -> float:
    """Grader for 'hard' task — 10 emails, highly deceptive. Returns [0.0, 1.0]."""
    return _grade_against(actions, _HARD_ANSWERS)


# ── Internal helpers used by env.py / app.py ─────────────────────────────────

def grade_step(predicted: dict, true: dict) -> float:
    """Single-step grader for use inside MFDEEnv.step()."""
    return _score_step(predicted, true)


def grade(history: List[Dict]) -> float:
    """
    Task Grader — returns float strictly within (0.0, 1.0).
    Averages grade_step scores across the full episode trajectory.
    """
    if not history:
        return 0.02   # No history — strictly above 0.0

    total_score = 0.0
    for step in history:
        # Compatibility with MFDEEnv history format
        action = step.get("action", {})
        answer = {
            "correct_decision": step.get("correct_decision"),
            "correct_priority": step.get("correct_priority"),
        }
        total_score += _score_step(action, answer)

    average_score = total_score / len(history)

    # Clamp with safe margins well away from 0.0 and 1.0
    return round(max(0.02, min(0.98, average_score)), 4)


def grade_gmail(results: List[Dict]) -> dict:
    """Summarise Gmail triage results (no ground truth). Returns summary dict."""
    if not results:
        return {"score": 0.0, "total": 0, "by_decision": {}, "by_priority": {}}
    by_decision = {"escalate": 0, "reply": 0, "ignore": 0}
    by_priority  = {"high": 0, "medium": 0, "low": 0}
    for r in results:
        by_decision[r.get("decision", "ignore")] = by_decision.get(r.get("decision", "ignore"), 0) + 1
        by_priority[r.get("priority", "low")]    = by_priority.get(r.get("priority", "low"), 0) + 1
    total = len(results)
    ignore_rate = by_decision["ignore"] / total
    return {
        "score":        round(max(0.0, min(1.0, 1.0 - ignore_rate * 0.5)), 4),
        "total":        total,
        "by_decision":  by_decision,
        "by_priority":  by_priority,
        "escalate_rate": round(by_decision["escalate"] / total, 2),
        "reply_rate":    round(by_decision["reply"] / total, 2),
        "ignore_rate":   round(ignore_rate, 2),
    }