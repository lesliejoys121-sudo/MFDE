import random
import numpy as np
from typing import Tuple, Dict, Any
from models import Observation, Action, Reward, State
from tasks import TASKS

class MFDEEnv:
    def __init__(self):
        self.task_name = "easy"
        self.mode = "simulation"
        self.total_score = 0.01  # Normalized average for validator
        self.cumulative_xp = 0.01 # Sum for Dashboard UI
        self.session_score = 0.01
        self.is_done = False
        self.history = []
        # Fix seed for reproducibility across environments
        random.seed(42)
        np.random.seed(42)

    def reset(self, task: str = "easy", mode: str = "simulation") -> Observation:
        if task not in TASKS:
            task = "easy"
        self.task_name = task
        self.mode = mode
        self.current_step = 0
        self.current_streak = 0
        self.total_score = 0.01
        self.is_done = False
        self.history = []
        
        # Shuffle for simulation mode to provide variety for agents
        if mode == "simulation":
            random.shuffle(TASKS[self.task_name]["emails"])
        
        return self._get_obs()

    def get_task_emails(self, task: str) -> list:
        """Helper for the Dashboard Inbox view."""
        if task not in TASKS: return []
        return TASKS[task]["emails"]

    def scan(self, text: str) -> dict:
        """
        Stateless Scanner for arbitrary text (Real-World Utility).
        Identifies scam patterns without storing data.
        """
        text_lower = text.lower()
        scam_keywords = ["urgent", "refund", "gift card", "ceo", "bitcoin", "password expire", "unauthorized", "bank account", "winner", "prize"]
        matches = [kw for kw in scam_keywords if kw in text_lower]
        
        # Simple heuristic for demo purposes
        score = len(matches) / 5.0
        prediction = "escalate" if score > 0.4 else ("reply" if score > 0.1 else "ignore")
        priority = "high" if score > 0.6 else ("medium" if score > 0.2 else "low")
        
        return {
            "scam_likelihood": round(max(0.01, min(0.99, score)), 2),
            "suggested_action": prediction,
            "suggested_priority": priority,
            "detected_patterns": matches[:3]
        }

    def _get_obs(self) -> Observation:
        task_data = TASKS[self.task_name]
        email = task_data["emails"][self.current_step]
        return Observation(
            email_text=email["email_text"],
            sender=email["sender"],
            subject=email["subject"],
            step_count=self.current_step
        )

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        if self.is_done:
            raise RuntimeError("Episode is already finished. Call reset() first.")

        task_data = TASKS[self.task_name]
        
        # Sync to specific ID if provided (for Dashboard correctness)
        if action.email_id is not None and 0 <= action.email_id < len(task_data["emails"]):
            self.current_step = action.email_id
            
        email = task_data["emails"][self.current_step]
        
        # 2. Match Logic
        decision_match = (action.decision == email["correct_decision"])
        priority_match = (action.priority == email["correct_priority"])
        
        # 3. Base Metrics (for Logging/History)
        base_reward = (0.6 if decision_match else 0.0) + (0.4 if priority_match else 0.0)
        multipliers = {"easy": 1.0, "medium": 1.5, "hard": 2.0}
        multiplier = multipliers.get(self.task_name, 1.0)

        # Core Reward Logic (following requested [0.99, 0.3, 0.01] format)
        if decision_match and priority_match:
            true_reward = 0.99
            self.current_streak += 1
        elif decision_match:
            true_reward = 0.3
            self.current_streak = 0
        else:
            true_reward = 0.01
            self.current_streak = 0
            
        # 4. Score Management
        self.cumulative_xp += true_reward
        self.session_score += true_reward
        
        # Calculate running average for total_score (Phase 2 compliance)
        average = self.cumulative_xp / (self.current_step + 1)
        self.total_score = round(max(0.01, min(0.99, average)), 4)
        
        # Add to history
        self.history.append({
            "step": self.current_step,
            "observation": self._get_obs().model_dump(),
            "action": action.model_dump(),
            "true_reward": true_reward,
            "streak": self.current_streak,
            "correct_decision": email["correct_decision"],
            "correct_priority": email["correct_priority"],
            "reason": email.get("reason", "N/A")
        })
        
        # NOISY reward to provide back to the agent
        # Noise used for feedback (agent sees this)
        feedback_reward = round(true_reward, 2)  # default: true reward (may be >1 for hard+streak)
        if random.random() < task_data.get("reward_noise_prob", 0.0):
            # Add/subtract random noise, capped to [0.01, 0.99]
            noise = random.uniform(-0.1, 0.1)
            feedback_reward = round(max(0.01, min(0.99, true_reward + noise)), 2)

        # Step Logic
        self.current_step += 1
        
        obs_to_return = None
        if self.mode == "simulation":
            if self.current_step >= len(task_data["emails"]):
                self.is_done = True
                obs_to_return = self._get_obs_last()
            else:
                obs_to_return = self._get_obs()
        else:
            # Dashboard / Infinite mode
            if self.current_step >= len(task_data["emails"]):
                self.current_step = 0
            obs_to_return = self._get_obs()
                
        return obs_to_return, Reward(value=feedback_reward), self.is_done, {
            "true_reward": true_reward,
            "streak": self.current_streak,
            "reason": email.get("reason", "N/A"),
            "correct_decision": email["correct_decision"],
            "correct_priority": email["correct_priority"]
        }

    def _get_obs_last(self) -> Observation:
        # Return the last email even if done to satisfy typed return
        task_data = TASKS[self.task_name]
        email = task_data["emails"][-1]
        return Observation(
            email_text=email["email_text"],
            sender=email["sender"],
            subject=email["subject"],
            step_count=self.current_step
        )

    def state(self) -> State:
        task_data = TASKS[self.task_name]
        return State(
            current_step=self.current_step,
            total_steps=len(task_data["emails"]),
            task_name=self.task_name,
            is_done=self.is_done,
            history=self.history
        )
