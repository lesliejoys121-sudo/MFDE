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

HF_TOKEN = os.getenv("HF_TOKEN") or os.environ.get("ANTHROPIC_API_KEY", "")
GMAIL_MCP_URL = os.environ.get("GMAIL_MCP_URL", "https://gmail.mcp.claude.com/mcp")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

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
        "description": "Misleading Feedback Decision Environment: High-fidelity email triage with calibrated (0.02, 0.98) scoring. Evaluates AI agents on high-stakes decisions under noisy feedback.",
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
    try:
        # Auto-reset if the episode finished so clicking never hard-fails
        if env.is_done:
            env.reset(env.task_name if not env._using_gmail else "gmail", env.mode)
        obs, reward, done, info = env.step(action)
        return {
            "observation": obs,
            "reward": round(reward.value, 2),
            "done": done,
            "info": info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step error: {str(e)}")

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

@app.get("/api/analytics/extended")
def get_extended_analytics():
    history = env.history
    if not history:
        return {
            "action_distribution": {"reply": 0, "ignore": 0, "escalate": 0},
            "noise_impact": [],
            "calibration": 0.0,
            "consistency": 1.0,
            "deception_exposure": {}
        }

    decisions = [h["action"]["decision"] for h in history]
    actions_count = {d: decisions.count(d) for d in ["reply", "ignore", "escalate"]}
    
    # Calculate calibration: correlation between true_reward and feedback_reward (simplified)
    # Actually, let's track "Misleading Events"
    noise_events = [h for h in history if h.get("noise_applied", False)]
    impact = len(noise_events) / len(history) if history else 0
    
    # Consistency: streak-based metric
    consistency = env.current_streak / len(history) if history else 1.0
    
    # Deception exposure
    deceptions = [h.get("deception_type", "none") for h in history if h.get("deception_type", "none") != "none"]
    deception_counts = {d: deceptions.count(d) for d in set(deceptions)}

    return {
        "action_distribution": actions_count,
        "noise_impact_ratio": round(impact, 2),
        "calibration_score": round(1.0 - (sum(abs(h.get("true_reward", 0) - h.get("feedback_reward", h.get("true_reward", 0))) for h in history) / len(history)), 2),
        "consistency_rating": round(consistency, 2),
        "deception_exposure": deception_counts,
        "recent_logs": history[-10:] # For the "Agent Console"
    }


@app.get("/api/inbox/{task}")
def get_inbox(task: str):
    emails = env.get_task_emails(task)
    if emails is None:
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
    if not HF_TOKEN:
        raise HTTPException(status_code=500, detail="HF_TOKEN is not configured on the server.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HF_TOKEN}"
    }

    # Note: MCP fetching is still Anthropic-centric in some setups, 
    # but here we redirect the prompt to the HF-compatible router.

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
        resp = requests.post(f"{API_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        clean = text.replace("```json", "").replace("```", "").strip()
        emails = json.loads(clean)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gmail MCP fetch failed: {str(e)}")

    count = env.load_gmail_emails(emails)
    return {"status": "loaded", "count": count, "emails": emails}


@app.post("/api/gmail/triage")
def gmail_triage(req: GmailTriageRequest):
    if not HF_TOKEN:
        raise HTTPException(status_code=500, detail="HF_TOKEN is not configured on the server.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HF_TOKEN}"
    }

    results = []
    for i, email in enumerate(req.emails):
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
        try:
            resp = requests.post(f"{API_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            clean = text.replace("```json", "").replace("```", "").strip()
            triage = json.loads(clean)

            results.append(GmailTriageResult(
                email_index=i,
                from_address=email.get("from", ""),
                subject=email.get("subject", "(no subject)"),
                decision=triage.get("decision", "ignore"),
                priority=triage.get("priority", "low"),
                reason=triage.get("reason", ""),
                score=0.98 # Calibrated score for successful triage
            ))
        except Exception as e:
            results.append(GmailTriageResult(
                email_index=i,
                from_address=email.get("from", ""),
                subject=email.get("subject", "(no subject)"),
                decision="ignore",
                priority="low",
                reason=f"Triage error: {str(e)}",
                score=0.02
            ))

    summary = grade_gmail([r.model_dump() for r in results])
    return GmailTriageResponse(results=results, summary=summary)


@app.get("/", response_class=HTMLResponse)
def root():
    # Load separate dashboard.html for cleaner code
    if os.path.exists("dashboard.html"):
        with open("dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    
    # Fallback to a basic message if dashboard.html is missing
    return HTMLResponse(content="<h1>MFDE v2.0 API is running</h1><p>dashboard.html not found.</p>")

def main():
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()