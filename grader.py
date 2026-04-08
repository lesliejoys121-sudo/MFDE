from typing import List, Dict

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

def grade(history: List[Dict]) -> float:
    """
    Task Grader following requested [0.99, 0.3, 0.01] format.
    Calculates the average of all step grades.
    """
    if not history:
        return 0.01
    
    total_score = 0.0
    for step in history:
        # Extract action and correct labels from history logs
        total_score += grade_step(step["action"], step)
        
    # Ensure final aggregate is strictly between 0 and 1
    average_score = total_score / len(history)
    return round(max(0.01, min(0.99, average_score)), 4)
