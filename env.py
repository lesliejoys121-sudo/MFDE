import random
import numpy as np
from typing import Tuple, Dict, Any, List
from models import Observation, Action, Reward, State
from tasks import TASKS

class MFDEEnv:
    def __init__(self):
        self.task_name = "easy"
        self.mode = "simulation"
        self.total_score = 0.01
        self.cumulative_xp = 0.01
        self.session_score = 0.01
        self.is_done = False
        self.history = []
        self.current_step = 0
        self.current_streak = 0
        # Real Gmail emails loaded externally (list of dicts)
        self._gmail_emails: List[dict] = []
        self._using_gmail = False
        random.seed(42)
        np.random.seed(42)

    # ------------------------------------------------------------------ #
    #  Gmail Integration                                                   #
    # ------------------------------------------------------------------ #

    def load_gmail_emails(self, emails: List[dict]) -> int:
        """
        Load real Gmail emails into the environment as a custom task.
        Each email dict must have: from, from_name (optional), subject, snippet.
        Returns the number of emails loaded.
        """
        self._gmail_emails = [
            {
                "email_text": e.get("snippet", e.get("body", "")),
                "sender": e.get("from", "unknown@unknown.com"),
                "subject": e.get("subject", "(no subject)"),
                # Gmail emails have no ground-truth labels — use None
                "correct_decision": None,
                "correct_priority": None,
            }
            for e in emails
        ]
        self._using_gmail = True
        return len(self._gmail_emails)

    def _active_emails(self) -> List[dict]:
        if self._using_gmail and self._gmail_emails:
            return self._gmail_emails
        return TASKS[self.task_name]["emails"]

    # ------------------------------------------------------------------ #
    #  Standard OpenEnv API                                               #
    # ------------------------------------------------------------------ #

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

        emails = self._active_emails()
        if mode == "simulation" and not self._using_gmail:
            random.shuffle(TASKS[self.task_name]["emails"])

        return self._get_obs()

    def get_task_emails(self, task: str) -> list:
        if self._using_gmail:
            return self._gmail_emails
        if task not in TASKS:
            return []
        return TASKS[task]["emails"]

    def scan(self, text: str) -> dict:
        text_lower = text.lower()
        scam_keywords = [
            "urgent", "refund", "gift card", "ceo", "bitcoin",
            "password expire", "unauthorized", "bank account", "winner", "prize"
        ]
        matches = [kw for kw in scam_keywords if kw in text_lower]
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
        emails = self._active_emails()
        email = emails[self.current_step]
        return Observation(
            email_text=email["email_text"],
            sender=email["sender"],
            subject=email["subject"],
            step_count=self.current_step
        )

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        if self.is_done:
            raise RuntimeError("Episode is already finished. Call reset() first.")

        emails = self._active_emails()
        task_data = TASKS[self.task_name]

        if action.email_id is not None and 0 <= action.email_id < len(emails):
            self.current_step = action.email_id

        email = emails[self.current_step]

        # For Gmail emails with no ground truth, reward based on internal heuristic
        if email["correct_decision"] is None:
            scan_result = self.scan(email["email_text"])
            decision_match = (action.decision == scan_result["suggested_action"])
            priority_match = (action.priority == scan_result["suggested_priority"])
        else:
            decision_match = (action.decision == email["correct_decision"])
            priority_match = (action.priority == email["correct_priority"])

        base_reward = (0.6 if decision_match else 0.0) + (0.4 if priority_match else 0.0)

        if decision_match and priority_match:
            true_reward = 0.99
            self.current_streak += 1
        elif decision_match:
            true_reward = 0.3
            self.current_streak = 0
        else:
            true_reward = 0.01
            self.current_streak = 0

        self.cumulative_xp += true_reward
        self.session_score += true_reward

        average = self.cumulative_xp / (self.current_step + 1)
        self.total_score = round(max(0.01, min(0.99, average)), 4)

        self.history.append({
            "step": self.current_step,
            "observation": self._get_obs().model_dump(),
            "action": action.model_dump(),
            "true_reward": true_reward,
            "streak": self.current_streak,
            "correct_decision": email.get("correct_decision", "n/a"),
            "correct_priority": email.get("correct_priority", "n/a"),
            "reason": email.get("reason", "N/A")
        })

        feedback_reward = round(true_reward, 2)
        noise_prob = task_data.get("reward_noise_prob", 0.0) if not self._using_gmail else 0.0
        if random.random() < noise_prob:
            noise = random.uniform(-0.1, 0.1)
            feedback_reward = round(max(0.01, min(0.99, true_reward + noise)), 2)

        self.current_step += 1

        if self.current_step >= len(emails):
            self.is_done = True
            obs_to_return = self._get_obs_last()
        else:
            if self.mode != "simulation":
                self.current_step = self.current_step % len(emails)
            obs_to_return = self._get_obs() if not self.is_done else self._get_obs_last()

        return obs_to_return, Reward(value=feedback_reward), self.is_done, {
            "true_reward": true_reward,
            "streak": self.current_streak,
            "reason": email.get("reason", "N/A"),
            "correct_decision": email.get("correct_decision", "n/a"),
            "correct_priority": email.get("correct_priority", "n/a")
        }

    def _get_obs_last(self) -> Observation:
        emails = self._active_emails()
        email = emails[-1]
        return Observation(
            email_text=email["email_text"],
            sender=email["sender"],
            subject=email["subject"],
            step_count=self.current_step
        )

    def state(self) -> State:
        emails = self._active_emails()
        return State(
            current_step=self.current_step,
            total_steps=len(emails),
            task_name=self.task_name if not self._using_gmail else "gmail",
            is_done=self.is_done,
            history=self.history
        )
