"""
inference.py — MFDE Email Triage Inference Script
===================================================
Follows OpenEnv mandatory spec exactly.

STDOUT FORMAT:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

Env vars:
    API_BASE_URL   LLM proxy endpoint (injected by OpenEnv evaluator)
    MODEL_NAME     Model identifier for inference
    HF_TOKEN       Hugging Face / API key (also checks API_KEY as fallback)
    MFDE_SERVER_URL  Internal MFDE game server (default: http://127.0.0.1:7860)
"""

import os
import json
import time
import argparse
from typing import List, Optional

import requests
from openai import OpenAI

# ── LLM Proxy (injected by OpenEnv evaluator) ─────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or "dummy_key"
MODEL_NAME   = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

# ── Internal MFDE game server (separate from LLM proxy) ───────────────────────
MFDE_SERVER_URL = os.getenv("MFDE_SERVER_URL", "http://127.0.0.1:7860")

BENCHMARK  = "mfde-email-triage"
MAX_STEPS  = 15

# ── OpenAI client wired to the injected proxy ─────────────────────────────────
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

TRIAGE_SYSTEM = """You are an expert email security and triage AI.
Classify each email into one action and one priority level.

Actions:
- escalate: security threats, breaches, legal matters, production outages, fraud
- reply: legitimate requests needing a response, invoices, meetings, support tickets
- ignore: spam, promotions, newsletters, automated FYI notifications

Priority:
- high: act within the hour
- medium: act within the day
- low: no urgency

Respond ONLY with JSON, no markdown, no explanation:
{"decision":"reply|ignore|escalate","priority":"low|medium|high","reason":"one sentence"}"""


# ── Mandatory stdout log helpers ───────────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# ── LLM triage via proxy ───────────────────────────────────────────────────────
def ai_triage(email_text: str, sender: str, subject: str) -> dict:
    """Call the LLM via the OpenEnv injected proxy."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM},
            {"role": "user",   "content": f"From: {sender}\nSubject: {subject}\nBody: {email_text}"}
        ],
        max_tokens=200,
        temperature=0.0,
    )
    raw   = response.choices[0].message.content or ""
    clean = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


# ── Simulation run ─────────────────────────────────────────────────────────────
def run_simulation(task: str = "easy") -> None:
    rewards: List[float] = []
    steps_taken   = 0
    score         = 0.0
    success       = False

    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        try:
            res = requests.post(f"{MFDE_SERVER_URL}/reset",
                                json={"task": task, "mode": "simulation"},
                                timeout=30)
            res.raise_for_status()
            obs = res.json()
        except Exception as e:
            log_end(success=False, steps=0, score=0.0, rewards=[])
            return

        done = False

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            steps_taken = step
            error_msg   = None

            # LLM decides action
            try:
                triage = ai_triage(obs["email_text"], obs["sender"], obs["subject"])
                action_str = f"{triage['decision']}/{triage['priority']}"
            except Exception as e:
                error_msg  = str(e)
                triage     = {"decision": "ignore", "priority": "low", "reason": "Error fallback."}
                action_str = "ignore/low"

            # Submit action to environment
            reward = 0.0
            try:
                res = requests.post(f"{MFDE_SERVER_URL}/step",
                                    json={"decision": triage["decision"], "priority": triage["priority"]},
                                    timeout=30)
                res.raise_for_status()
                data   = res.json()
                obs    = data["observation"]
                reward = float(data["reward"])
                done   = bool(data["done"])
            except Exception as e:
                error_msg = str(e)
                done      = True

            rewards.append(reward)
            log_step(step=step, action=action_str, reward=reward, done=done, error=error_msg)

        score   = sum(rewards) / max(steps_taken, 1)
        score   = min(max(score, 0.0), 0.99)
        success = score >= 0.1

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MFDE AI Inference Script")
    parser.add_argument("--task", type=str, default="easy",
                        choices=["easy", "medium", "hard"],
                        help="Simulation task difficulty")
    parser.add_argument("--wait", type=int, default=2,
                        help="Seconds to wait for server startup")
    args = parser.parse_args()

    time.sleep(args.wait)
    run_simulation(task=args.task)
