import asyncio
import json
import os
import re
import time
from io import StringIO
from unittest.mock import AsyncMock, patch

import httpx
from django.core.cache import cache
from django.core.management import call_command
from django.test import SimpleTestCase
from pydantic import ValidationError as ModelValidationError
from rest_framework.test import APITestCase

from .consultant import (
    SYSTEM_PROMPT,
    ConsultationInput,
    LLMConfig,
    ProductConsultationResponse,
    consult_product,
    fallback_response,
    parse_response,
)


def answer(product="working_capital", term=12):
    return {
        "product": product,
        "confidence": 0.95,
        "title": "Подходящий кредитный продукт",
        "explanation": (
            "Этот продукт подходит под задачу вашего бизнеса. "
            "Срок учитывает период использования средств."
        ),
        "suggested_term_months": term,
        "alternative_product": None,
        "is_fallback": False,
    }


def provider_response(value):
    content = value if isinstance(value, str) else json.dumps(value)
    return httpx.Response(
        200, json={"choices": [{"message": {"content": content}}]}
    )


class ConsultantServiceTests(SimpleTestCase):
    def consult(self, value=None, *, response=None, handler=None, **kwargs):
        kwargs.setdefault("config", LLMConfig(base_url="http://llm.test/v1"))
        if handler is None:

            def handler(request):
                return (
                    response
                    if response is not None
                    else provider_response(value)
                )

        return asyncio.run(
            consult_product(
                "Закупаем партию товара",
                transport=httpx.MockTransport(handler),
                **kwargs,
            )
        )

    def test_query_is_trimmed_before_length_and_type_validation(self):
        self.assertEqual(
            ConsultationInput(user_query="  закупка  ").user_query, "закупка"
        )
        for value in ["    ", " 1234 ", "я" * 1001, 12345, None]:
            with self.subTest(value=str(value)[:15]):
                with self.assertRaises(ModelValidationError):
                    ConsultationInput(user_query=value)
        self.assertEqual(
            len(ConsultationInput(user_query="я" * 1000).user_query), 1000
        )

    def test_prompt_has_valid_few_shot_examples_for_all_four_products(self):
        examples = re.findall(r"Ответ: (\{.*?\})", SYSTEM_PROMPT)
        self.assertGreaterEqual(len(examples), 3)
        products = {
            ProductConsultationResponse.model_validate(
                json.loads(value)
            ).product
            for value in examples
        }
        self.assertEqual(
            products,
            {
                "overdraft",
                "working_capital",
                "equipment_purchase",
                "investment",
            },
        )

    def test_four_products_and_product_specific_term_validation(self):
        for product, lower, upper in [
            ("overdraft", 1, 3),
            ("working_capital", 6, 24),
            ("equipment_purchase", 12, 60),
            ("investment", 24, 120),
        ]:
            for term in [lower, upper]:
                response = self.consult(answer(product, term))
                self.assertFalse(response.is_fallback)
                self.assertEqual(response.product, product)
            self.assertTrue(
                self.consult(answer(product, upper + 1)).is_fallback
            )

    def test_openai_contract_and_configuration_are_used(self):
        def handler(request):
            self.assertEqual(
                str(request.url), "https://llm.test/v1/chat/completions"
            )
            self.assertEqual(
                request.headers["Authorization"], "Bearer test-secret"
            )
            data = json.loads(request.content)
            self.assertEqual(data["model"], "jury-qwen")
            self.assertEqual(data["temperature"], 0.1)
            self.assertFalse(data["stream"])
            self.assertEqual(data["messages"][0]["role"], "system")
            self.assertEqual(
                data["messages"][1]["content"], "Закупаем партию товара"
            )
            self.assertIn("Пример 3", data["messages"][0]["content"])
            return provider_response(answer())

        response = self.consult(
            handler=handler,
            config=LLMConfig(
                "https://llm.test/v1/", "test-secret", "jury-qwen"
            ),
        )
        self.assertFalse(response.is_fallback)

    def test_markdown_and_service_tokens_are_removed(self):
        for wrapper in ["```json\n{}\n```", "<answer>{}</answer>"]:
            response = self.consult(wrapper.format(json.dumps(answer())))
            self.assertFalse(response.is_fallback)
        with self.assertRaises(ValueError):
            parse_response(json.dumps(answer()) + json.dumps(answer()))

    def test_invalid_model_results_always_produce_safe_fallback(self):
        variants = [
            {**answer(), "product": "consumer_credit"},
            {**answer(), "alternative_product": "unknown"},
            {**answer(), "alternative_product": "working_capital"},
            {**answer(), "confidence": 1.1},
            {**answer(), "confidence": float("nan")},
            {**answer(), "suggested_term_months": "12"},
            {**answer(), "suggested_term_months": True},
            {
                **answer(),
                "explanation": (
                    "Гарантированное одобрение кредита. Подайте заявку."
                ),
            },
            {**answer(), "explanation": "Только одно предложение."},
            {**answer(), "title": "Credit product"},
            {**answer(), "is_fallback": True},
            {**answer(), "secret": "unexpected field"},
            {"product": "working_capital"},
            "not a JSON object",
            "{broken json}",
        ]
        for value in variants:
            with self.subTest(value=str(value)[:90]):
                result = self.consult(value)
                self.assertEqual(result.product, "working_capital")
                self.assertTrue(result.is_fallback)
                self.assertEqual(result.confidence, 0.0)
                ProductConsultationResponse.model_validate(result.model_dump())

    def test_network_errors_and_provider_statuses_are_contained(self):
        for status in [400, 401, 429, 500, 502, 503]:
            self.assertTrue(
                self.consult(response=httpx.Response(status)).is_fallback
            )
        for error in [
            httpx.ConnectError("offline"),
            httpx.ReadTimeout("slow"),
        ]:

            def handler(request):
                raise error

            self.assertTrue(self.consult(handler=handler).is_fallback)
        for body in [
            {},
            {"choices": []},
            {"choices": [{"message": {"content": None}}]},
        ]:
            self.assertTrue(
                self.consult(
                    response=httpx.Response(200, json=body)
                ).is_fallback
            )

    def test_oversized_response_is_rejected(self):
        self.assertTrue(
            self.consult(
                response=httpx.Response(200, content=b"a" * 65537)
            ).is_fallback
        )

    def test_global_deadline_includes_waiting_for_provider(self):
        async def delayed(request):
            await asyncio.sleep(10)
            return provider_response(answer())

        started = time.monotonic()
        result = self.consult(
            handler=delayed,
            config=LLMConfig(
                base_url="http://llm.test/v1", timeout_seconds=5.0
            ),
        )
        elapsed = time.monotonic() - started
        self.assertTrue(result.is_fallback)
        self.assertLessEqual(elapsed, 5.1)

    def test_slow_stream_cannot_extend_total_time_budget(self):
        class SlowStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                for _ in range(20):
                    await asyncio.sleep(0.02)
                    yield b"x"

        started = time.monotonic()
        response = self.consult(
            response=httpx.Response(200, stream=SlowStream()),
            config=LLMConfig(
                base_url="http://llm.test/v1", timeout_seconds=0.06
            ),
        )
        self.assertTrue(response.is_fallback)
        self.assertLess(time.monotonic() - started, 0.2)

    def test_async_requests_run_concurrently(self):
        async def run():
            started = 0
            all_started = asyncio.Event()

            async def delayed(request):
                nonlocal started
                started += 1
                if started == 4:
                    all_started.set()
                await asyncio.wait_for(all_started.wait(), timeout=1)
                return provider_response(answer())

            return await asyncio.gather(
                *[
                    consult_product(
                        "Закупаем товар",
                        transport=httpx.MockTransport(delayed),
                        config=LLMConfig(base_url="http://llm.test/v1"),
                    )
                    for _ in range(4)
                ]
            )

        results = asyncio.run(run())
        self.assertTrue(all(not r.is_fallback for r in results))

    def test_env_defaults_and_safe_timeout(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = LLMConfig.from_env()
            self.assertEqual(cfg.base_url, "")
            self.assertEqual(cfg.model_name, "qwen2.5:7b")
            self.assertEqual(cfg.timeout_seconds, 5.0)
        for value in ["nan", "inf", "invalid", "-1", "9"]:
            with patch.dict(os.environ, {"LLM_TIMEOUT_SECONDS": value}):
                self.assertEqual(LLMConfig.from_env().timeout_seconds, 5.0)
        self.assertNotIn("secret", repr(LLMConfig(api_key="secret")))


class ConsultantApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def setUp(self):
        cache.clear()

    def login(self, profile="green"):
        token = self.client.post(
            "/api/v1/auth/demo-login/", {"profile_id": profile}, format="json"
        ).data["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

    def test_auth_roles_and_query_validation(self):
        path = "/api/v1/consultations/"
        self.assertEqual(self.client.post(path, {}).status_code, 401)
        self.login("underwriter")
        self.assertEqual(self.client.post(path, {}).status_code, 403)
        self.login()
        for body in [
            {},
            {"user_query": " 1234 "},
            {"user_query": "я" * 1001},
            {"user_query": 12345},
            {"user_query": "Товар", "LLM_BASE_URL": "http://evil"},
        ]:
            self.assertEqual(
                self.client.post(path, body, format="json").status_code, 400
            )

    def test_api_returns_valid_result_and_trims_input(self):
        self.login()
        mocked = AsyncMock(return_value=fallback_response())
        with patch("api.consultation_views.consult_product", mocked):
            response = self.client.post(
                "/api/v1/consultations/",
                {"user_query": "  Закупаем товар  "},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_fallback"])
        mocked.assert_awaited_once_with("Закупаем товар")

    def test_empty_url_uses_keyword_rules_without_network(self):
        self.login()
        with patch.dict(os.environ, {"LLM_BASE_URL": ""}):
            with patch("api.consultant.httpx.AsyncClient") as client:
                for query, product in [
                    (
                        "Нечем платить зарплату завтра, "
                        "клиент задерживает расчет",
                        "overdraft",
                    ),
                    (
                        "Закупаем партию обуви на осенне-зимний сезон",
                        "working_capital",
                    ),
                    (
                        "Нужны новые станки и оборудование",
                        "equipment_purchase",
                    ),
                    ("Открываем новую точку", "investment"),
                ]:
                    response = self.client.post(
                        "/api/v1/consultations/",
                        {"user_query": query},
                        format="json",
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.data["product"], product)
                    self.assertTrue(response.data["is_fallback"])
                client.assert_not_called()

    def test_investment_recommendation_is_a_valid_draft(self):
        self.login()
        values = {
            "product_id": "investment",
            "amount": 2000000,
            "term_months": 120,
            "purpose": "Открытие филиала",
            "monthly_revenue": 1500000,
            "current_monthly_payments": 40000,
        }
        response = self.client.post(
            "/api/v1/applications/", values, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        values["product_id"] = "working_capital"
        self.assertEqual(
            self.client.post(
                "/api/v1/applications/", values, format="json"
            ).status_code,
            400,
        )

    def test_profile_has_consultation_rate_limit(self):
        self.login()
        with patch(
            "api.consultation_views.consult_product",
            AsyncMock(return_value=fallback_response()),
        ):
            for _ in range(10):
                response = self.client.post(
                    "/api/v1/consultations/",
                    {"user_query": "Закупаем товар"},
                    format="json",
                )
                self.assertEqual(response.status_code, 200)
            self.assertEqual(
                self.client.post(
                    "/api/v1/consultations/",
                    {"user_query": "Закупаем товар"},
                    format="json",
                ).status_code,
                429,
            )
