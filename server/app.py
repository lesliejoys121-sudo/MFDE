from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse
from env import MFDEEnv
from models import Observation, Action, Reward, State, ResetRequest, GmailTriageRequest, GmailTriageResponse, GmailTriageResult
from grader import grade, grade_gmail
from pydantic import BaseModel
from typing import Optional
import os
import json
import requests

app = FastAPI(
    title="MFDE | Email Triage System",
    version="2.0",
    description="Misleading Feedback Decision Environment — now with real Gmail integration."
)
env = MFDEEnv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GMAIL_MCP_URL = os.environ.get("GMAIL_MCP_URL", "https://gmail.mcp.claude.com/mcp")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"

TRIAGE_SYSTEM = """You are an expert email security and triage AI.
Classify each email into one action and one priority level.

Actions:
- escalate: security threats, breaches, legal matters, production outages, fraud
- reply: legitimate requests needing a response, invoices, meetings, support
- ignore: spam, promotions, newsletters, automated FYI notifications

Priority:
- high: act within the hour
- medium: act within the day
- low: no urgency

Respond ONLY with JSON, no markdown:
{"decision":"reply|ignore|escalate","priority":"low|medium|high","reason":"one concise sentence"}"""


class ScanRequest(BaseModel):
    text: str

class GmailFetchRequest(BaseModel):
    max_emails: int = 10

# ------------------------------------------------------------------ #
#  OpenEnv Standard Endpoints                                          #
# ------------------------------------------------------------------ #

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/metadata")
def metadata():
    return {
        "name": "MFDE-Email-Triage",
        "description": "Misleading Feedback Decision Environment with Gmail integration.",
        "version": "2.0",
        "tags": ["openenv", "nlp", "classification", "uncertainty", "gmail"]
    }

@app.get("/schema")
def schema():
    return {
        "action": {
            "decision": {"type": "string", "options": ["reply", "ignore", "escalate"]},
            "priority": {"type": "string", "options": ["low", "medium", "high"]},
            "email_id": {"type": "integer", "optional": True}
        },
        "observation": {
            "email_text": {"type": "string"},
            "sender": {"type": "string"},
            "subject": {"type": "string"},
            "step_count": {"type": "integer"}
        }
    }

@app.post("/mcp")
def mcp(payload: Optional[dict] = Body(default=None)):
    return {
        "jsonrpc": "2.0",
        "result": {
            "name": "MFDE-Email-Triage",
            "capabilities": ["reset", "step", "state", "health", "metadata", "schema", "gmail/fetch", "gmail/triage"]
        },
        "id": (payload or {}).get("id", None)
    }

@app.post("/reset", response_model=Observation)
def reset(req: Optional[ResetRequest] = Body(default=None)):
    actual_req = req or ResetRequest()
    return env.reset(actual_req.task, actual_req.mode)

@app.post("/step")
def step(action: Action):
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs,
        "reward": round(reward.value, 2),
        "done": done,
        "info": info
    }

@app.get("/state", response_model=State)
def state():
    return env.state()

@app.get("/api/performance")
def get_performance():
    score = env.cumulative_xp
    streak = env.current_streak
    if score < 10.0: rank, next_goal = "Novice Analyst", 10.0
    elif score < 50.0: rank, next_goal = "Junior Triage", 50.0
    elif score < 150.0: rank, next_goal = "Senior Specialist", 150.0
    elif score < 500.0: rank, next_goal = "Master Triage Expert", 500.0
    else: rank, next_goal = "Grandmaster Phish-Hunter", 5000.0
    return {
        "total_score": round(score, 2),
        "current_streak": streak,
        "rank": rank,
        "progress_percent": min(100, (score / next_goal) * 100)
    }

@app.get("/api/inbox/{task}")
def get_inbox(task: str):
    emails = env.get_task_emails(task)
    if not emails:
        raise HTTPException(status_code=404, detail="Task not found")
    return [{"id": i, "sender": e["sender"], "subject": e["subject"], "body": e["email_text"]} for i, e in enumerate(emails)]

@app.post("/api/scan")
def scan_email(req: ScanRequest):
    return env.scan(req.text)

# ------------------------------------------------------------------ #
#  Gmail Integration Endpoints                                         #
# ------------------------------------------------------------------ #

@app.post("/api/gmail/fetch")
def gmail_fetch(req: GmailFetchRequest):
    """
    Fetch real Gmail emails via the Anthropic MCP.
    Requires ANTHROPIC_API_KEY and Gmail MCP access.
    Loads emails into the environment as the active email set.
    """
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not configured on the server.")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "mcp-client-2025-04-04",
    }

    payload = {
        "model": MODEL,
        "max_tokens": 1000,
        "mcp_servers": [{"type": "url", "url": GMAIL_MCP_URL, "name": "gmail-mcp"}],
        "messages": [{
            "role": "user",
            "content": (
                f"Use Gmail MCP to fetch the {req.max_emails} most recent inbox emails. "
                "Return ONLY a JSON array, no markdown. "
                "Each item: {\"from\": \"email\", \"from_name\": \"display name\", "
                "\"subject\": \"subject\", \"snippet\": \"first 200 chars of body\"}"
            )
        }]
    }

    try:
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        clean = text.replace("```json", "").replace("```", "").strip()
        emails = json.loads(clean)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gmail MCP fetch failed: {str(e)}")

    count = env.load_gmail_emails(emails)
    return {"status": "loaded", "count": count, "emails": emails}


@app.post("/api/gmail/triage")
def gmail_triage(req: GmailTriageRequest):
    """
    Triage a provided list of emails using Claude AI.
    Each email should have: from, from_name, subject, snippet.
    Returns triage decisions + a summary report.
    """
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not configured on the server.")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
    }

    results = []
    for i, email in enumerate(req.emails):
        payload = {
            "model": MODEL,
            "max_tokens": 200,
            "system": TRIAGE_SYSTEM,
            "messages": [{
                "role": "user",
                "content": (
                    f"From: {email.get('from_name', '')} <{email.get('from', '')}>\n"
                    f"Subject: {email.get('subject', '(no subject)')}\n"
                    f"Body: {email.get('snippet', '')}"
                )
            }]
        }
        try:
            resp = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            clean = text.replace("```json", "").replace("```", "").strip()
            triage = json.loads(clean)

            score_map = {"escalate+high": 0.99, "reply+medium": 0.99, "ignore+low": 0.99}
            score = 0.5  # default for unlabelled real email

            results.append(GmailTriageResult(
                email_index=i,
                from_address=email.get("from", ""),
                subject=email.get("subject", "(no subject)"),
                decision=triage.get("decision", "ignore"),
                priority=triage.get("priority", "low"),
                reason=triage.get("reason", ""),
                score=score
            ))
        except Exception as e:
            results.append(GmailTriageResult(
                email_index=i,
                from_address=email.get("from", ""),
                subject=email.get("subject", "(no subject)"),
                decision="ignore",
                priority="low",
                reason=f"Triage error: {str(e)}",
                score=0.01
            ))

    summary = grade_gmail([r.model_dump() for r in results])
    return GmailTriageResponse(results=results, summary=summary)


# ------------------------------------------------------------------ #
#  Dashboard UI                                                        #
# ------------------------------------------------------------------ #

@app.get("/", response_class=HTMLResponse)
def root():
    html_content = open("dashboard.html").read() if os.path.exists("dashboard.html") else """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>MFDE | Email Triage</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-950 text-gray-200 p-8 font-mono">
  <h1 class="text-2xl font-bold mb-4">MFDE Email Triage — v2.0</h1>
  <p class="text-gray-400 mb-6">API running. Visit <a href="/docs" class="text-blue-400">/docs</a> for Swagger UI.</p>
  <div class="grid grid-cols-3 gap-4 text-sm">
    <a href="/docs" class="bg-gray-800 p-4 rounded-lg hover:bg-gray-700">📖 Swagger Docs</a>
    <a href="/state" class="bg-gray-800 p-4 rounded-lg hover:bg-gray-700">📊 Current State</a>
    <a href="/api/performance" class="bg-gray-800 p-4 rounded-lg hover:bg-gray-700">🏆 Performance</a>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)
