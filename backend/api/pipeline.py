import uuid
from copy import deepcopy
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import scoring
from . import serializers as S
from .demo_data import COMPANIES
from .models import Application, Decision, StatusEvent
from .permissions import IsBank, IsClient, get_profile


def company_for(user):
    company_id = get_profile(user)["company_id"]
    return deepcopy(next(c for c in COMPANIES if c["id"] == company_id))


def scoped(request, bank=False):
    return (
        Application.objects.all()
        if bank
        else Application.objects.filter(owner=request.user)
    )


def application_for(request, application_id, bank=False):
    try:
        return scoped(request, bank).get(pk=application_id)
    except Application.DoesNotExist:
        raise NotFound("Заявка не найдена.")


def record(application, before, after, message, role="system"):
    StatusEvent.objects.create(
        application=application,
        from_status=before,
        to_status=after,
        message=message,
        actor_role=role,
    )


def serialize(application, bank=False):
    data = dict(S.Application(application).data)
    data["client_scoring"] = scoring.client_result(application)
    offer = application.offers.exclude(status="declined").first()
    info = application.info_requests.filter(status="open").first()
    receipt = getattr(application, "disbursement", None)
    data.update(
        current_offer=S.Offer(offer).data if offer else None,
        info_request=S.InfoRequest(info).data if info else None,
        disbursement=(
            {
                "id": str(receipt.id),
                "amount": receipt.amount,
                "account": receipt.account,
                "reference": receipt.reference,
                "simulated": True,
                "created_at": receipt.created_at.isoformat(),
            }
            if receipt
            else None
        ),
    )
    if bank:
        data.update(
            company=application.company,
            scoring=application.scoring,
            enrichment=application.enrichment or None,
            scoring_unavailable=application.scoring_unavailable,
        )
    return data


class ClientAPI(APIView):
    permission_classes = [IsAuthenticated, IsClient]


class PrePredictView(ClientAPI):
    @extend_schema(
        tags=["Скоринг"],
        request=S.ValidApplicationWrite,
        responses={200: S.MLPreview, 503: S.Error},
        summary="Предварительная оценка параметров через ML",
    )
    def post(self, request):
        values = S.ValidApplicationWrite(data=request.data)
        values.is_valid(raise_exception=True)
        try:
            return Response(
                scoring.preview(
                    company_for(request.user), values.validated_data
                )
            )
        except scoring.MLUnavailable:
            return Response(
                {
                    "detail": (
                        "Предварительная оценка недоступна. "
                        "Заявку можно отправить на ручное рассмотрение."
                    )
                },
                status=503,
            )


class ApplicationsView(ClientAPI):
    @extend_schema(
        tags=["Заявки"],
        responses=S.LiveApplicationPage,
        operation_id="listClientApplications",
        summary="Сохранённые заявки своей компании",
    )
    def get(self, request):
        return list_response(request)

    @extend_schema(
        tags=["Заявки"],
        request=S.ValidApplicationWrite,
        responses={201: S.LiveApplication, 409: S.Error},
        summary="Создать черновик заявки",
    )
    def post(self, request):
        values = S.ValidApplicationWrite(data=request.data)
        values.is_valid(raise_exception=True)
        key = request.headers.get("Idempotency-Key")
        if key:
            try:
                key = uuid.UUID(key)
            except ValueError:
                raise ValidationError({"Idempotency-Key": "Ожидается UUID."})
            existing = Application.objects.filter(
                owner=request.user, submission_key=key
            ).first()
            if existing:
                if any(
                    getattr(existing, k) != v
                    for k, v in values.validated_data.items()
                ):
                    return Response(
                        {"detail": "Ключ использован с другими параметрами."},
                        status=409,
                    )
                return Response(serialize(existing), status=200)
        try:
            with transaction.atomic():
                application = Application.objects.create(
                    owner=request.user,
                    company=company_for(request.user),
                    submission_key=key,
                    **values.validated_data,
                )
                record(
                    application, None, "DRAFT", "Черновик сохранён.", "client"
                )
        except IntegrityError:
            existing = Application.objects.get(
                owner=request.user, submission_key=key
            )
            if any(
                getattr(existing, k) != v
                for k, v in values.validated_data.items()
            ):
                return Response(
                    {"detail": "Ключ использован с другими параметрами."},
                    status=409,
                )
            return Response(serialize(existing), status=200)
        return Response(serialize(application), status=201)


def list_response(request, bank=False):
    queryset = scoped(request, bank)
    status = request.query_params.get("status")
    if status:
        if status not in S.APPLICATION_STATUSES:
            raise ValidationError({"status": "Неизвестный статус."})
        queryset = queryset.filter(status=status)
    search = request.query_params.get("search", "").strip().lower()
    grade = request.query_params.get("grade")
    if grade and grade not in {"A", "B", "C", "D"}:
        raise ValidationError({"grade": "Неизвестный рейтинг."})
    items = [
        a
        for a in queryset
        if (
            not search
            or search in (a.number + a.company_name + a.company["inn"]).lower()
        )
        and (not grade or (a.scoring or {}).get("grade") == grade)
    ]
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        size = min(100, max(1, int(request.query_params.get("page_size", 20))))
    except ValueError:
        raise ValidationError({"page": "Ожидается номер страницы."})

    def link(number):
        params = request.query_params.copy()
        params["page"] = number
        return request.build_absolute_uri(
            request.path + "?" + params.urlencode()
        )

    start = (page - 1) * size
    return Response(
        {
            "count": len(items),
            "next": link(page + 1) if start + size < len(items) else None,
            "previous": link(page - 1) if page > 1 else None,
            "results": [
                serialize(a, bank) for a in items[start : start + size]
            ],
        }
    )


class ApplicationView(ClientAPI):
    @extend_schema(
        tags=["Заявки"],
        responses=S.LiveApplication,
        summary="Карточка своей заявки",
    )
    def get(self, request, application_id):
        return Response(serialize(application_for(request, application_id)))

    @extend_schema(
        tags=["Заявки"],
        request=S.ApplicationPatch,
        responses={200: S.LiveApplication, 409: S.Error},
        summary="Изменить черновик",
    )
    def patch(self, request, application_id):
        application = application_for(request, application_id)
        patch = S.ApplicationPatch(data=request.data)
        patch.is_valid(raise_exception=True)
        values = {
            key: getattr(application, key)
            for key in S.ApplicationWrite().fields
        }
        values.update(patch.validated_data)
        validated = S.ValidApplicationWrite(data=values)
        validated.is_valid(raise_exception=True)
        with transaction.atomic():
            changed = Application.objects.filter(
                pk=application.pk,
                status="DRAFT",
                updated_at=application.updated_at,
            ).update(**validated.validated_data, updated_at=timezone.now())
            if not changed:
                return Response(
                    {"detail": "Изменять можно только черновик."}, status=409
                )
        application.refresh_from_db()
        return Response(serialize(application))


class SubmitView(ClientAPI):
    @extend_schema(
        tags=["Заявки"],
        request=None,
        responses={200: S.LiveApplication, 409: S.Error},
        summary="Отправить заявку на проверку и ML-скоринг",
    )
    def post(self, request, application_id):
        application = application_for(request, application_id)
        values = {
            key: getattr(application, key)
            for key in S.ApplicationWrite().fields
        }
        payload = scoring.features(application.company, values, application.id)
        with transaction.atomic():
            eligible = Application.objects.filter(
                pk=application.pk,
                status="DRAFT",
                updated_at=application.updated_at,
            )
            if application.status == "SCORING":
                eligible = Application.objects.filter(
                    pk=application.pk,
                    status="SCORING",
                    updated_at__lt=timezone.now() - timedelta(seconds=30),
                )
            changed = eligible.update(
                status="SCORING",
                request_id=payload["request_id"],
                updated_at=timezone.now(),
            )
            if not changed:
                application.refresh_from_db()
                if application.status in {
                    "APPROVED",
                    "REJECTED",
                    "REVIEW",
                    "COUNTER_OFFER",
                    "SIGNING",
                    "DISBURSED",
                    "NEED_INFO",
                }:
                    return Response(serialize(application))
                return Response(
                    {"detail": "Заявка уже обрабатывается или отменена."},
                    status=409,
                )
            before = application.status
            checkpoints = [
                ("SUBMITTED", "Заявка отправлена."),
                ("CHECK", "Параметры продукта проверены."),
                (
                    "ENRICH",
                    "Получены демонстрационные сведения ЕГРЮЛ и БКИ.",
                ),
                ("SCORING", "Запущена оценка кредитного риска."),
            ]
            if before == "SCORING":
                checkpoints = [("SCORING", "Оценка возобновлена после сбоя.")]
            for state, message in checkpoints:
                record(
                    application,
                    before,
                    state,
                    message,
                    "client" if state == "SUBMITTED" else "system",
                )
                before = state
        # Network I/O deliberately occurs outside a SQLite write transaction.
        unavailable = False
        try:
            result = scoring.call_ml("evaluate", payload)
            status, message = scoring.verdict(result, application.amount)
        except scoring.MLUnavailable:
            unavailable, result = True, None
            status, message = (
                "REVIEW",
                "Оценка недоступна. Заявка передана сотруднику банка.",
            )
        enrichment = {
            k: v
            for k, v in payload.items()
            if k.startswith("bki_")
            or k in {"company_status", "company_age_months", "okved_group"}
        }
        enrichment.update(
            source="Локальные синтетические данные ЕГРЮЛ/БКИ",
            fetched_at=timezone.now().isoformat(),
        )
        with transaction.atomic():
            changed = Application.objects.filter(
                pk=application.pk,
                status="SCORING",
                request_id=payload["request_id"],
            ).update(
                status=status,
                scoring=result,
                scoring_unavailable=unavailable,
                enrichment=enrichment,
                updated_at=timezone.now(),
            )
            if changed:
                record(application, "SCORING", status, message)
                Decision.objects.create(
                    application=application,
                    verdict={
                        "APPROVED": "approve",
                        "REJECTED": "reject",
                        "REVIEW": "review",
                    }[status],
                    reason=message,
                    actor_role="system",
                    application_status=status,
                )
                if status == "APPROVED":
                    from .completion import issue_offer

                    issue_offer(application, message)
        application.refresh_from_db()
        return Response(serialize(application))


class CancelView(ClientAPI):
    @extend_schema(
        tags=["Заявки"],
        request=S.Cancel,
        responses={200: S.LiveApplication, 409: S.Error},
        summary="Отменить черновик или заявку на ручном рассмотрении",
    )
    def post(self, request, application_id):
        application = application_for(request, application_id)
        values = S.Cancel(data=request.data)
        values.is_valid(raise_exception=True)
        with transaction.atomic():
            before = application.status
            changed = Application.objects.filter(
                pk=application.pk,
                status__in=[
                    "DRAFT",
                    "REVIEW",
                    "NEED_INFO",
                    "APPROVED",
                    "COUNTER_OFFER",
                    "SIGNING",
                ],
                status=before,
            ).update(status="CANCELLED", updated_at=timezone.now())
            if not changed:
                return Response(
                    {"detail": "В текущем статусе отмена недоступна."},
                    status=409,
                )
            record(
                application,
                before,
                "CANCELLED",
                values.validated_data.get("reason")
                or "Заявка отменена клиентом.",
                "client",
            )
            application.offers.filter(status="pending").update(
                status="declined"
            )
            application.info_requests.filter(status="open").update(
                status="cancelled"
            )
        application.refresh_from_db()
        return Response(serialize(application))


class HistoryView(ClientAPI):
    @extend_schema(
        tags=["Заявки"],
        responses=S.StatusEvent(many=True),
        summary="История своей заявки",
    )
    def get(self, request, application_id):
        return Response(
            S.StatusEvent(
                application_for(request, application_id).events.all(),
                many=True,
            ).data
        )


class ClientScoringView(ClientAPI):
    @extend_schema(
        tags=["Скоринг"],
        responses=S.ClientScoring,
        summary="Понятное клиенту объяснение результата",
    )
    def get(self, request, application_id):
        return Response(
            scoring.client_result(application_for(request, application_id))
        )


class BankAPI(APIView):
    permission_classes = [IsAuthenticated, IsBank]


class BankQueueView(BankAPI):
    @extend_schema(
        tags=["Банк"],
        responses=S.LiveBankApplicationPage,
        operation_id="listBankApplications",
        summary="Сохранённые заявки для сотрудника банка",
    )
    def get(self, request):
        return list_response(request, bank=True)


class BankApplicationView(BankAPI):
    @extend_schema(
        tags=["Банк"],
        responses=S.LiveBankApplication,
        summary="Карточка с результатом модели и сведениями проверок",
    )
    def get(self, request, application_id):
        return Response(
            serialize(application_for(request, application_id, True), True)
        )


class BankHistoryView(BankAPI):
    @extend_schema(
        tags=["Банк"],
        responses=S.StatusEvent(many=True),
        summary="История статусов заявки",
    )
    def get(self, request, application_id):
        return Response(
            S.StatusEvent(
                application_for(request, application_id, True).events.all(),
                many=True,
            ).data
        )


class BankDecisionsView(BankAPI):
    @extend_schema(
        tags=["Банк"],
        responses=S.Decision(many=True),
        summary="История решений по заявке",
    )
    def get(self, request, application_id):
        return Response(
            S.Decision(
                application_for(request, application_id, True).decisions.all(),
                many=True,
            ).data
        )

    @extend_schema(
        tags=["Банк"],
        request=S.WorkflowDecision,
        responses={201: S.Decision, 409: S.Error},
        summary="Решение, встречные условия или дозапрос по заявке",
    )
    def post(self, request, application_id):
        application = application_for(request, application_id, True)
        from .completion import bank_decision

        return bank_decision(request, application)
