"""Response schemas for the risk API (Stage 7)."""
from pydantic import BaseModel


class SignalOut(BaseModel):
    key: str
    label: str
    group: str
    evaluated: bool
    triggered: bool
    weight: float
    value: float | str | bool | None = None
    threshold: float | str | bool | None = None
    explanation: str


class RiskAssessment(BaseModel):
    profile_id: int
    creator_name: str | None = None
    platform: str | None = None
    risk_score: float
    review_priority: str
    triggered_count: int
    not_evaluated: list[str]
    signals: list[SignalOut]
    method: str
    disclaimer: str


class QueueItem(BaseModel):
    profile_id: int
    creator_name: str | None = None
    platform: str | None = None
    risk_score: float
    review_priority: str
    signals_triggered: list[str]


class QueueResponse(BaseModel):
    items: list[QueueItem]
    total: int
    page: int
    pages: int
    page_size: int
    disclaimer: str


class SignalCount(BaseModel):
    key: str
    label: str
    count: int


class SummaryResponse(BaseModel):
    total: int
    review_priority: dict[str, int]
    signals: list[SignalCount]
    baselines: dict[str, dict[str, float]]
    config: dict[str, float]
    method: str
    disclaimer: str
