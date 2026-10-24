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
        }.get(self.status, self.status)

    @property
    def next_action(self):
        return (
            "edit"
            if self.status == "DRAFT"
            else ("wait" if self.status in {"SCORING", "REVIEW"} else "none")
        )

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
