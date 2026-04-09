"""
grader.py — MFDE Email Triage Graders
======================================
Each task has a dedicated grader function: grade_easy, grade_medium, grade_hard.
The evaluator enumerates these by name and calls them with a list of agent actions.

Grader contract (OpenEnv):
  - Input:  list of dicts, each with keys: decision, priority
  - Output: float in [0.00, 0.99]
  - Must return VARYING scores (not always the same value)
  - Must be deterministic and reproducible
"""

from typing import List, Dict


# ── Ground-truth answers per task ─────────────────────────────────────────────

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


# ── Core step grader ──────────────────────────────────────────────────────────

def _score_step(action: dict, answer: dict) -> float:
    """
    Score a single triage decision against ground truth.
    Strictly stays within [0.02, 0.98] to satisfy validator.
    """
    decision_ok = action.get("decision") == answer.get("correct_decision")
    priority_ok = action.get("priority") == answer.get("correct_priority")
    
    if decision_ok and priority_ok:
        return 0.98
    if decision_ok:
        return 0.55
    return 0.02


def _grade_against(actions: List[Dict], answers: List[Dict]) -> float:
    """Grade actions vs ground-truth answers. Returns float in [0.02, 0.98]."""
    if not actions:
        return 0.02
    total = 0.0
    count = min(len(actions), len(answers))
    for i in range(count):
        total += _score_step(actions[i], answers[i])
    # Average and ensure we don't hit 0.0 or 1.0 even with rounding
    return round(total / len(answers), 4)


# ── Public per-task graders (called by OpenEnv evaluator) ────────────────────

def grade_easy(actions: List[Dict]) -> float:
    """Grader for the 'easy' task (5 emails). Returns [0.02, 0.98]."""
    return _grade_against(actions, _EASY_ANSWERS)


def grade_medium(actions: List[Dict]) -> float:
    """Grader for the 'medium' task (7 emails). Returns [0.02, 0.98]."""
    return _grade_against(actions, _MEDIUM_ANSWERS)


def grade_hard(actions: List[Dict]) -> float:
    """Grader for the 'hard' task (10 emails). Returns [0.02, 0.98]."""
    return _grade_against(actions, _HARD_ANSWERS)


# ── Internal helpers (used by env.py and app.py) ─────────────────────────────

def grade_step(predicted: dict, true: dict) -> float:
    """Legacy step grader used internally by MFDEEnv."""
    return _score_step(predicted, true)


def grade(history: List[Dict], task_name: str = "easy") -> float:
    """Grade a completed episode history (used by env.py). Returns [0.02, 0.98]."""
    if not history:
        return 0.02
    total = 0.0
    for step in history:
        action = step.get("action", {})
        answer = {
            "correct_decision": step.get("correct_decision"),
            "correct_priority": step.get("correct_priority"),
        }
        total += _score_step(action, answer)
    return round(total / len(history), 4)


def grade_gmail(results: List[Dict]) -> dict:
    """Summarise Gmail triage results without ground-truth."""
    if not results:
        return {"score": 0.02, "total": 0, "by_decision": {}, "by_priority": {}}
    
    by_decision = {"escalate": 0, "reply": 0, "ignore": 0}
    by_priority  = {"high": 0, "medium": 0, "low": 0}
    
    for r in results:
        dec = r.get("decision", "ignore")
        pri = r.get("priority", "low")
        by_decision[dec] = by_decision.get(dec, 0) + 1
        by_priority[pri]  = by_priority.get(pri, 0) + 1
        
    total = len(results)
    ignore_rate = by_decision["ignore"] / total if total > 0 else 1.0
    # Heuristic score between 0.02 and 0.98
    score = round(max(0.02, min(0.98, 1.0 - ignore_rate * 0.5)), 4)
    
    return {
        "score": score,
        "total": total,
        "by_decision": by_decision,
        "by_priority": by_priority,
        "reply_rate":    round(by_decision["reply"] / total, 2) if total > 0 else 0,
        "ignore_rate":   round(ignore_rate, 2),
    }
