from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
    extend_schema,
)
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import serializers as S
from .demo_data import COMPANIES, NEWS, PRODUCTS, PROFILES
from .permissions import IsBank, IsClient, get_profile


def user_data(user):
    profile = get_profile(user)
    if not profile:
        raise PermissionDenied("Этот пользователь не является демо-профилем.")
    return {
        "id": user.pk,
        "name": profile["name"],
        "role": profile["role"],
        "profile_id": profile["id"],
        "company_id": profile["company_id"],
    }


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Система"],
        summary="Доступность Django и базы данных",
        responses={200: S.Health, 503: S.Health},
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response(
                {"status": "unavailable", "database": "unavailable"},
                status=503,
            )
        return Response({"status": "ok", "database": "ok"})


class DemoProfilesView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Демо-вход"],
        summary="Готовые профили для входа по клику",
        responses={200: S.DemoProfile(many=True), 403: S.Error},
    )
    def get(self, request):
        if not settings.DEMO_MODE:
            raise PermissionDenied("Демо-режим отключён.")
        return Response(S.DemoProfile(PROFILES, many=True).data)


class DemoLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Демо-вход"],
        summary="Войти под выбранным демо-профилем",
        description=(
            "Без пароля, только DEMO_MODE=true. Создайте "
            "пользователей командой seed_demo. Скопируйте token"
            " в Authorize в формате `Token <token>`."
        ),
        request=S.DemoLogin,
        responses={
            200: S.LoginResult,
            400: OpenApiResponse(
                description="Неизвестный profile_id или ошибка валидации."
            ),
            403: S.Error,
            503: S.Error,
        },
        examples=[
            OpenApiExample(
                "Клиент: зелёный сценарий",
                value={"profile_id": "green"},
                request_only=True,
            ),
            OpenApiExample(
                "Сотрудник банка",
                value={"profile_id": "underwriter"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        if not settings.DEMO_MODE:
            raise PermissionDenied("Демо-режим отключён.")
        serializer = S.DemoLogin(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = (
            get_user_model()
            .objects.filter(
                username=f"demo_{serializer.validated_data['profile_id']}",
                is_active=True,
            )
            .first()
        )
        if not user:
            return Response(
                {
                    "detail": (
                        "Демо-пользователи не подготовлены. Выполните "
                        "python manage.py seed_demo."
                    )
                },
                status=503,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": user_data(user)})


class MeView(APIView):
    @extend_schema(
        tags=["Демо-вход"],
        summary="Текущий пользователь",
        responses={200: S.CurrentUser, 401: S.Error, 403: S.Error},
    )
    def get(self, request):
        return Response(user_data(request.user))


class LogoutView(APIView):
    @extend_schema(
        tags=["Демо-вход"],
        summary="Выйти и отозвать текущий токен",
        request=None,
        responses={204: None, 401: S.Error},
    )
    def post(self, request):
        request.auth.delete()
        return Response(status=204)


class CompanyView(APIView):
    permission_classes = [IsAuthenticated, IsClient]

    @extend_schema(
        tags=["Компания"],
        summary="Компания текущего клиента",
        responses={200: S.Company, 401: S.Error, 403: S.Error},
    )
    def get(self, request):
        company_id = get_profile(request.user)["company_id"]
        return Response(
            S.Company(next(c for c in COMPANIES if c["id"] == company_id)).data
        )


class ProductsView(APIView):
    @extend_schema(
        tags=["Продукты"],
        summary="Каталог продуктов и допустимые параметры",
        responses=S.Product(many=True),
    )
    def get(self, request):
        return Response(S.Product(PRODUCTS, many=True).data)


class ProductView(APIView):
    @extend_schema(
        tags=["Продукты"],
        summary="Условия выбранного продукта",
        responses={200: S.Product, 404: S.Error},
    )
    def get(self, request, product_id):
        product = next((p for p in PRODUCTS if p["id"] == product_id), None)
        if not product:
            raise NotFound("Продукт не найден.")
        return Response(S.Product(product).data)


class NewsView(APIView):
    @extend_schema(
        tags=["Новости"],
        summary="Персональная лента новостей",
        description=(
            "Без category клиент получает статьи своей отрасли "
            "и общие финансовые статьи; сотрудник банка — все. "
            "С category возвращаются все статьи выбранной "
            "категории. Локальные синтетические статьи, без LLM"
            " и внешних запросов."
        ),
        parameters=[
            OpenApiParameter(
                "category",
                str,
                enum=["trade", "production", "construction", "finance"],
            )
        ],
        responses={200: S.NewsItem(many=True), 400: S.Error},
    )
    def get(self, request):
        category = request.query_params.get("category")
        if category and category not in {
            "trade",
            "production",
            "construction",
            "finance",
        }:
            return Response({"detail": "Неизвестная категория."}, status=400)
        items = NEWS
        if category:
            items = [n for n in items if n["category"] == category]
        else:
            profile = get_profile(request.user)
            if profile and profile["company_id"]:
                company = next(
                    c for c in COMPANIES if c["id"] == profile["company_id"]
                )
                items = [
                    n
                    for n in items
                    if n["category"] in {company["news_category"], "finance"}
                ]
        return Response(S.NewsItem(items, many=True).data)


class NewsDetailView(APIView):
    @extend_schema(
        tags=["Новости"],
        summary="Полный текст статьи",
        responses={200: S.NewsDetail, 404: S.Error},
    )
    def get(self, request, news_id):
        article = next((n for n in NEWS if n["id"] == news_id), None)
        if not article:
            raise NotFound("Статья не найдена.")
        return Response(S.NewsDetail(article).data)


# Ниже — только предлагаемые контракты.
# Ответ 501 не создаёт и не изменяет данные.
def planned(
    tag,
    summary,
    response,
    *,
    request=None,
    status=200,
    description="",
    parameters=None,
    extra_responses=None,
    operation_id=None,
    media_type=None,
):
    return extend_schema(
        tags=[tag],
        summary=f"[ПЛАН] {summary}",
        request=request,
        operation_id=operation_id,
        description=(
            "Контракт для обсуждения. Бизнес-логика ещё не реализована: "
            f"сейчас возвращается 501. {description}"
        ),
        responses={
            (status, media_type) if media_type else status: response,
            400: OpenApiResponse(
                description="Ошибка валидации параметров или полей запроса."
            ),
            401: S.Error,
            403: S.Error,
            404: S.Error,
            409: OpenApiResponse(
                S.Error,
                description=(
                    "Действие недоступно в текущем статусе или конфликт"
                    " версии данных."
                ),
            ),
            501: S.PlannedError,
            **(extra_responses or {}),
        },
        parameters=parameters or [],
        extensions={"x-implementation-status": "planned"},
    )


PAGE_PARAMETERS = [
    OpenApiParameter("page", int, description="Номер страницы, начиная с 1."),
    OpenApiParameter(
        "page_size", int, description="По умолчанию 20, максимум 100."
    ),
]
STATUS_PARAMETER = OpenApiParameter("status", str, enum=S.APPLICATION_STATUSES)


class ContractView(APIView):
    permission_classes = [IsAuthenticated, IsClient]

    def not_implemented(self):
        return Response(
            {
                "code": "not_implemented",
                "detail": (
                    "Это черновой контракт API. Бизнес-логика операции "
                    "ещё не реализована."
                ),
            },
            status=501,
        )


class ApplicationsView(ContractView):
    @planned(
        "Заявки",
        "Список своих заявок",
        S.ApplicationPage,
        operation_id="listApplications",
        parameters=[STATUS_PARAMETER, *PAGE_PARAMETERS],
        description=(
            "Только заявки компании текущего клиента. Порядок: "
            "сначала новые."
        ),
    )
    def get(self, request):
        return self.not_implemented()

    @planned(
        "Заявки",
        "Создать черновик заявки",
        S.Application,
        request=S.ApplicationWrite,
        status=201,
        description=(
            "Компания определяется по авторизации. Начальный "
            "статус DRAFT. В первой версии черновик содержит "
            "все основные числовые поля."
        ),
    )
    def post(self, request):
        return self.not_implemented()


class ApplicationView(ContractView):
    @planned("Заявки", "Карточка своей заявки", S.Application)
    def get(self, request, application_id):
        return self.not_implemented()

    @planned(
        "Заявки",
        "Обновить черновик",
        S.Application,
        request=S.ApplicationPatch,
        description=(
            "Только DRAFT. Нельзя менять company_id, status и "
            "результаты скоринга. Для NEED_INFO используется "
            "отдельный ответ на запрос."
        ),
    )
    def patch(self, request, application_id):
        return self.not_implemented()


class SubmitView(ContractView):
    @planned(
        "Заявки",
        "Отправить заявку в обработку",
        S.Application,
        status=202,
        description=(
            "DRAFT → SUBMITTED. Проверка лимитов продукта, "
            "затем CHECK → ENRICH → SCORING. Конвейер "
            "обрабатывается в фоне; 202 возвращает SUBMITTED. "
            "Способ фонового выполнения ещё не выбран. "
            "Повторная отправка не запускает второй конвейер."
        ),
    )
    def post(self, request, application_id):
        return self.not_implemented()


class CancelView(ContractView):
    @planned(
        "Заявки",
        "Отменить заявку",
        S.Application,
        request=S.Cancel,
        description=(
            "Пока предлагается разрешить отмену в DRAFT, "
            "NEED_INFO и COUNTER_OFFER. Подписанную или "
            "выданную заявку отменить нельзя."
        ),
    )
    def post(self, request, application_id):
        return self.not_implemented()


class HistoryView(ContractView):
    @planned(
        "Заявки",
        "История движения своей заявки",
        S.StatusEvent(many=True),
        description=(
            "Хронологический порядок; используется Vue для "
            "таймлайна. Внутренние комментарии сотрудника не "
            "выдаются."
        ),
    )
    def get(self, request, application_id):
        return self.not_implemented()


class ClientScoringView(ContractView):
    @planned(
        "Скоринг",
        "Понятное клиенту объяснение оценки",
        S.ClientScoring,
        description=(
            "До завершения оценки — 409. Числовые пороги и "
            "внутренние проверки остаются в банковском API."
        ),
    )
    def get(self, request, application_id):
        return self.not_implemented()


class PrePredictView(ContractView):
    @planned(
        "Скоринг",
        "Предварительный расчёт до отправки заявки",
        S.PrePredict,
        request=S.ApplicationWrite,
        extra_responses={503: S.Error},
        description=(
            "Не создаёт заявку. Django добавляет признаки "
            "компании из локальных моков и вызывает ML. "
            "application_id для внутреннего ML-запроса до "
            "создания заявки ещё нужно согласовать. Vue "
            "использует debounce 300–400 мс. При недоступности "
            "ML планируется 503 с возможностью продолжить "
            "оформление."
        ),
    )
    def post(self, request):
        return self.not_implemented()


class OfferView(ContractView):
    @planned(
        "Офферы",
        "Текущее предложение банка",
        S.Offer,
        description="404, если предложение ещё не сформировано.",
    )
    def get(self, request, application_id):
        return self.not_implemented()


class AcceptOfferView(ContractView):
    @planned(
        "Офферы",
        "Принять условия банка",
        S.Application,
        description=(
            "Принимает конкретную версию оффера, относящуюся к "
            "заявке. APPROVED / COUNTER_OFFER → SIGNING. Старый"
            " или уже отклонённый оффер → 409."
        ),
    )
    def post(self, request, application_id, offer_id):
        return self.not_implemented()


class DeclineOfferView(ContractView):
    @planned(
        "Офферы",
        "Отклонить предложение",
        S.Application,
        request=S.Cancel,
        description=(
            "APPROVED / COUNTER_OFFER → CANCELLED. Оффер должен"
            " принадлежать заявке."
        ),
    )
    def post(self, request, application_id, offer_id):
        return self.not_implemented()


class DocumentsView(ContractView):
    @planned("Документы", "Документы своей заявки", S.Document(many=True))
    def get(self, request, application_id):
        return self.not_implemented()

    @planned(
        "Документы",
        "Загрузить выписку или дополнительный документ",
        S.Document,
        request={"multipart/form-data": S.DocumentUpload},
        status=201,
        description=(
            "Только DRAFT / NEED_INFO. Проверяются тип, размер "
            "и принадлежность заявки. Автоматическое извлечение"
            " показателей пока не предполагается."
        ),
    )
    def post(self, request, application_id):
        return self.not_implemented()

    parser_classes = [MultiPartParser, FormParser]


class DocumentDownloadView(ContractView):
    permission_classes = [IsAuthenticated]

    @planned(
        "Документы",
        "Скачать документ",
        OpenApiTypes.BINARY,
        media_type="application/octet-stream",
        description=(
            "Сотрудник банка или владелец заявки. Ответ — файл "
            "с Content-Disposition: attachment. Конкретный "
            "Content-Type зависит от документа."
        ),
    )
    def get(self, request, application_id, document_id):
        return self.not_implemented()


class SignView(ContractView):
    @planned(
        "Документы",
        "Имитировать подписание договора и выдачу",
        S.Application,
        request=S.Sign,
        description=(
            "Только SIGNING, актуальный договор этой заявки и "
            "consent=true. Записывает демо-подпись и переводит "
            "в DISBURSED. Повторный запрос не создаёт повторную"
            " выдачу. Реальных денежных или юридических "
            "операций нет."
        ),
    )
    def post(self, request, application_id):
        return self.not_implemented()


class InfoRequestView(ContractView):
    @planned(
        "Заявки",
        "Текущий запрос дополнительных данных",
        S.InfoRequest,
        description="404, если открытого запроса нет.",
    )
    def get(self, request, application_id):
        return self.not_implemented()


class InfoResponseView(ContractView):
    @planned(
        "Заявки",
        "Ответить на запрос банка",
        S.Application,
        request=S.InfoResponse,
        status=202,
        description=(
            "Только NEED_INFO и открытый запрос этой заявки. "
            "После проверки полноты ответа возвращает заявку в "
            "ENRICH либо REVIEW с сохранением контекста. Не "
            "запускается автоматически при одной лишь загрузке "
            "файла."
        ),
    )
    def post(self, request, application_id, info_request_id):
        return self.not_implemented()


class BankQueueView(ContractView):
    permission_classes = [IsAuthenticated, IsBank]

    @planned(
        "Банк",
        "Очередь заявок банка",
        S.ApplicationPage,
        operation_id="listBankApplications",
        parameters=[
            STATUS_PARAMETER,
            OpenApiParameter("grade", str, enum=["A", "B", "C", "D"]),
            OpenApiParameter(
                "search",
                str,
                description="Номер заявки, название компании или ИНН.",
            ),
            *PAGE_PARAMETERS,
        ],
        description=(
            "По умолчанию REVIEW. Включает заявки без "
            "результата ML, если скоринг недоступен."
        ),
    )
    def get(self, request):
        return self.not_implemented()


class BankApplicationView(ContractView):
    permission_classes = [IsAuthenticated, IsBank]

    @planned(
        "Банк",
        "Полная карточка для андеррайтера",
        S.BankApplication,
        description=(
            "Анкета, компания, результаты обогащения и ML. При "
            "таймауте ML — REVIEW и scoring_unavailable=true."
        ),
    )
    def get(self, request, application_id):
        return self.not_implemented()


class BankDecisionsView(ContractView):
    permission_classes = [IsAuthenticated, IsBank]

    @planned(
        "Банк",
        "История решений",
        S.Decision(many=True),
        description="Системные и ручные решения в хронологическом порядке.",
    )
    def get(self, request, application_id):
        return self.not_implemented()

    @planned(
        "Банк",
        "Принять решение по заявке",
        S.Decision,
        request=S.DecisionWrite,
        status=201,
        description=(
            "Только REVIEW. approve → APPROVED; counter → "
            "COUNTER_OFFER; need_info → NEED_INFO; reject → "
            "REJECTED. Для counter обязательны сумма, срок и "
            "ставка. Для need_info обязателен перечень полей "
            "или document_required=true. Все решения имеют "
            "обоснование и запись аудита. Обход стоп-факторов "
            "пока не предусматривается."
        ),
    )
    def post(self, request, application_id):
        return self.not_implemented()


class BankHistoryView(ContractView):
    permission_classes = [IsAuthenticated, IsBank]

    @planned(
        "Банк",
        "Аудит переходов заявки",
        S.StatusEvent(many=True),
        description=(
            "Неизменяемая история: до/после, роль участника, "
            "причина и время."
        ),
    )
    def get(self, request, application_id):
        return self.not_implemented()


class BankDocumentsView(ContractView):
    permission_classes = [IsAuthenticated, IsBank]

    @planned(
        "Банк",
        "Документы заявки для сотрудника",
        S.Document(many=True),
        description=(
            "Для скачивания используется общий защищённый "
            "маршрут documents/{document_id}/download/."
        ),
    )
    def get(self, request, application_id):
        return self.not_implemented()
