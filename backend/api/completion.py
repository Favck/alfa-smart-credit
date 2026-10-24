import hashlib
import uuid
import zipfile
from decimal import Decimal
from io import BytesIO

from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from django.utils.text import get_valid_filename
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from . import scoring
from . import serializers as S
from .contracts import contract_pdf
from .models import (
    Application,
    Decision,
    Disbursement,
    Document,
    InfoRequest,
    Offer,
)
from .permissions import get_profile
from .pipeline import BankAPI, ClientAPI, application_for, record, serialize


def conflict(message="Действие недоступно в текущем статусе."):
    return Response({"detail": message}, status=409)


def offer_terms(application, values=None):
    values = values or {}
    product = scoring.product_for(application.product_id)
    amount = values.get("amount", application.amount)
    term = values.get("term_months", application.term_months)
    if not product["min_amount"] <= amount <= product["max_amount"]:
        raise ValidationError({"amount": "Сумма вне диапазона продукта."})
    if not product["min_term_months"] <= term <= product["max_term_months"]:
        raise ValidationError({"term_months": "Срок вне диапазона продукта."})
    rate = Decimal(
        str(values.get("annual_rate_percent", product["base_rate_percent"]))
    )
    monthly = None
    if application.product_id != "overdraft":
        r = float(rate) / 1200
        monthly = round(
            amount / term if r == 0 else amount * r / (1 - (1 + r) ** -term)
        )
    return dict(
        amount=amount,
        term_months=term,
        annual_rate_percent=rate,
        monthly_payment=monthly,
    )


def issue_offer(application, reason, values=None, kind="approved"):
    terms = offer_terms(application, values)
    application.offers.filter(status="pending").update(status="declined")
    return Offer.objects.create(
        application=application, kind=kind, explanation=reason, **terms
    )


def bank_decision(request, application):
    serializer = S.WorkflowDecision(data=request.data)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    verdict = values["verdict"]
    status = {
        "approve": "APPROVED",
        "counter": "COUNTER_OFFER",
        "need_info": "NEED_INFO",
        "reject": "REJECTED",
    }[verdict]
    if verdict in {"approve", "counter"}:
        offer_terms(application, values)
    with transaction.atomic():
        if not Application.objects.filter(
            pk=application.pk,
            status="REVIEW",
            updated_at=application.updated_at,
        ).update(status=status, updated_at=timezone.now()):
            return conflict("Решение доступно только при ручном рассмотрении.")
        decision = Decision.objects.create(
            application=application,
            verdict=verdict,
            reason=values["reason"],
            actor_role="bank",
            application_status=status,
        )
        if verdict in {"approve", "counter"}:
            issue_offer(
                application,
                values["reason"],
                values,
                "counter" if verdict == "counter" else "approved",
            )
        elif verdict == "need_info":
            InfoRequest.objects.create(
                application=application,
                message=values["reason"],
                requested_fields=values.get("requested_fields", []),
                document_required=values.get("document_required", False),
            )
        record(application, "REVIEW", status, values["reason"], "bank")
    return Response(S.Decision(decision).data, status=201)


class OfferView(ClientAPI):
    @extend_schema(
        tags=["Офферы"],
        responses={200: S.Offer, 404: S.Error},
        summary="Текущее предложение банка",
    )
    def get(self, request, application_id):
        application = application_for(request, application_id)
        offer = application.offers.exclude(status="declined").first()
        if not offer:
            raise NotFound("Предложение пока не подготовлено.")
        return Response(S.Offer(offer).data)


class AcceptOfferView(ClientAPI):
    @extend_schema(
        tags=["Офферы"],
        request=None,
        responses={200: S.LiveApplication, 409: S.Error},
        summary="Принять предложение и подготовить PDF-договор",
    )
    def post(self, request, application_id, offer_id):
        application = application_for(request, application_id)
        offer = application.offers.filter(pk=offer_id).first()
        if not offer:
            raise NotFound("Предложение не найдено.")
        with transaction.atomic():
            if offer.status == "accepted" and application.status in {
                "SIGNING",
                "DISBURSED",
            }:
                return Response(serialize(application))
            if offer.status != "pending":
                return conflict("Это предложение больше не актуально.")
            previous = application.status
            if not Application.objects.filter(
                pk=application.pk,
                status__in=["APPROVED", "COUNTER_OFFER"],
                status=previous,
            ).update(status="SIGNING", updated_at=timezone.now()):
                return conflict()
            offer.status = "accepted"
            offer.save(update_fields=["status"])
            content = contract_pdf(application, offer)
            Document.objects.create(
                application=application,
                offer=offer,
                kind="contract",
                filename=f"demo-contract-{application.number}.pdf",
                content_type="application/pdf",
                size_bytes=len(content),
                content=content,
                sha256=hashlib.sha256(content).hexdigest(),
            )
            record(
                application,
                previous,
                "SIGNING",
                "Условия приняты. Подготовлен демонстрационный договор.",
                "client",
            )
        application.refresh_from_db()
        return Response(serialize(application))


class DeclineOfferView(ClientAPI):
    @extend_schema(
        tags=["Офферы"],
        request=S.Cancel,
        responses={200: S.LiveApplication, 409: S.Error},
        summary="Отклонить предложение и отменить заявку",
    )
    def post(self, request, application_id, offer_id):
        application = application_for(request, application_id)
        offer = application.offers.filter(pk=offer_id).first()
        if not offer:
            raise NotFound("Предложение не найдено.")
        reason = S.Cancel(data=request.data)
        reason.is_valid(raise_exception=True)
        with transaction.atomic():
            if (
                application.status == "CANCELLED"
                and offer.status == "declined"
            ):
                return Response(serialize(application))
            previous = application.status
            if offer.status != "pending" or not Application.objects.filter(
                pk=application.pk,
                status__in=["APPROVED", "COUNTER_OFFER"],
                status=previous,
            ).update(status="CANCELLED", updated_at=timezone.now()):
                return conflict()
            offer.status = "declined"
            offer.save(update_fields=["status"])
            record(
                application,
                previous,
                "CANCELLED",
                reason.validated_data.get("reason")
                or "Клиент отказался от предложения.",
                "client",
            )
        application.refresh_from_db()
        return Response(serialize(application))


def validated_upload(upload):
    if upload.size > 10 * 1024 * 1024:
        raise ValidationError({"file": "Максимальный размер — 10 МиБ."})
    filename = get_valid_filename(
        upload.name.replace("\\", "/").split("/")[-1]
    )[-140:]
    content = upload.read(10 * 1024 * 1024 + 1)
    if len(content) != upload.size:
        raise ValidationError({"file": "Некорректный размер файла."})
    ext = filename.rsplit(".", 1)[-1].lower()
    if (
        ext == "pdf"
        and content.startswith(b"%PDF-")
        and b"%%EOF" in content[-2048:]
    ):
        return filename, "application/pdf", content
    if ext == "xlsx":
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                members = archive.infolist()
                names = {item.filename for item in members}
                if (
                    len(members) > 5000
                    or sum(item.file_size for item in members)
                    > 40 * 1024 * 1024
                ):
                    raise ValueError("Archive size")
                if not {"[Content_Types].xml", "xl/workbook.xml"} <= names:
                    raise ValueError("Workbook structure")
                if any(
                    "vba" in name.lower() or name.lower().endswith(".bin")
                    for name in names
                ):
                    raise ValueError("Macros")
            return (
                filename,
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet",
                content,
            )
        except (zipfile.BadZipFile, ValueError):
            pass
    raise ValidationError({"file": "Допускаются PDF и XLSX без макросов."})


class DocumentsView(ClientAPI):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Документы"],
        responses=S.LiveDocument(many=True),
        summary="Документы своей заявки",
    )
    def get(self, request, application_id):
        return Response(
            S.LiveDocument(
                application_for(request, application_id)
                .documents.all()
                .defer("content"),
                many=True,
            ).data
        )

    @extend_schema(
        tags=["Документы"],
        request={"multipart/form-data": S.DocumentUpload},
        responses={201: S.LiveDocument, 409: S.Error},
        summary="Загрузить PDF или XLSX в черновик или ответ на дозапрос",
    )
    def post(self, request, application_id):
        application = application_for(request, application_id)
        values = S.DocumentUpload(data=request.data)
        values.is_valid(raise_exception=True)
        filename, content_type, content = validated_upload(
            values.validated_data["file"]
        )
        with transaction.atomic():
            # Acquire a write claim before checking count to serialize uploads.
            if not Application.objects.filter(
                pk=application.pk, status__in=["DRAFT", "NEED_INFO"]
            ).update(updated_at=timezone.now()):
                return conflict(
                    "Загрузка доступна в черновике или по запросу банка."
                )
            if application.documents.exclude(kind="contract").count() >= 6:
                raise ValidationError(
                    "К заявке можно приложить не более 6 файлов."
                )
            document = Document.objects.create(
                application=application,
                kind=values.validated_data["kind"],
                filename=filename,
                content_type=content_type,
                content=content,
                size_bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
            )
        return Response(S.LiveDocument(document).data, status=201)


class BankDocumentsView(BankAPI):
    @extend_schema(
        tags=["Банк"],
        responses=S.LiveDocument(many=True),
        summary="Документы заявки для сотрудника банка",
    )
    def get(self, request, application_id):
        return Response(
            S.LiveDocument(
                application_for(request, application_id, True)
                .documents.all()
                .defer("content"),
                many=True,
            ).data
        )


class DocumentDownloadView(ClientAPI):
    # Check both roles against the actual application.
    permission_classes = BankAPI.permission_classes[:1]

    @extend_schema(
        tags=["Документы"],
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
        summary="Защищённое скачивание документа",
    )
    def get(self, request, application_id, document_id):
        profile = get_profile(request.user)
        if not profile:
            raise NotFound("Документ не найден.")
        application = application_for(
            request, application_id, profile["role"] == "bank"
        )
        document = application.documents.filter(pk=document_id).first()
        if not document:
            raise NotFound("Документ не найден.")
        response = FileResponse(
            BytesIO(bytes(document.content)),
            as_attachment=True,
            filename=document.filename,
            content_type=document.content_type,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "sandbox"
        return response


class SignView(ClientAPI):
    @extend_schema(
        tags=["Документы"],
        request=S.Sign,
        responses={200: S.LiveApplication, 409: S.Error},
        summary="Демонстрационное подписание и имитация выдачи",
    )
    def post(self, request, application_id):
        application = application_for(request, application_id)
        values = S.Sign(data=request.data)
        values.is_valid(raise_exception=True)
        if not values.validated_data["consent"]:
            raise ValidationError(
                {
                    "consent": (
                        "Подтвердите согласие с демонстрационными условиями."
                    )
                }
            )
        document = (
            application.documents.filter(
                pk=values.validated_data["document_id"],
                kind="contract",
                offer__status="accepted",
            )
            .select_related("offer")
            .first()
        )
        if not document:
            raise NotFound("Актуальный договор не найден.")
        with transaction.atomic():
            if application.status == "DISBURSED" and document.signed_at:
                return Response(serialize(application))
            now = timezone.now()
            if not Application.objects.filter(
                pk=application.pk, status="SIGNING"
            ).update(status="DISBURSED", updated_at=now):
                return conflict()
            content = contract_pdf(application, document.offer, now)
            document.content, document.size_bytes = content, len(content)
            document.sha256, document.signed_at = (
                hashlib.sha256(content).hexdigest(),
                now,
            )
            document.save(
                update_fields=["content", "size_bytes", "sha256", "signed_at"]
            )
            Disbursement.objects.create(
                application=application,
                offer=document.offer,
                amount=document.offer.amount,
                account="DEMO-" + application.company_id.upper(),
                reference="DEMO-" + str(uuid.uuid4())[:12].upper(),
            )
            record(
                application,
                "SIGNING",
                "DISBURSED",
                "Демо-договор подписан. Выдача смоделирована, "
                "реальные деньги не переводились.",
                "client",
            )
        application.refresh_from_db()
        return Response(serialize(application))


class InfoRequestView(ClientAPI):
    @extend_schema(
        tags=["Заявки"],
        responses={200: S.InfoRequest, 404: S.Error},
        summary="Текущий дозапрос банка",
    )
    def get(self, request, application_id):
        item = (
            application_for(request, application_id)
            .info_requests.filter(status="open")
            .first()
        )
        if not item:
            raise NotFound("Открытого запроса нет.")
        return Response(S.InfoRequest(item).data)


class InfoResponseView(ClientAPI):
    @extend_schema(
        tags=["Заявки"],
        request=S.InfoResponse,
        responses={200: S.LiveApplication, 409: S.Error},
        summary="Ответить на запрос и вернуть заявку на рассмотрение",
    )
    def post(self, request, application_id, info_request_id):
        application = application_for(request, application_id)
        info = application.info_requests.filter(pk=info_request_id).first()
        if not info:
            raise NotFound("Запрос не найден.")
        values = S.InfoResponse(data=request.data)
        values.is_valid(raise_exception=True)
        data = values.validated_data
        for key in info.requested_fields:
            if key not in data:
                raise ValidationError({key: "Укажите запрошенное значение."})
        ids = data.get("document_ids", [])
        if info.document_required and not ids:
            raise ValidationError(
                {"document_ids": "Приложите запрошенный документ."}
            )
        if application.documents.exclude(kind="contract").filter(
            id__in=ids
        ).count() != len(set(ids)):
            raise ValidationError(
                {"document_ids": "Документ не принадлежит заявке."}
            )
        changes = {
            key: data[key]
            for key in ["monthly_revenue", "current_monthly_payments"]
            if key in data
        }
        full = {
            key: getattr(application, key)
            for key in S.ApplicationWrite().fields
        }
        full.update(changes)
        checked = S.ValidApplicationWrite(data=full)
        checked.is_valid(raise_exception=True)
        changed_finance = any(
            getattr(application, key) != value
            for key, value in changes.items()
        )
        payload = scoring.features(application.company, full, application.id)
        with transaction.atomic():
            if info.status != "open" or not Application.objects.filter(
                pk=application.pk,
                status="NEED_INFO",
                updated_at=application.updated_at,
            ).update(
                status="SCORING" if changed_finance else "REVIEW",
                request_id=(
                    payload["request_id"]
                    if changed_finance
                    else application.request_id
                ),
                updated_at=timezone.now(),
                **changes,
            ):
                return conflict()
            info.status, info.answered_at = "answered", timezone.now()
            info.response = {**data, "document_ids": [str(i) for i in ids]}
            info.save(update_fields=["status", "answered_at", "response"])
            if changed_finance:
                record(
                    application,
                    "NEED_INFO",
                    "ENRICH",
                    "Клиент уточнил финансовые показатели.",
                    "client",
                )
                record(
                    application,
                    "ENRICH",
                    "SCORING",
                    "Запущена повторная оценка с сохранением контекста.",
                )
            else:
                record(
                    application,
                    "NEED_INFO",
                    "REVIEW",
                    "Клиент ответил на запрос. Заявка возвращена сотруднику.",
                    "client",
                )
        if changed_finance:
            try:
                result = scoring.call_ml("evaluate", payload)
                unavailable = False
            except scoring.MLUnavailable:
                result, unavailable = None, True
            with transaction.atomic():
                if Application.objects.filter(
                    pk=application.pk,
                    status="SCORING",
                    request_id=payload["request_id"],
                ).update(
                    status="REVIEW",
                    scoring=result,
                    scoring_unavailable=unavailable,
                    updated_at=timezone.now(),
                ):
                    record(
                        application,
                        "SCORING",
                        "REVIEW",
                        "Ответ клиента сохранён. Решение принимает "
                        "сотрудник банка.",
                    )
        application.refresh_from_db()
        return Response(serialize(application))
