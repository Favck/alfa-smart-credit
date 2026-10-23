import os
import math
from typing import List, Tuple
import lightgbm as lgb
import numpy as np

from app.schemas import (
    ScoringRequest,
    CompanyStatus,
    RiskGrade,
    RecommendationType,
    ScoreFactorReason,
    ProductType,
)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.txt")

FEATURE_NAMES = [
    "amount",
    "term_months",
    "company_age_months",
    "monthly_revenue",
    "current_monthly_payments",
    "dti",
    "leverage",
    "bki_has_history",
    "bki_overdue_count_12m",
    "bki_max_overdue_days",
    "bki_active_loans",
    "prod_working_capital",
    "prod_equipment",
    "prod_investment",
    "prod_overdraft",
]


class RiskEngine:
    _booster: lgb.Booster = None

    @classmethod
    def get_booster(cls) -> lgb.Booster:
        """Загрузка обученного бустинга (синглтон)."""
        if cls._booster is None:
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(
                    f"Файл модели {MODEL_PATH} не найден. Сначала выполните: python train.py"
                )
            cls._booster = lgb.Booster(model_file=MODEL_PATH)
        return cls._booster

    @staticmethod
    def calculate_annuity_payment(amount: int, term_months: int, annual_rate: float = 0.22) -> int:
        """Расчет аннуитетного платежа по рыночной ставке."""
        if term_months <= 0 or amount <= 0:
            return 0
        monthly_rate = annual_rate / 12.0
        coef = (monthly_rate * ((1 + monthly_rate) ** term_months)) / (((1 + monthly_rate) ** term_months) - 1)
        return int(round(amount * coef))

    @classmethod
    def check_stop_factors(cls, payload: ScoringRequest) -> List[str]:
        """Проверка стоп-правил перед вызовом ML-модели."""
        stops = []
        if payload.company_status in [CompanyStatus.LIQUIDATING, CompanyStatus.LIQUIDATED]:
            stops.append("COMPANY_LIQUIDATION_STATUS")
        if payload.company_status == CompanyStatus.BANKRUPT:
            stops.append("COMPANY_BANKRUPT")
        if payload.bki_max_overdue_days >= 90:
            stops.append("BKI_CRITICAL_OVERDUE_90_PLUS")
        if payload.company_age_months < 3:
            stops.append("BUSINESS_AGE_UNDER_3_MONTHS")
        return stops

    @classmethod
    def _extract_feature_vector(cls, payload: ScoringRequest, payment: int) -> np.ndarray:
        """Преобразование Pydantic-схемы в числовой вектор признаков."""
        revenue = max(payload.monthly_revenue, 1)
        dti = (payload.current_monthly_payments + payment) / revenue
        leverage = payload.amount / (revenue * 12)

        prod_wc = 1 if payload.product == ProductType.WORKING_CAPITAL else 0
        prod_eq = 1 if payload.product == ProductType.EQUIPMENT_PURCHASE else 0
        prod_inv = 1 if payload.product == ProductType.INVESTMENT else 0
        prod_od = 1 if payload.product == ProductType.OVERDRAFT else 0

        vec = np.array([
            payload.amount,
            payload.term_months,
            payload.company_age_months,
            payload.monthly_revenue,
            payload.current_monthly_payments,
            dti,
            leverage,
            1 if payload.bki_has_history else 0,
            payload.bki_overdue_count_12m,
            payload.bki_max_overdue_days,
            payload.bki_active_loans,
            prod_wc,
            prod_eq,
            prod_inv,
            prod_od,
        ], dtype=np.float64)

        return vec.reshape(1, -1)

    @staticmethod
    def _format_shap_reason(feature_name: str, shap_val: float, payload: ScoringRequest, payment: int) -> ScoreFactorReason:
        """Превращение сырого SHAP-вклада в понятный текст и балл влияния."""
        # В LightGBM положительный SHAP повышает log-odds дефолта (увеличивает риск).
        # Для скорингового балла наоборот: снижение риска — это плюс к баллу, рост риска — минус.
        score_impact = int(round(-shap_val * 45))

        if feature_name == "dti":
            dti_val = int(((payload.current_monthly_payments + payment) / max(payload.monthly_revenue, 1)) * 100)
            if score_impact > 0:
                text = f"Низкая долговая нагрузка (DTI {dti_val}%): выручка легко покрывает платежи"
            else:
                text = f"Высокая долговая нагрузка (DTI {dti_val}%): платеж давит на чистый денежный поток"

        elif feature_name in ["bki_max_overdue_days", "bki_overdue_count_12m", "bki_has_history"]:
            if payload.bki_max_overdue_days == 0 and payload.bki_overdue_count_12m == 0:
                text = "Идеальная кредитная история в БКИ без просрочек"
            else:
                text = f"Наличие просрочек в БКИ (макс. {payload.bki_max_overdue_days} дн.)"

        elif feature_name == "company_age_months":
            years = payload.company_age_months // 12
            if score_impact > 0:
                text = f"Устойчивый стаж бизнеса: компания на рынке более {years} лет"
            else:
                text = "Молодая компания: повышенный фактор неопределенности"

        elif feature_name in ["leverage", "amount"]:
            if score_impact > 0:
                text = "Запрошенная сумма соразмерна масштабу годового оборота компании"
            else:
                text = "Запрошенная сумма превышает комфортную долю годовой выручки"

        elif feature_name == "term_months":
            if payload.term_months <= 12:
                text = f"Короткий срок кредитования ({payload.term_months} мес.) снижает риск"
            else:
                text = f"Длинный горизонт кредитования ({payload.term_months} мес.) требует повышенной маржи риска"

        else:
            text = f"Влияние отраслевого профиля и типа кредитного продукта ({payload.product.value})"

        return ScoreFactorReason(factor=feature_name, impact=score_impact, text=text)

    @classmethod
    def compute_scoring_factors(
        cls, payload: ScoringRequest, payment: int
    ) -> Tuple[int, float, int, RiskGrade, List[ScoreFactorReason], int]:
        booster = cls.get_booster()
        X = cls._extract_feature_vector(payload, payment)

        # 1. Предсказание вероятности дефолта PD
        raw_pd = float(booster.predict(X)[0])
        pd = round(max(0.01, min(0.99, raw_pd)), 4)

        # 2. Инверсия в процент шанса одобрения
        prob_percent = int(round((1.0 - pd) * 100))
        prob_percent = max(0, min(100, prob_percent))

        # 3. Скоринговый балл (300–850)
        logit = math.log(pd / (1.0 - pd))
        score = int(round(600 - logit * 65))
        score = max(300, min(850, score))

        # 4. Вычисление точных SHAP-значений (TreeSHAP встроен в predict LightGBM)
        # Возвращает массив (1, n_features + 1), где последний элемент — bias
        shap_values = booster.predict(X, pred_contrib=True)[0][:-1]

        # 5. Сортировка по абсолютному влиянию и отбор строго ТОП-5
        top_indices = np.argsort(np.abs(shap_values))[::-1][:5]
        reasons: List[ScoreFactorReason] = [
            cls._format_shap_reason(FEATURE_NAMES[idx], float(shap_values[idx]), payload, payment)
            for idx in top_indices
        ]

        # 6. Определение грейда
        if score >= 680:
            grade = RiskGrade.A
        elif score >= 600:
            grade = RiskGrade.B
        elif score >= 520:
            grade = RiskGrade.C
        else:
            grade = RiskGrade.D

        # 7. Расчет посильного лимита
        free_cash = max(0, int(payload.monthly_revenue * 0.40 - payload.current_monthly_payments))
        if free_cash > 0:
            r = 0.22 / 12.0
            coef = (r * ((1 + r) ** payload.term_months)) / (((1 + r) ** payload.term_months) - 1)
            max_limit = int(free_cash / coef)
            max_limit = (max_limit // 50000) * 50000
        else:
            max_limit = 0

        return score, pd, prob_percent, grade, reasons, max_limit