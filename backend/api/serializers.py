from rest_framework import serializers as s

PRODUCT_CODES = ["working_capital", "equipment_purchase", "overdraft"]
DEMO_PROFILE_IDS = ["green", "yellow", "red", "underwriter"]
APPLICATION_STATUSES = [
    "DRAFT",
    "SUBMITTED",
    "CHECK",
    "ENRICH",
    "SCORING",
    "REVIEW",
    "APPROVED",
    "COUNTER_OFFER",
    "NEED_INFO",
    "REJECTED",
    "SIGNING",
    "DISBURSED",
    "CANCELLED",
]


class Error(s.Serializer):
    detail = s.CharField()


class PlannedError(Error):
    code = s.CharField(default="not_implemented")


class Health(s.Serializer):
    status = s.CharField()
    database = s.CharField()


class DemoProfile(s.Serializer):
    id = s.ChoiceField(choices=DEMO_PROFILE_IDS)
    name = s.CharField()
    role = s.ChoiceField(choices=["client", "bank"])
    company_id = s.CharField(allow_null=True)
    scenario = s.ChoiceField(
        choices=["green", "yellow", "red"], allow_null=True
    )
    description = s.CharField()


class DemoLogin(s.Serializer):
    profile_id = s.ChoiceField(choices=DEMO_PROFILE_IDS)


class CurrentUser(s.Serializer):
    id = s.IntegerField()
    name = s.CharField()
    role = s.ChoiceField(choices=["client", "bank"])
    profile_id = s.CharField()
    company_id = s.CharField(allow_null=True)


class LoginResult(s.Serializer):
    token = s.CharField(
        help_text=(
            "Заголовок последующих запросов: Authorization: " "Token <token>."
        )
    )
    user = CurrentUser()


class Company(s.Serializer):
    id = s.CharField()
    name = s.CharField()
    inn = s.CharField(
        help_text="Синтетический ИНН: 10 цифр для ООО, 12 для ИП."
    )
    ogrn = s.CharField(help_text="ОГРН либо ОГРНИП. Данные вымышлены.")
    legal_form = s.ChoiceField(choices=["company", "individual_entrepreneur"])
    okved = s.CharField()
    industry = s.CharField()
    status = s.ChoiceField(
        choices=["active", "liquidating", "liquidated", "bankrupt"]
    )
    registered_at = s.DateField()
    monthly_revenue = s.IntegerField(min_value=0)
    current_monthly_payments = s.IntegerField(min_value=0)


class Product(s.Serializer):
    id = s.ChoiceField(choices=PRODUCT_CODES)
    name = s.CharField()
    description = s.CharField()
    min_amount = s.IntegerField()
    max_amount = s.IntegerField()
    min_term_months = s.IntegerField()
    max_term_months = s.IntegerField()
    base_rate_percent = s.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Демонстрационная ставка, не актуальное предложение банка.",
    )
    is_demo_rate = s.BooleanField()


class NewsItem(s.Serializer):
    id = s.IntegerField()
    title = s.CharField()
    summary = s.CharField()
    category = s.ChoiceField(
        choices=["trade", "production", "construction", "finance"]
    )
    published_at = s.DateTimeField()


class NewsDetail(NewsItem):
    body = s.CharField()


class ApplicationWrite(s.Serializer):
    product_id = s.ChoiceField(choices=PRODUCT_CODES)
    amount = s.IntegerField(
        min_value=50000,
        help_text="Целые рубли. Дополнительно проверяется диапазон продукта.",
    )
    term_months = s.IntegerField(min_value=1, max_value=60)
    purpose = s.CharField(max_length=1000, required=False, allow_blank=True)
    monthly_revenue = s.IntegerField(min_value=0)
    current_monthly_payments = s.IntegerField(min_value=0)


class ApplicationPatch(s.Serializer):
    product_id = s.ChoiceField(choices=PRODUCT_CODES, required=False)
    amount = s.IntegerField(min_value=50000, required=False)
    term_months = s.IntegerField(min_value=1, max_value=60, required=False)
    purpose = s.CharField(max_length=1000, required=False, allow_blank=True)
    monthly_revenue = s.IntegerField(min_value=0, required=False)
    current_monthly_payments = s.IntegerField(min_value=0, required=False)


class Application(ApplicationWrite):
    id = s.UUIDField()
    number = s.CharField(
        help_text="Номер для показа клиенту, например APP-1042."
    )
    company_id = s.CharField()
    company_name = s.CharField()
    status = s.ChoiceField(choices=APPLICATION_STATUSES)
    status_label = s.CharField()
    next_action = s.ChoiceField(
        choices=[
            "wait",
            "edit",
            "provide_info",
            "accept_offer",
            "sign",
            "none",
        ]
    )
    created_at = s.DateTimeField()
    updated_at = s.DateTimeField()


class ApplicationPage(s.Serializer):
    count = s.IntegerField()
    next = s.URLField(allow_null=True)
    previous = s.URLField(allow_null=True)
    results = Application(many=True)


class StatusEvent(s.Serializer):
    id = s.IntegerField()
    from_status = s.ChoiceField(choices=APPLICATION_STATUSES, allow_null=True)
    to_status = s.ChoiceField(choices=APPLICATION_STATUSES)
    message = s.CharField(
        help_text="В клиентском API — только безопасное для клиента описание."
    )
    actor_role = s.ChoiceField(choices=["client", "bank", "system"])
    created_at = s.DateTimeField()


class ScoreReason(s.Serializer):
    factor = s.CharField()
    impact = s.IntegerField(help_text="Вклад в баллы. Не вероятность.")
    text = s.CharField()


class Scoring(s.Serializer):
    score = s.IntegerField(min_value=300, max_value=850, allow_null=True)
    pd = s.FloatField(min_value=0, max_value=1, allow_null=True)
    grade = s.ChoiceField(choices=["A", "B", "C", "D"], allow_null=True)
    reasons = ScoreReason(many=True)
    stop_factors = s.ListField(child=s.CharField())
    max_affordable_amount = s.IntegerField(allow_null=True)
    model_version = s.CharField(allow_null=True)
    scoring_unavailable = s.BooleanField()


class ClientScoring(s.Serializer):
    risk_label = s.CharField()
    explanation = s.CharField()
    reasons = s.ListField(
        child=s.CharField(),
        help_text=(
            "Клиенту — понятные причины без внутренних правил и" " порогов."
        ),
    )


class PrePredict(s.Serializer):
    status = s.ChoiceField(choices=["green", "yellow", "red", "blocked"])
    approval_probability_percent = s.IntegerField(
        min_value=0,
        max_value=100,
        help_text="Предварительная оценка, не гарантия решения и не 1-PD.",
    )
    estimated_monthly_payment = s.IntegerField(allow_null=True)
    dti_forecast = s.FloatField(min_value=0)
    recommended_max_amount = s.IntegerField(allow_null=True)
    recommended_min_term_months = s.IntegerField(allow_null=True)
    hint_message = s.CharField()


class Offer(s.Serializer):
    id = s.UUIDField()
    application_id = s.UUIDField()
    kind = s.ChoiceField(choices=["approved", "counter"])
    amount = s.IntegerField()
    term_months = s.IntegerField()
    annual_rate_percent = s.DecimalField(max_digits=5, decimal_places=2)
    monthly_payment = s.IntegerField(
        allow_null=True,
        help_text="Для овердрафта способ расчёта ещё не согласован.",
    )
    explanation = s.CharField()
    status = s.ChoiceField(choices=["pending", "accepted", "declined"])
    created_at = s.DateTimeField()


class Document(s.Serializer):
    id = s.UUIDField()
    application_id = s.UUIDField()
    kind = s.ChoiceField(choices=["statement", "additional", "contract"])
    filename = s.CharField()
    content_type = s.CharField()
    size_bytes = s.IntegerField()
    created_at = s.DateTimeField()


class DocumentUpload(s.Serializer):
    kind = s.ChoiceField(
        choices=["statement", "additional"], default="additional"
    )
    file = s.FileField(
        help_text=(
            "PDF/XLSX, до 10 МиБ; хранение для просмотра "
            "сотрудником, без OCR."
        )
    )


class Sign(s.Serializer):
    document_id = s.UUIDField()
    consent = s.BooleanField(
        help_text=(
            "Для имитации подписи должно быть true. Реальных "
            "юридических операций нет."
        )
    )


class InfoRequest(s.Serializer):
    id = s.UUIDField()
    message = s.CharField()
    requested_fields = s.ListField(child=s.CharField())
    document_required = s.BooleanField()
    status = s.ChoiceField(choices=["open", "answered"])
    created_at = s.DateTimeField()


class InfoResponse(s.Serializer):
    message = s.CharField(required=False, allow_blank=True)
    document_ids = s.ListField(child=s.UUIDField(), required=False)
    monthly_revenue = s.IntegerField(min_value=0, required=False)
    current_monthly_payments = s.IntegerField(min_value=0, required=False)


class Cancel(s.Serializer):
    reason = s.CharField(max_length=1000, required=False, allow_blank=True)


class Enrichment(s.Serializer):
    company_status = s.CharField()
    company_age_months = s.IntegerField()
    okved_group = s.CharField()
    bki_has_history = s.BooleanField()
    bki_overdue_count_12m = s.IntegerField()
    bki_max_overdue_days = s.IntegerField()
    bki_active_loans = s.IntegerField()
    source = s.CharField(
        help_text="В MVP — только локальные синтетические моки."
    )
    fetched_at = s.DateTimeField()


class BankApplication(Application):
    company = Company()
    scoring = Scoring(allow_null=True)
    enrichment = Enrichment(allow_null=True)


class DecisionWrite(s.Serializer):
    verdict = s.ChoiceField(
        choices=["approve", "counter", "need_info", "reject"]
    )
    reason = s.CharField(
        max_length=2000,
        help_text="Обоснование обязательно для любого ручного решения.",
    )
    amount = s.IntegerField(
        min_value=50000,
        required=False,
        help_text=(
            "Обязательно для counter; для approve — если " "меняются условия."
        ),
    )
    term_months = s.IntegerField(
        min_value=1,
        max_value=60,
        required=False,
        help_text="Обязательно для counter.",
    )
    annual_rate_percent = s.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        required=False,
        help_text="Обязательно для counter.",
    )
    requested_fields = s.ListField(
        child=s.CharField(),
        required=False,
        help_text="Для need_info — перечень полей для уточнения.",
    )
    document_required = s.BooleanField(
        required=False, help_text="Для need_info — требуется ли файл."
    )


class Decision(s.Serializer):
    id = s.UUIDField()
    application_id = s.UUIDField()
    verdict = s.ChoiceField(
        choices=["approve", "counter", "need_info", "reject"]
    )
    reason = s.CharField()
    actor_role = s.ChoiceField(choices=["bank", "system"])
    created_at = s.DateTimeField()
    application_status = s.ChoiceField(choices=APPLICATION_STATUSES)


class ValidApplicationWrite(ApplicationWrite):
    def validate(self, attrs):
        from .demo_data import PRODUCTS

        product = next(p for p in PRODUCTS if p["id"] == attrs["product_id"])
        errors = {}
        if (
            not product["min_amount"]
            <= attrs["amount"]
            <= product["max_amount"]
        ):
            errors["amount"] = "Сумма вне диапазона выбранного продукта."
        if (
            not product["min_term_months"]
            <= attrs["term_months"]
            <= product["max_term_months"]
        ):
            errors["term_months"] = "Срок вне диапазона выбранного продукта."
        for field in ["monthly_revenue", "current_monthly_payments"]:
            if attrs[field] > 10**12:
                errors[field] = "Значение не должно превышать 1 трлн рублей."
        if errors:
            raise s.ValidationError(errors)
        return attrs


class MLResult(Scoring):
    request_id = s.UUIDField()
    recommendation = s.ChoiceField(choices=["approve", "counter", "reject"])
    approval_probability_percent = s.IntegerField(min_value=0, max_value=100)
    scoring_unavailable = s.BooleanField(default=False)


class MLPreview(PrePredict):
    method_note = s.CharField(required=False)


class LiveApplication(Application):
    client_scoring = ClientScoring()
    current_offer = Offer(allow_null=True)
    info_request = InfoRequest(allow_null=True)
    disbursement = s.DictField(allow_null=True)


class LiveApplicationPage(ApplicationPage):
    results = LiveApplication(many=True)


class LiveBankApplication(LiveApplication):
    company = Company()
    scoring = MLResult(allow_null=True)
    enrichment = Enrichment(allow_null=True)
    scoring_unavailable = s.BooleanField()


class LiveBankApplicationPage(ApplicationPage):
    results = LiveBankApplication(many=True)


class ManualDecision(s.Serializer):
    verdict = s.ChoiceField(choices=["approve", "reject"])
    reason = s.CharField(max_length=2000, allow_blank=False)


class WorkflowDecision(DecisionWrite):
    annual_rate_percent = s.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
    )

    def validate(self, attrs):
        verdict = attrs["verdict"]
        if verdict == "counter":
            for key in ["amount", "term_months", "annual_rate_percent"]:
                if key not in attrs:
                    raise s.ValidationError(
                        {key: "Укажите встречные условия."}
                    )
        if verdict == "need_info":
            allowed = {"monthly_revenue", "current_monthly_payments"}
            if set(attrs.get("requested_fields", [])) - allowed:
                raise s.ValidationError(
                    {"requested_fields": "Неизвестное поле."}
                )
            if not attrs.get("requested_fields") and not attrs.get(
                "document_required"
            ):
                raise s.ValidationError("Укажите поля или запросите документ.")
        return attrs


class LiveDocument(Document):
    sha256 = s.CharField()
    signed_at = s.DateTimeField(allow_null=True)
