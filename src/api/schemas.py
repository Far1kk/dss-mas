from typing import Optional, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=128)
    llm_provider: str = Field("gigachat")


class FeedbackRequest(BaseModel):
    session_id: str
    rating: Literal["like", "dislike"]
    comment: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
