import time
from datetime import datetime, timezone
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.schemas import (
    ScoringRequest,
    ScoringResponse,
    PrePredictResponse,
    PrePredictStatus,
    RecommendationType,
    ModelInfoResponse,
    HealthResponse,
    ScoreFactorReason,
)
from app.model import RiskEngine

app = FastAPI(
    title="ML Scoring & Pre-Predict Engine API",
    version="1.3.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    details = [{"field": str(err["loc"][-1]), "message": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation Error", "details": details},
    )


@app.post(
    "/api/v1/scoring/pre-predict",
    response_model=PrePredictResponse,
    tags=["Pre-Predictor"],
    summary="Экспресс-прогноз шансов на одобрение",
)
async def pre_predict(payload: ScoringRequest):
    t_start = time.perf_counter()

    payment = RiskEngine.calculate_annuity_payment(payload.amount, payload.term_months)
    stops = RiskEngine.check_stop_factors(payload)

    total_outflow = payload.current_monthly_payments + payment
    dti = round(total_outflow / payload.monthly_revenue if payload.monthly_revenue > 0 else 1.5, 2)

    if stops:
        latency = round((time.perf_counter() - t_start) * 1000, 2)
        return PrePredictResponse(
            status=PrePredictStatus.BLOCKED,
            approval_probability_percent=0,
            estimated_monthly_payment=payment,
            dti_forecast=dti,
            recommended_max_amount=0,
            recommended_min_term_months=None,
            hint_message="Обнаружены стоп-факторы: заемщик не соответствует базовым требованиям кредитования.",
            latency_ms=latency,
        )

    score, pd, prob_pct, grade, reasons, max_limit = RiskEngine.compute_scoring_factors(payload, payment)

    if prob_pct >= 70:
        pred_status = PrePredictStatus.GREEN
        hint = f"Отличные шансы ({prob_pct}%)! Платеж {payment:,.0f} ₽ комфортен для бизнеса.".replace(",", " ")
    elif prob_pct >= 40:
        pred_status = PrePredictStatus.YELLOW
        rec_sum = min(payload.amount, max_limit) if max_limit > 0 else payload.amount
        hint = f"Шанс {prob_pct}%. Рекомендуем снизить сумму до {rec_sum:,.0f} ₽ или увеличить срок для снижения платежа.".replace(",", " ")
    else:
        pred_status = PrePredictStatus.RED
        hint = f"Высокий риск отказа (шанс {prob_pct}%). Текущая нагрузка превышает финансовые возможности компании."

    latency = round((time.perf_counter() - t_start) * 1000, 2)
    return PrePredictResponse(
        status=pred_status,
        approval_probability_percent=prob_pct,
        estimated_monthly_payment=payment,
        dti_forecast=dti,
        recommended_max_amount=max_limit if max_limit > 0 else None,
        recommended_min_term_months=min(120, payload.term_months + 12) if pred_status != PrePredictStatus.GREEN else None,
        hint_message=hint,
        latency_ms=latency,
    )


@app.post(
    "/api/v1/scoring/evaluate",
    response_model=ScoringResponse,
    tags=["Full Scoring"],
    summary="Полная оценка кредитного риска",
)
async def evaluate(payload: ScoringRequest):
    t_start = time.perf_counter()

    stops = RiskEngine.check_stop_factors(payload)
    payment = RiskEngine.calculate_annuity_payment(payload.amount, payload.term_months)

    if stops:
        latency = round((time.perf_counter() - t_start) * 1000, 2)
        default_reasons = [
            ScoreFactorReason(factor=f"stop_{i+1}", impact=-100, text=f"Критический стоп-фактор: {s}")
            for i, s in enumerate(stops[:5])
        ]
        while len(default_reasons) < 5:
            default_reasons.append(
                ScoreFactorReason(factor=f"extra_stop_{len(default_reasons)+1}", impact=0, text="Ограничение кредитной политики")
            )

        return ScoringResponse(
            request_id=payload.request_id,
            model_version="risk_scorecard_v1.0",
            stop_factors=stops,
            score=None,
            pd=1.0,
            approval_probability_percent=0,
            grade=None,
            reasons=default_reasons,
            max_affordable_amount=0,
            recommendation=RecommendationType.REJECT,
            latency_ms=latency,
        )

    score, pd, prob_pct, grade, reasons, max_limit = RiskEngine.compute_scoring_factors(payload, payment)

    if score >= 620:
        recommendation = RecommendationType.APPROVE
    elif score >= 520:
        recommendation = RecommendationType.COUNTER
    else:
        recommendation = RecommendationType.REJECT

    latency = round((time.perf_counter() - t_start) * 1000, 2)
    return ScoringResponse(
        request_id=payload.request_id,
        model_version="risk_scorecard_v1.0",
        stop_factors=[],
        score=score,
        pd=pd,
        approval_probability_percent=prob_pct,
        grade=grade,
        reasons=reasons,
        max_affordable_amount=max_limit,
        recommendation=recommendation,
        latency_ms=latency,
    )


@app.get("/api/v1/model", response_model=ModelInfoResponse, tags=["Audit & System"])
async def get_model_info():
    return ModelInfoResponse(
        model_name="alfa_mmb_risk_engine",
        model_version="1.0.0",
        algorithm="LogisticRegression Scorecard + SHAP Explainability",
        features_count=14,
        latency_p95_ms=22.5,
    )


@app.get("/api/v1/health", response_model=HealthResponse, tags=["Audit & System"])
async def health():
    return HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))