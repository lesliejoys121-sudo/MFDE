from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class Observation(BaseModel):
    email_text: str = Field(..., description="The content of the email")
    sender: str = Field(..., description="The sender of the email")
    subject: str = Field(..., description="The subject line of the email")
    step_count: int = Field(..., description="Current step in the episode", ge=0)

class Action(BaseModel):
    decision: Literal["reply", "ignore", "escalate"] = Field(..., description="Action to take")
    priority: Literal["low", "medium", "high"] = Field(..., description="Assigned priority level")
    email_id: Optional[int] = Field(None, description="Optional: Target index of the email in the current task")

class Reward(BaseModel):
    value: float = Field(..., ge=0.0)

class State(BaseModel):
    current_step: int
    total_steps: int
    task_name: str
    is_done: bool
    history: List[dict]

class ResetRequest(BaseModel):
    task: Literal["easy", "medium", "hard", "stress_test"] = "easy"
    mode: Literal["simulation", "infinite"] = "simulation"


# --- Gmail Integration Models ---

class GmailTriageRequest(BaseModel):
    emails: List[dict] = Field(..., description="List of emails with from, from_name, subject, snippet")

class GmailTriageResult(BaseModel):
    email_index: int
    from_address: str
    subject: str
    decision: Literal["reply", "ignore", "escalate"]
    priority: Literal["low", "medium", "high"]
    reason: str
    score: float

class GmailTriageResponse(BaseModel):
    results: List[GmailTriageResult]
    summary: dict
