from typing import List, Dict

# ── Per-task grader registry (required by OpenEnv evaluator) ──────────────────
GRADERS = {
    "easy":   "deterministic",
    "medium": "deterministic",
    "hard":   "deterministic",
    "gmail":  "heuristic",
}

def get_grader(task_name: str) -> str:
    """Return the grader type for a given task name."""
    return GRADERS.get(task_name, "deterministic")


def grade_step(predicted: dict, true: dict) -> float:
    """
    Core grading logic for a single decision.
    Returns 0.99, 0.3, or 0.01 to stay strictly within (0, 1).
    """
    decision_match = predicted.get("decision") == true.get("correct_decision")
    priority_match = predicted.get("priority") == true.get("correct_priority")

    if decision_match and priority_match:
        return 0.99

    if decision_match:
        return 0.3

    return 0.01


def grade(history: List[Dict], task_name: str = "easy") -> float:
    """
    Task Grader following [0.99, 0.3, 0.01] format.
    Calculates the average of all step grades.
    """
    if not history:
        return 0.01

    total_score = 0.0
    for step in history:
        total_score += grade_step(step["action"], step)

    average_score = total_score / len(history)
    return round(max(0.01, min(0.99, average_score)), 4)


def grade_easy(history: List[Dict]) -> float:
    """Grader for the 'easy' task."""
    return grade(history, task_name="easy")


def grade_medium(history: List[Dict]) -> float:
    """Grader for the 'medium' task."""
    return grade(history, task_name="medium")


def grade_hard(history: List[Dict]) -> float:
    """Grader for the 'hard' task."""
    return grade(history, task_name="hard")


def grade_gmail(results: List[Dict]) -> dict:
    """
    Grade a list of Gmail triage results (no ground-truth labels).
    Uses heuristic confidence scoring instead of exact match.
    Returns a summary dict with per-decision stats.
    """
    if not results:
        return {"score": 0.01, "total": 0, "by_decision": {}}

    by_decision = {"escalate": 0, "reply": 0, "ignore": 0}
    by_priority = {"high": 0, "medium": 0, "low": 0}

    for r in results:
        dec = r.get("decision", "ignore")
        pri = r.get("priority", "low")
        by_decision[dec] = by_decision.get(dec, 0) + 1
        by_priority[pri] = by_priority.get(pri, 0) + 1

    total = len(results)
    return {
        "total": total,
        "by_decision": by_decision,
        "by_priority": by_priority,
        "escalate_rate": round(by_decision["escalate"] / total, 2),
        "reply_rate": round(by_decision["reply"] / total, 2),
        "ignore_rate": round(by_decision["ignore"] / total, 2),
    }
