from django.contrib import admin

from .models import (
    Application,
    Decision,
    Disbursement,
    Document,
    InfoRequest,
    Offer,
    StatusEvent,
)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "number",
        "company_name",
        "product_id",
        "amount",
        "status",
        "scoring_unavailable",
        "created_at",
    ]
    list_filter = ["status", "product_id", "scoring_unavailable"]
    readonly_fields = [field.name for field in Application._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(StatusEvent, Decision, Offer, InfoRequest, Disbursement)
class AuditAdmin(admin.ModelAdmin):
    list_display = ["application", "record_type", "created_at"]

    @admin.display(description="Запись")
    def record_type(self, obj):
        return (
            getattr(obj, "verdict", None)
            or getattr(obj, "status", None)
            or getattr(obj, "actor_role", None)
            or "Демовыдача"
        )

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Document)
class DocumentAdmin(AuditAdmin):
    list_display = [
        "filename",
        "application",
        "kind",
        "size_bytes",
        "signed_at",
    ]
    exclude = ["content"]

    def get_readonly_fields(self, request, obj=None):
        return [
            field.name
            for field in self.model._meta.fields
            if field.name != "content"
        ]
