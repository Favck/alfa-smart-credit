from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ProductType(str, Enum):
    WORKING_CAPITAL = "working_capital"
    EQUIPMENT_PURCHASE = "equipment_purchase"
    INVESTMENT = "investment"
    OVERDRAFT = "overdraft"


class CompanyStatus(str, Enum):
    ACTIVE = "active"
    LIQUIDATING = "liquidating"
    LIQUIDATED = "liquidated"
    BANKRUPT = "bankrupt"


class RiskGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class RecommendationType(str, Enum):
    APPROVE = "approve"
    COUNTER = "counter"
    REJECT = "reject"


class PrePredictStatus(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    BLOCKED = "blocked"


class ProbabilityBucket(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    ZERO = "zero"


# --- Входной контракт (единый для /pre-predict и /evaluate) ---
class ScoringRequest(BaseModel):
    request_id: UUID = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    application_id: str = Field(..., example="APP-1042")
    product: ProductType = Field(..., example=ProductType.WORKING_CAPITAL)
    amount: int = Field(..., ge=50000, example=2000000)
    term_months: int = Field(..., ge=1, le=120, example=24)
    company_age_months: int = Field(..., ge=0, example=48)
    company_status: CompanyStatus = Field(..., example=CompanyStatus.ACTIVE)
    okved_group: str = Field(..., pattern=r"^[0-9]{2}$", example="10")
    monthly_revenue: int = Field(..., ge=0, example=1200000)
    current_monthly_payments: int = Field(default=0, ge=0, example=40000)
    bki_has_history: bool = Field(default=True, example=True)
    bki_overdue_count_12m: int = Field(default=0, ge=0, example=0)
    bki_max_overdue_days: int = Field(default=0, ge=0, example=0)
    bki_active_loans: int = Field(default=0, ge=0, example=1)


# --- Факторы Explainability (SHAP Waterfall) ---
class ScoreFactorReason(BaseModel):
    factor: str = Field(..., example="bki_history")
    impact: int = Field(..., example=60)
    text: str = Field(..., example="Положительная история в БКИ: нет текущих и исторических просрочек")


# --- Ответ Pre-Predictor ---
class PrePredictResponse(BaseModel):
    status: PrePredictStatus = Field(..., example=PrePredictStatus.GREEN)
    approval_probability_percent: int = Field(..., ge=0, le=100, example=85)
    estimated_monthly_payment: int = Field(..., example=105000)
    dti_forecast: float = Field(..., example=0.12)
    recommended_max_amount: Optional[int] = Field(None, example=2500000)
    recommended_min_term_months: Optional[int] = Field(None, example=24)
    hint_message: str = Field(..., example="Отличные параметры! При выручке 1.2 млн ₽ ежемесячный платеж 105 000 ₽ не перегружает бизнес.")
    latency_ms: float = Field(..., example=4.8)


# --- Ответ Full Scoring ---
class ScoringResponse(BaseModel):
    request_id: UUID
    model_version: str = Field(default="risk_scorecard_v1.0")
    stop_factors: List[str] = Field(default_factory=list)
    score: Optional[int] = Field(None, ge=300, le=850, example=670)
    pd: Optional[float] = Field(None, ge=0.0, le=1.0, example=0.035)
    approval_probability_percent: int = Field(..., ge=0, le=100, example=85)
    grade: Optional[RiskGrade] = Field(None, example=RiskGrade.A)
    reasons: List[ScoreFactorReason] = Field(..., min_length=5, max_length=5)
    max_affordable_amount: Optional[int] = Field(None, example=2400000)
    recommendation: RecommendationType = Field(..., example=RecommendationType.APPROVE)
    latency_ms: float = Field(..., example=18.4)



class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    algorithm: str
    features_count: int
    latency_p95_ms: float


class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime