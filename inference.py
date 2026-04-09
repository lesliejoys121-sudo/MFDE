"""
inference.py
------------
AI-powered inference script for MFDE.
Uses Claude to triage emails — works with both simulation tasks and real Gmail.

Usage (simulation):
    python inference.py --task easy

Usage (Gmail):
    python inference.py --gmail --max-emails 10

Env vars:
    API_BASE_URL        — MFDE server URL (default: http://localhost:8000)
    ANTHROPIC_API_KEY   — required for Gmail mode
    MODEL_NAME          — Claude model (default: claude-sonnet-4-20250514)
"""

import os
import json
import time
import argparse
import requests
import openai

ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:8000")

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


def ai_triage(email_text: str, sender: str, subject: str) -> dict:
    """Strict evaluation proxy route explicitly following OpenEnv guidelines."""
    # Ensure they exist or gracefully default to standard openai variables locally
    api_base = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ.get("API_KEY", "dummy_key")
    
    client = openai.OpenAI(
        base_url=api_base,
        api_key=api_key
    )
    
    response = client.chat.completions.create(
        model=os.environ.get("MODEL_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM},
            {"role": "user", "content": f"From: {sender}\nSubject: {subject}\nBody: {email_text}"}
        ],
        max_tokens=200,
        temperature=0.0
    )
    
    clean = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def run_simulation(task: str = "easy"):
    """Run AI triage on a simulation task."""
    print(f"\n[START] MFDE AI Inference — task={task}")
    print(f"        Server: {ENV_BASE_URL}")

    # Reset
    try:
        res = requests.post(f"{ENV_BASE_URL}/reset", json={"task": task, "mode": "simulation"})
        res.raise_for_status()
        obs = res.json()
        print(f"[RESET] Subject: {obs['subject']} | From: {obs['sender']}\n")
    except Exception as e:
        print(f"[ERROR] Reset failed: {e}")
        return

    done = False
    step_count = 0
    total_reward = 0.0

    while not done and step_count < 15:
        step_count += 1

        # AI triage
        try:
            triage = ai_triage(obs["email_text"], obs["sender"], obs["subject"])
        except Exception as e:
            print(f"[STEP {step_count}] AI triage error: {e} — falling back to ignore/low")
            triage = {"decision": "ignore", "priority": "low", "reason": "Error fallback."}

        print(f"[STEP {step_count}] Subject : {obs['subject']}")
        print(f"           From    : {obs['sender']}")
        print(f"           AI      : {triage['decision'].upper()} / {triage['priority'].upper()}")
        print(f"           Reason  : {triage.get('reason', '')}")

        try:
            res = requests.post(f"{ENV_BASE_URL}/step", json={
                "decision": triage["decision"],
                "priority": triage["priority"]
            })
            res.raise_for_status()
            data = res.json()
            obs = data["observation"]
            reward = data["reward"]
            done = data["done"]
            info = data.get("info", {})
            total_reward += reward
            match = "✓" if reward >= 0.9 else ("~" if reward >= 0.2 else "✗")
            print(f"           Reward  : {reward:.2f} {match}  |  Correct: {info.get('correct_decision','?')}/{info.get('correct_priority','?')}")
            print(f"           Streak  : {info.get('streak', 0)}  |  Cumulative: {total_reward:.2f}\n")
        except Exception as e:
            print(f"[ERROR] Step failed: {e}")
            break

    print(f"[END] Steps: {step_count} | Total reward: {total_reward:.2f} | Score: {total_reward/max(step_count,1):.2f}/step\n")


def run_gmail_mode(max_emails: int = 10):
    """Fetch real Gmail and triage via the server's /api/gmail endpoints."""
    print(f"\n[START] MFDE Gmail Triage — fetching {max_emails} emails")
    print(f"        Server: {ENV_BASE_URL}\n")

    # 1. Fetch Gmail
    try:
        res = requests.post(f"{ENV_BASE_URL}/api/gmail/fetch", json={"max_emails": max_emails})
        res.raise_for_status()
        data = res.json()
        emails = data["emails"]
        print(f"[GMAIL] Loaded {data['count']} emails.\n")
    except Exception as e:
        print(f"[ERROR] Gmail fetch failed: {e}")
        return

    # 2. Triage all emails
    try:
        res = requests.post(f"{ENV_BASE_URL}/api/gmail/triage", json={"emails": emails})
        res.raise_for_status()
        data = res.json()
        results = data["results"]
        summary = data["summary"]
    except Exception as e:
        print(f"[ERROR] Gmail triage failed: {e}")
        return

    # 3. Print results
    print(f"{'#':<4} {'From':<28} {'Subject':<32} {'Decision':<10} {'Priority':<8} Reason")
    print("-" * 105)
    for r in results:
        print(
            f"{r['email_index']:<4} "
            f"{r['from_address'][:27]:<28} "
            f"{r['subject'][:31]:<32} "
            f"{r['decision']:<10} "
            f"{r['priority']:<8} "
            f"{r.get('reason','')[:35]}"
        )

    print(f"\n[SUMMARY]")
    print(f"  Total   : {summary['total']}")
    print(f"  Escalate: {summary['by_decision'].get('escalate', 0)}")
    print(f"  Reply   : {summary['by_decision'].get('reply', 0)}")
    print(f"  Ignore  : {summary['by_decision'].get('ignore', 0)}")
    print(f"\n[END] Gmail triage complete.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MFDE AI Inference Script")
    parser.add_argument("--task", type=str, default="easy", choices=["easy", "medium", "hard"],
                        help="Simulation task difficulty")
    parser.add_argument("--gmail", action="store_true", help="Triage real Gmail emails instead of simulation")
    parser.add_argument("--max-emails", type=int, default=10, help="Number of Gmail emails to fetch")
    parser.add_argument("--wait", type=int, default=2, help="Seconds to wait for server startup")
    args = parser.parse_args()

    time.sleep(args.wait)

    if args.gmail:
        run_gmail_mode(max_emails=args.max_emails)
    else:
        run_simulation(task=args.task)
