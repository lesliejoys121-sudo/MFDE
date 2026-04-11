"""
gmail_triage.py
---------------
Standalone Gmail triage engine.
Fetches real emails via Gmail MCP and triages each with Claude AI.

Usage:
    python gmail_triage.py

Env vars required:
    ANTHROPIC_API_KEY   — your Anthropic API key
    GMAIL_MCP_URL       — Gmail MCP server URL (default: https://gmail.mcp.claude.com/mcp)
"""

import os
import json
import time
import requests
from grader import grade_gmail

HF_TOKEN = os.getenv("HF_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
GMAIL_MCP_URL = os.environ.get("GMAIL_MCP_URL", "https://gmail.mcp.claude.com/mcp")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {HF_TOKEN}"
}

TRIAGE_SYSTEM = """You are an expert email security and triage AI.
Your job is to classify each email into exactly one of three actions and one priority.

Actions:
- escalate: security threats, breaches, legal matters, production outages, fraud
- reply: legitimate requests needing a response, invoices, meeting requests, support tickets
- ignore: spam, promotions, newsletters, automated notifications, FYI-only emails

Priority:
- high: requires action within the hour
- medium: requires action within the day
- low: no urgency

Respond ONLY with a JSON object. No markdown, no explanation. Format:
{"decision":"reply|ignore|escalate","priority":"low|medium|high","reason":"one concise sentence"}"""


def fetch_gmail_emails(max_emails: int = 10) -> list:
    """Fetch recent emails from Gmail via MCP."""
    print(f"[GMAIL] Fetching {max_emails} emails via MCP...")

    payload = {
        "model": MODEL,
        "max_tokens": 1000,
        "mcp_servers": [{"type": "url", "url": GMAIL_MCP_URL, "name": "gmail-mcp"}],
        "messages": [{
            "role": "user",
            "content": (
                f"Use Gmail MCP to fetch the {max_emails} most recent inbox emails. "
                "Return ONLY a JSON array, no markdown, no explanation. "
                "Each item: {\"from\": \"email\", \"from_name\": \"display name or empty\", "
                "\"subject\": \"subject line\", \"snippet\": \"first 200 chars of body\"}"
            )
        }]
    }

    resp = requests.post(f"{API_BASE_URL}/chat/completions", headers=HEADERS, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    clean = text.replace("```json", "").replace("```", "").strip()
    emails = json.loads(clean)
    print(f"[GMAIL] Fetched {len(emails)} emails.")
    return emails


def triage_email(email: dict) -> dict:
    """Triage a single email using Claude."""
    payload = {
        "model": MODEL,
        "max_tokens": 200,
        "messages": [
            {"role": "system", "content": TRIAGE_SYSTEM},
            {"role": "user", "content": (
                f"From: {email.get('from_name', '')} <{email.get('from', '')}>\n"
                f"Subject: {email.get('subject', '(no subject)')}\n"
                f"Body: {email.get('snippet', '')}"
            )}
        ]
    }

    resp = requests.post(f"{API_BASE_URL}/chat/completions", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    clean = text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean)


def run_gmail_triage(max_emails: int = 10) -> list:
    """
    Full pipeline: fetch → triage → grade → print summary.
    Returns list of triage result dicts.
    """
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN (or ANTHROPIC_API_KEY) environment variable is not set.")

    emails = fetch_gmail_emails(max_emails)
    results = []

    print("\n[TRIAGE] Starting AI triage...\n")
    print(f"{'#':<4} {'From':<30} {'Subject':<35} {'Decision':<10} {'Priority':<8} Reason")
    print("-" * 110)

    for i, email in enumerate(emails):
        try:
            result = triage_email(email)
            result["email_index"] = i
            result["from_address"] = email.get("from", "")
            result["subject"] = email.get("subject", "(no subject)")
            results.append(result)

            print(
                f"{i:<4} "
                f"{email.get('from_name', email.get('from', ''))[:29]:<30} "
                f"{email.get('subject', '')[:34]:<35} "
                f"{result['decision']:<10} "
                f"{result['priority']:<8} "
                f"{result.get('reason', '')[:40]}"
            )
            time.sleep(0.3)  # mild rate limiting
        except Exception as e:
            print(f"{i:<4} ERROR: {e}")

    # Summary
    summary = grade_gmail(results)
    print("\n" + "=" * 110)
    print("[SUMMARY]")
    print(f"  Total emails   : {summary['total']}")
    print(f"  Escalate       : {summary['by_decision'].get('escalate', 0)}")
    print(f"  Reply          : {summary['by_decision'].get('reply', 0)}")
    print(f"  Ignore         : {summary['by_decision'].get('ignore', 0)}")
    print(f"  High priority  : {summary['by_priority'].get('high', 0)}")
    print(f"  Medium priority: {summary['by_priority'].get('medium', 0)}")
    print(f"  Low priority   : {summary['by_priority'].get('low', 0)}")
    print("=" * 110)

    return results


if __name__ == "__main__":
    run_gmail_triage(max_emails=10)
