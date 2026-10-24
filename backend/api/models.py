import uuid

from django.conf import settings
from django.db import models


class Application(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    company = models.JSONField()
    product_id = models.CharField(max_length=40)
    amount = models.PositiveBigIntegerField()
    term_months = models.PositiveSmallIntegerField()
    purpose = models.TextField(blank=True)
    monthly_revenue = models.PositiveBigIntegerField()
    current_monthly_payments = models.PositiveBigIntegerField()
    status = models.CharField(max_length=24, default="DRAFT", db_index=True)
    scoring = models.JSONField(null=True, blank=True)
    enrichment = models.JSONField(default=dict)
    scoring_unavailable = models.BooleanField(default=False)
    request_id = models.UUIDField(null=True, blank=True)
    submission_key = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "submission_key"],
                name="application_request_key",
            )
        ]

    @property
    def number(self):
        return f"APP-{str(self.id)[:8].upper()}"

    @property
    def company_id(self):
        return self.company["id"]

    @property
    def company_name(self):
        return self.company["name"]

    @property
    def status_label(self):
        return {
            "DRAFT": "Черновик",
            "SUBMITTED": "Заявка отправлена",
            "CHECK": "Проверка данных",
            "ENRICH": "Сбор сведений",
            "SCORING": "Оценка риска",
            "REVIEW": "Рассмотрение сотрудником",
            "APPROVED": "Одобрена",
            "REJECTED": "Отказ",
            "CANCELLED": "Отменена",
            "COUNTER_OFFER": "Предложены другие условия",
            "NEED_INFO": "Нужны дополнительные сведения",
            "SIGNING": "Ожидает подписания",
            "DISBURSED": "Финансирование выдано (демо)",
        }.get(self.status, self.status)

    @property
    def next_action(self):
        return {
            "DRAFT": "edit",
            "SCORING": "wait",
            "REVIEW": "wait",
            "NEED_INFO": "provide_info",
            "APPROVED": "accept_offer",
            "COUNTER_OFFER": "accept_offer",
            "SIGNING": "sign",
        }.get(self.status, "none")

    def __str__(self):
        return f"{self.number} — {self.company_name}"


class StatusEvent(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="events"
    )
    from_status = models.CharField(max_length=24, null=True)
    to_status = models.CharField(max_length=24)
    message = models.TextField()
    actor_role = models.CharField(max_length=12)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class Decision(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="decisions"
    )
    verdict = models.CharField(max_length=24)
    reason = models.TextField()
    actor_role = models.CharField(max_length=12)
    application_status = models.CharField(max_length=24)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class Offer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="offers"
    )
    kind = models.CharField(max_length=12)
    amount = models.PositiveBigIntegerField()
    term_months = models.PositiveSmallIntegerField()
    annual_rate_percent = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_payment = models.PositiveBigIntegerField(null=True)
    explanation = models.TextField()
    status = models.CharField(max_length=12, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["application"],
                condition=models.Q(status="pending"),
                name="one_pending_offer",
            )
        ]


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="documents"
    )
    offer = models.OneToOneField(
        Offer,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="contract",
    )
    kind = models.CharField(max_length=16)
    filename = models.CharField(max_length=150)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    content = models.BinaryField()
    sha256 = models.CharField(max_length=64)
    signed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class InfoRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application, on_delete=models.PROTECT, related_name="info_requests"
    )
    message = models.TextField()
    requested_fields = models.JSONField(default=list)
    document_required = models.BooleanField(default=False)
    status = models.CharField(max_length=12, default="open")
    response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application"],
                condition=models.Q(status="open"),
                name="one_open_info_request",
            )
        ]


class Disbursement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        Application, on_delete=models.PROTECT, related_name="disbursement"
    )
    offer = models.OneToOneField(Offer, on_delete=models.PROTECT)
    amount = models.PositiveBigIntegerField()
    account = models.CharField(max_length=50)
    reference = models.CharField(max_length=50, unique=True)
    simulated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
