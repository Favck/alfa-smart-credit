import json
import os
import uuid
from datetime import timedelta
from io import StringIO
from unittest import skipUnless
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from . import scoring
from .demo_data import COMPANIES
from .models import Application

VALUES = {
    "product_id": "working_capital",
    "amount": 2000000,
    "term_months": 24,
    "purpose": "Закупка сырья",
    "monthly_revenue": 1500000,
    "current_monthly_payments": 40000,
}


def result(score=700, limit=3000000, stops=None, request_id=None):
    return {
        "request_id": str(request_id or uuid.uuid4()),
        "score": score,
        "pd": 0.1,
        "grade": "A",
        "stop_factors": stops or [],
        "reasons": [
            {"factor": "dti", "impact": 30, "text": "Низкая нагрузка"}
        ],
        "max_affordable_amount": limit,
        "model_version": "supplied-model",
        "recommendation": "approve",
        "approval_probability_percent": 90,
        "scoring_unavailable": False,
    }


class PipelineTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def login(self, profile="green"):
        response = self.client.post(
            "/api/v1/auth/demo-login/", {"profile_id": profile}, format="json"
        )
        self.client.credentials(
            HTTP_AUTHORIZATION="Token " + response.data["token"]
        )

    def create(self, values=None, **headers):
        return self.client.post(
            "/api/v1/applications/", values or VALUES, format="json", **headers
        )

    def submit(self, identity):
        return self.client.post(f"/api/v1/applications/{identity}/submit/")

    def test_persistence_scoring_history_and_idempotent_submit(self):
        self.login()
        created = self.create()
        self.assertEqual(created.status_code, 201)
        identity = created.data["id"]
        with patch("api.scoring.call_ml", return_value=result()) as model:
            submitted = self.submit(identity)
            self.assertEqual(submitted.data["status"], "APPROVED")
            self.assertEqual(self.submit(identity).status_code, 200)
            self.assertEqual(model.call_count, 1)
        saved = Application.objects.get(pk=identity)
        self.assertEqual(saved.scoring["score"], 700)
        self.assertEqual(saved.decisions.count(), 1)
        self.assertEqual(
            list(saved.events.values_list("to_status", flat=True)),
            ["DRAFT", "SUBMITTED", "CHECK", "ENRICH", "SCORING", "APPROVED"],
        )
        self.login()
        listed = self.client.get("/api/v1/applications/")
        self.assertEqual(listed.data["count"], 1)
        self.assertNotIn("scoring", listed.data["results"][0])
        self.assertEqual(
            self.client.get(
                f"/api/v1/applications/{identity}/history/"
            ).status_code,
            200,
        )

    def test_unavailable_ml_keeps_application_for_manual_decision(self):
        self.login()
        identity = self.create().data["id"]
        with patch("api.scoring.call_ml", side_effect=scoring.MLUnavailable):
            submitted = self.submit(identity)
        self.assertEqual(submitted.data["status"], "REVIEW")
        self.login("underwriter")
        detail = self.client.get(f"/api/v1/bank/applications/{identity}/").data
        self.assertTrue(detail["scoring_unavailable"])
        self.assertIsNone(detail["scoring"])
        response = self.client.post(
            f"/api/v1/bank/applications/{identity}/decisions/",
            {
                "verdict": "approve",
                "reason": "Проверены документы и финансовые показатели.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.client.post(
                f"/api/v1/bank/applications/{identity}/decisions/",
                {"verdict": "reject", "reason": "Повторное решение"},
                format="json",
            ).status_code,
            409,
        )
        self.login()
        self.assertEqual(
            self.client.get(f"/api/v1/applications/{identity}/").data[
                "status"
            ],
            "APPROVED",
        )

    def test_stop_factors_win_over_recommendation_and_are_private(self):
        self.login("red")
        identity = self.create().data["id"]
        with patch(
            "api.scoring.call_ml",
            return_value=result(stops=["BKI_CRITICAL_OVERDUE_90_PLUS"]),
        ):
            response = self.submit(identity)
        self.assertEqual(response.data["status"], "REJECTED")
        self.assertNotIn("BKI_CRITICAL", json.dumps(response.data))
        self.assertIn(
            "просрочка", response.data["client_scoring"]["reasons"][0]
        )

    def test_product_limits_and_fields_owned_by_server(self):
        self.login()
        for changes in [
            {"amount": 999999999},
            {"term_months": 120},
            {"monthly_revenue": 10**13},
        ]:
            self.assertEqual(
                self.create({**VALUES, **changes}).status_code, 400
            )
        identity = self.create(
            {
                **VALUES,
                "company_id": "vector",
                "status": "APPROVED",
                "bki_max_overdue_days": 0,
            }
        ).data["id"]
        application = Application.objects.get(pk=identity)
        self.assertEqual(application.company_id, "grain")
        self.assertEqual(application.status, "DRAFT")
        with patch("api.scoring.call_ml", return_value=result()) as model:
            self.submit(identity)
        self.assertEqual(model.call_args.args[1]["bki_active_loans"], 1)

    def test_owner_isolation_roles_and_cancel(self):
        self.login()
        identity = self.create().data["id"]
        self.login("yellow")
        self.assertEqual(
            self.client.get("/api/v1/applications/").data["count"], 0
        )
        for suffix in ["", "history/", "scoring/"]:
            self.assertEqual(
                self.client.get(
                    f"/api/v1/applications/{identity}/{suffix}"
                ).status_code,
                404,
            )
        self.assertEqual(self.submit(identity).status_code, 404)
        self.assertEqual(
            self.client.get("/api/v1/bank/applications/").status_code, 403
        )
        self.login("underwriter")
        self.assertEqual(self.create().status_code, 403)
        self.assertEqual(
            self.client.get("/api/v1/bank/applications/").data["count"], 1
        )
        self.login()
        self.assertEqual(
            self.client.post(
                f"/api/v1/applications/{identity}/cancel/", {}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(self.submit(identity).status_code, 409)

    def test_idempotency_key_and_draft_edit(self):
        self.login()
        key = str(uuid.uuid4())
        original = self.create(HTTP_IDEMPOTENCY_KEY=key)
        repeated = self.create(HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(original.data["id"], repeated.data["id"])
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(
            self.create(
                {**VALUES, "amount": 2500000}, HTTP_IDEMPOTENCY_KEY=key
            ).status_code,
            409,
        )
        identity = original.data["id"]
        self.assertEqual(
            self.client.patch(
                f"/api/v1/applications/{identity}/",
                {"amount": 2500000},
                format="json",
            ).status_code,
            200,
        )
        with patch("api.scoring.call_ml", return_value=result(score=560)):
            self.assertEqual(self.submit(identity).data["status"], "REVIEW")
        self.assertEqual(
            self.client.patch(
                f"/api/v1/applications/{identity}/",
                {"amount": 1000000},
                format="json",
            ).status_code,
            409,
        )

    def test_manual_reason_required_and_no_decision_on_draft(self):
        self.login()
        identity = self.create().data["id"]
        self.login("underwriter")
        path = f"/api/v1/bank/applications/{identity}/decisions/"
        self.assertEqual(
            self.client.post(
                path, {"verdict": "approve", "reason": " "}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                path,
                {"verdict": "approve", "reason": "Проверено"},
                format="json",
            ).status_code,
            409,
        )

    def test_low_score_and_insufficient_limit_not_auto_approved(self):
        self.assertEqual(
            scoring.verdict(result(score=490), 2000000)[0], "REJECTED"
        )
        self.assertEqual(
            scoring.verdict(result(limit=1000000), 2000000)[0], "REVIEW"
        )

    def test_edit_race_does_not_score_outdated_parameters(self):
        self.login()
        identity = self.create().data["id"]
        original_features = scoring.features

        def concurrent_edit(*args):
            payload = original_features(*args)
            Application.objects.filter(pk=identity).update(
                amount=2500000, updated_at=timezone.now()
            )
            return payload

        with patch("api.scoring.features", side_effect=concurrent_edit):
            with patch("api.scoring.call_ml") as model:
                self.assertEqual(self.submit(identity).status_code, 409)
                model.assert_not_called()
        with patch("api.scoring.call_ml", return_value=result()) as model:
            self.assertEqual(self.submit(identity).status_code, 200)
            self.assertEqual(model.call_args.args[1]["amount"], 2500000)

    def test_active_scoring_is_not_duplicated_and_stale_job_recovers(self):
        self.login()
        identity = self.create().data["id"]
        Application.objects.filter(pk=identity).update(
            status="SCORING", updated_at=timezone.now()
        )
        with patch("api.scoring.call_ml") as model:
            self.assertEqual(self.submit(identity).status_code, 409)
            model.assert_not_called()
        Application.objects.filter(pk=identity).update(
            updated_at=timezone.now() - timedelta(seconds=31)
        )
        with patch("api.scoring.call_ml", return_value=result()):
            self.assertEqual(self.submit(identity).data["status"], "APPROVED")
        saved = Application.objects.get(pk=identity)
        self.assertEqual(saved.decisions.count(), 1)
        self.assertEqual(
            list(saved.events.values_list("to_status", flat=True)),
            ["DRAFT", "SCORING", "APPROVED"],
        )

    def test_preview_unavailable_does_not_create_application(self):
        self.login()
        with patch("api.scoring.call_ml", side_effect=scoring.MLUnavailable):
            response = self.client.post(
                "/api/v1/scoring/pre-predict/", VALUES, format="json"
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Application.objects.count(), 0)


class GatewayTests(SimpleTestCase):
    def test_timeout_and_bad_response_are_unavailable(self):
        payload = scoring.features(COMPANIES[0], VALUES, "preview")
        with patch("api.scoring.urlopen", side_effect=TimeoutError):
            with self.assertRaises(scoring.MLUnavailable):
                scoring.call_ml("evaluate", payload)
        for body in [
            b"{}",
            b"not json",
            b'{"pd":NaN}',
            json.dumps(result()).encode(),
        ]:
            response = MagicMock()
            response.__enter__.return_value.read.return_value = body
            with patch("api.scoring.urlopen", return_value=response):
                with self.assertRaises(scoring.MLUnavailable):
                    scoring.call_ml("evaluate", payload)

    def test_correlated_response_and_safe_adapter(self):
        payload = scoring.features(COMPANIES[0], VALUES, "example")
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            result(request_id=payload["request_id"])
        ).encode()
        with patch("api.scoring.urlopen", return_value=response):
            self.assertEqual(
                scoring.call_ml("evaluate", payload)["score"], 700
            )
        with patch(
            "api.scoring.call_ml",
            return_value={
                "status": "green",
                "recommended_max_amount": 10**9,
                "recommended_min_term_months": 120,
                "estimated_monthly_payment": 999999,
                "approval_probability_percent": 90,
                "dti_forecast": 0.1,
                "hint_message": "raw hint",
            },
        ):
            preview = scoring.preview(COMPANIES[0], VALUES)
        self.assertEqual(preview["recommended_max_amount"], 5000000)
        self.assertIsNone(preview["recommended_min_term_months"])
        self.assertEqual(
            preview["estimated_monthly_payment"],
            scoring.estimated_payment(VALUES),
        )
        self.assertIsNone(
            scoring.estimated_payment({**VALUES, "product_id": "overdraft"})
        )


@skipUnless(
    os.environ.get("ML_INTEGRATION") == "1", "Real ML service is opt-in"
)
class RealMLTests(APITestCase):
    login = PipelineTests.login
    create = PipelineTests.create
    submit = PipelineTests.submit

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def test_real_service_all_profiles_and_contract(self):
        for profile in ["green", "yellow", "red"]:
            self.login(profile)
            company = self.client.get("/api/v1/company/").data
            values = {
                **VALUES,
                "monthly_revenue": company["monthly_revenue"],
                "current_monthly_payments": company[
                    "current_monthly_payments"
                ],
            }
            preview = self.client.post(
                "/api/v1/scoring/pre-predict/", values, format="json"
            )
            self.assertEqual(preview.status_code, 200, preview.data)
            self.assertIn("method_note", preview.data)
            identity = self.create(values).data["id"]
            response = self.submit(identity)
            self.assertEqual(response.status_code, 200, response.data)
            saved = Application.objects.get(pk=identity)
            self.assertFalse(saved.scoring_unavailable)
            self.assertEqual(len(saved.scoring["reasons"]), 5)
            self.assertEqual(
                str(saved.request_id), saved.scoring["request_id"]
            )
            if profile == "red":
                self.assertEqual(saved.status, "REJECTED")
                self.assertIn(
                    "BKI_CRITICAL_OVERDUE_90_PLUS",
                    saved.scoring["stop_factors"],
                )
