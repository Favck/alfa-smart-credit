"""Django adapter. The independently supplied ml/ code is not modified."""

import json
import logging
import uuid
from datetime import date
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from . import serializers as S
from .demo_data import PRODUCTS

logger = logging.getLogger(__name__)
METHOD_NOTE = (
    "ML использует упрощённую аннуитетную оценку со ставкой 22%. "
    "Процент модели равен 100 − PD и не является гарантией одобрения. "
    "Платёж ниже рассчитан Django по демонстрационной ставке продукта; "
    "для овердрафта фиксированный ежемесячный платёж не определён."
)


class MLUnavailable(Exception):
    pass


def product_for(code):
    return next(p for p in PRODUCTS if p["id"] == code)


def estimated_payment(values):
    if values["product_id"] == "overdraft":
        return None
    rate = float(product_for(values["product_id"])["base_rate_percent"]) / 1200
    return round(
        values["amount"] * rate / (1 - (1 + rate) ** -values["term_months"])
    )


def features(company, values, application_id):
    registered = date.fromisoformat(company["registered_at"])
    today = timezone.localdate()
    age = max(
        0,
        (today.year - registered.year) * 12
        + today.month
        - registered.month
        - (today.day < registered.day),
    )
    # Synthetic BKI fixtures cannot be overridden by the browser.
    bki = {
        "grain": (True, 0, 0, 1),
        "smirnov": (True, 2, 30, 3),
        "vector": (True, 3, 95, 2),
    }[company["id"]]
    return {
        "request_id": str(uuid.uuid4()),
        "application_id": str(application_id),
        "product": values["product_id"],
        "amount": values["amount"],
        "term_months": values["term_months"],
        "company_age_months": age,
        "company_status": company["status"],
        "okved_group": company["okved"][:2],
        "monthly_revenue": values["monthly_revenue"],
        "current_monthly_payments": values["current_monthly_payments"],
        "bki_has_history": bki[0],
        "bki_overdue_count_12m": bki[1],
        "bki_max_overdue_days": bki[2],
        "bki_active_loans": bki[3],
    }


def call_ml(operation, payload):
    request = Request(
        settings.ML_BASE_URL.rstrip("/") + "/api/v1/scoring/" + operation,
        data=json.dumps(payload, allow_nan=False).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.ML_TIMEOUT_SECONDS) as response:
            raw = response.read(524289)
        if len(raw) > 524288:
            raise ValueError("Oversized ML response")
        data = json.loads(
            raw,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("Non-finite ML response")
            ),
        )
        serializer = (
            S.MLPreview if operation == "pre-predict" else S.MLResult
        )(data=data)
        serializer.is_valid(raise_exception=True)
        result = serializer.validated_data
        if (
            operation == "evaluate"
            and str(result["request_id"]) != payload["request_id"]
        ):
            raise ValueError("ML request correlation failed")
        return json.loads(json.dumps(result, default=str, allow_nan=False))
    except (URLError, OSError, ValueError, TypeError, ValidationError) as exc:
        logger.warning("ML %s unavailable: %s", operation, type(exc).__name__)
        raise MLUnavailable() from exc


def preview(company, values):
    result = call_ml(
        "pre-predict",
        features(company, values, "preview-" + str(uuid.uuid4())),
    )
    product = product_for(values["product_id"])
    recommended = result.get("recommended_max_amount")
    if recommended is not None:
        result["recommended_max_amount"] = (
            min(recommended, product["max_amount"])
            if recommended >= product["min_amount"]
            else None
        )
    term = result.get("recommended_min_term_months")
    if term is not None:
        result["recommended_min_term_months"] = (
            max(product["min_term_months"], term)
            if term <= product["max_term_months"]
            else None
        )
    result["estimated_monthly_payment"] = estimated_payment(values)
    # Do not present the ML's fixed-rate payment/120-month suggestion as a
    # contractual product offer; the original hint remains internal to ML.
    result["hint_message"] = {
        "green": "Параметры выглядят подходящими для предварительной оценки.",
        "yellow": "Модель рекомендует проверить сумму и долговую нагрузку.",
        "red": "Модель оценивает риск как высокий. Рассмотрите меньшую сумму.",
        "blocked": "Есть ограничения по сведениям компании или БКИ.",
    }[result["status"]]
    result["method_note"] = METHOD_NOTE
    return result


def verdict(result, amount):
    if result["stop_factors"] or (
        result["score"] is not None and result["score"] < 520
    ):
        return "REJECTED", "Отказ по результатам оценки риска."
    limit = result.get("max_affordable_amount")
    if (
        result["score"] is not None
        and result["score"] >= 620
        and limit is not None
        and amount <= limit
    ):
        return "APPROVED", "Заявка одобрена по результатам оценки риска."
    return "REVIEW", "Заявка передана сотруднику банка для уточнения решения."


def client_result(application):
    if application.status == "CANCELLED":
        return {
            "risk_label": "Отменена",
            "explanation": "Заявка отменена клиентом.",
            "reasons": [],
        }
    decision = application.decisions.last()
    if application.scoring_unavailable:
        return {
            "risk_label": application.status_label,
            "explanation": (
                decision.reason
                if decision
                else "Оценка недоступна. Заявка сохранена для сотрудника."
            ),
            "reasons": [],
        }
    result = application.scoring
    if not result:
        return {
            "risk_label": application.status_label,
            "explanation": "Результат появится после отправки заявки.",
            "reasons": [],
        }
    stops = {
        "COMPANY_LIQUIDATION_STATUS": "Компания закрывается или закрыта.",
        "COMPANY_BANKRUPT": "В проверке есть сведения о банкротстве компании.",
        "BKI_CRITICAL_OVERDUE_90_PLUS": "В кредитной истории есть просрочка.",
        "BUSINESS_AGE_UNDER_3_MONTHS": "Недостаточный стаж бизнеса.",
    }
    reasons = [
        stops.get(code, "Обнаружено ограничение по результатам проверки.")
        for code in result["stop_factors"]
    ]
    if not reasons:
        reasons = [
            "Учтены выручка, кредитная нагрузка, стаж бизнеса и история БКИ."
        ]
    decision = application.decisions.last()
    explanation = decision.reason if decision else application.status_label
    return {
        "risk_label": application.status_label,
        "explanation": explanation,
        "reasons": reasons,
    }
