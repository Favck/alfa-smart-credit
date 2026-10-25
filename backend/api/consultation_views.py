"""Authenticated Django adapter for the asynchronous consultant module."""

from asgiref.sync import async_to_sync
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from . import serializers as S
from .consultant import consult_product, fallback_response
from .pipeline import ClientAPI


class ConsultationThrottle(UserRateThrottle):
    scope = "consultation"
    rate = "10/minute"


class ProductConsultationView(ClientAPI):
    """Expose validated recommendations to the current client profile."""

    throttle_classes = [ConsultationThrottle]

    @extend_schema(
        tags=["AI-консультант"],
        summary="Подобрать кредитный продукт по задаче бизнеса",
        request=S.ConsultationWrite,
        responses={200: S.ProductConsultation, 400: S.Error},
        description=(
            "Асинхронный Chat Completions клиент. При сбое LLM возвращает "
            "валидный working_capital с is_fallback=true. "
            "LLM_ENABLED=false отключает сетевые вызовы и возвращает "
            "тот же базовый вариант. "
            "Рекомендация переносится в заявку; кредитное решение принимает "
            "основной конвейер. Не более 10 запросов в минуту на профиль."
        ),
    )
    def post(self, request):
        values = S.ConsultationWrite(data=request.data)
        values.is_valid(raise_exception=True)
        if set(request.data) - {"user_query"}:
            raise ValidationError("Передайте только user_query.")
        result = (
            async_to_sync(consult_product)(values.validated_data["user_query"])
            if settings.LLM_ENABLED
            else fallback_response()
        )
        return Response(result.model_dump(mode="json"))
