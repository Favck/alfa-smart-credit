from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import DatabaseError, connection
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import serializers as S
from .demo_data import COMPANIES, NEWS, PRODUCTS, PROFILES
from .permissions import IsClient, get_profile


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
