from io import StringIO

from django.core.management import call_command
from django.test import override_settings
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APITestCase


class ApiSmokeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def login_as(self, profile):
        response = self.client.post(
            "/api/v1/auth/demo-login/", {"profile_id": profile}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return token

    def test_public_docs_health_and_profiles(self):
        self.assertEqual(self.client.get("/").url, "/api/docs/")
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)
        self.assertEqual(self.client.get("/api/schema/").status_code, 200)
        self.assertEqual(
            self.client.get("/api/v1/health/").data,
            {"status": "ok", "database": "ok"},
        )
        self.assertEqual(
            len(self.client.get("/api/v1/auth/demo-profiles/").data), 4
        )

    def test_click_login_company_and_logout(self):
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)
        token = self.login_as("green")
        self.assertEqual(
            self.client.get("/api/v1/auth/me/").data["role"], "client"
        )
        self.assertEqual(
            self.client.get("/api/v1/company/").data["id"], "grain"
        )
        self.assertEqual(
            self.client.post("/api/v1/auth/logout/").status_code, 204
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)

    def test_roles_are_separated(self):
        self.login_as("green")
        self.assertEqual(
            self.client.get("/api/v1/bank/applications/").status_code, 403
        )
        self.login_as("underwriter")
        self.assertEqual(self.client.get("/api/v1/company/").status_code, 403)
        self.assertEqual(
            self.client.get("/api/v1/applications/").status_code, 403
        )
        self.assertEqual(
            self.client.get("/api/v1/bank/applications/").status_code, 501
        )

    def test_invalid_profile_is_not_created(self):
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/demo-login/", {"profile_id": "admin"}
            ).status_code,
            400,
        )

    @override_settings(DEMO_MODE=False)
    def test_demo_entry_can_be_disabled(self):
        self.assertEqual(
            self.client.get("/api/v1/auth/demo-profiles/").status_code, 403
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/demo-login/", {"profile_id": "green"}
            ).status_code,
            403,
        )

    def test_news_changes_with_company_and_has_full_content(self):
        self.login_as("green")
        green_categories = {
            n["category"] for n in self.client.get("/api/v1/news/").data
        }
        self.login_as("yellow")
        yellow_categories = {
            n["category"] for n in self.client.get("/api/v1/news/").data
        }
        self.assertEqual(green_categories, {"production", "finance"})
        self.assertEqual(yellow_categories, {"trade", "finance"})
        self.assertTrue(self.client.get("/api/v1/news/1/").data["body"])
        self.assertEqual(
            self.client.get("/api/v1/news/?category=unknown").status_code, 400
        )

    def test_catalog_and_missing_items(self):
        self.login_as("green")
        self.assertEqual(len(self.client.get("/api/v1/products/").data), 3)
        self.assertEqual(
            self.client.get("/api/v1/products/overdraft/").status_code, 200
        )
        self.assertEqual(
            self.client.get("/api/v1/products/unknown/").status_code, 404
        )
        self.assertEqual(self.client.get("/api/v1/news/999/").status_code, 404)

    def test_planned_operations_are_explicit(self):
        self.login_as("green")
        response = self.client.post("/api/v1/applications/", {}, format="json")
        self.assertEqual(response.status_code, 501)
        self.assertEqual(response.data["code"], "not_implemented")
        schema = SchemaGenerator().get_schema(request=None, public=True)
        for path, methods in schema["paths"].items():
            for method, operation in methods.items():
                if method in {
                    "get",
                    "post",
                    "patch",
                    "delete",
                    "put",
                } and "[ПЛАН]" in operation.get("summary", ""):
                    self.assertIn("501", operation["responses"], path)
                    self.assertEqual(
                        operation["x-implementation-status"], "planned"
                    )

    def test_seed_is_repeatable_and_does_not_revoke_login(self):
        self.login_as("green")
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 200)
