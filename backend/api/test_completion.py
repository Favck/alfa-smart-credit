import hashlib
import uuid
from io import BytesIO, StringIO
from unittest.mock import patch
from zipfile import ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from pypdf import PdfReader
from rest_framework.test import APITestCase

from .models import Application, Disbursement, Document, Offer
from .test_pipeline import VALUES, result


class CompletionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def login(self, role="green"):
        response = self.client.post(
            "/api/v1/auth/demo-login/", {"profile_id": role}, format="json"
        )
        self.client.credentials(
            HTTP_AUTHORIZATION="Token " + response.data["token"]
        )

    def create(self, status="DRAFT"):
        self.login()
        response = self.client.post(
            "/api/v1/applications/", VALUES, format="json"
        )
        identity = response.data["id"]
        if status != "DRAFT":
            with patch(
                "api.scoring.call_ml",
                return_value=result(
                    score=700 if status == "APPROVED" else 600
                ),
            ):
                response = self.client.post(
                    f"/api/v1/applications/{identity}/submit/"
                )
            self.assertEqual(response.data["status"], status)
        return str(identity)

    def post(self, identity, route, values=None):
        return self.client.post(
            f"/api/v1/applications/{identity}/{route}",
            values or {},
            format="json",
        )

    def bank(self, identity, values):
        self.login("underwriter")
        return self.client.post(
            f"/api/v1/bank/applications/{identity}/decisions/",
            values,
            format="json",
        )

    def upload(
        self,
        identity,
        filename="statement.pdf",
        content=b"%PDF-1.7\nDEMO\n%%EOF",
    ):
        return self.client.post(
            f"/api/v1/applications/{identity}/documents/",
            {"file": SimpleUploadedFile(filename, content)},
            format="multipart",
        )

    def test_approved_offer_contract_and_idempotent_disbursement(self):
        identity = self.create("APPROVED")
        offer = Offer.objects.get(application_id=identity)
        route = f"offers/{offer.id}/accept/"
        self.assertEqual(self.post(identity, route).data["status"], "SIGNING")
        self.assertEqual(self.post(identity, route).status_code, 200)
        self.assertEqual(
            Document.objects.filter(application_id=identity).count(), 1
        )
        document = Document.objects.get(application_id=identity)
        pdf = PdfReader(BytesIO(bytes(document.content)))
        self.assertIn("ДЕМОНСТРАЦИОННЫЙ", pdf.pages[0].extract_text())
        self.assertEqual(
            self.post(
                identity,
                "sign/",
                {"document_id": str(document.id), "consent": False},
            ).status_code,
            400,
        )
        values = {"document_id": str(document.id), "consent": True}
        signed = self.post(identity, "sign/", values)
        self.assertEqual(signed.data["status"], "DISBURSED")
        self.assertEqual(
            signed.data["disbursement"]["amount"], VALUES["amount"]
        )
        self.assertTrue(signed.data["disbursement"]["simulated"])
        self.assertEqual(
            self.post(identity, "sign/", values).data["disbursement"]["id"],
            signed.data["disbursement"]["id"],
        )
        self.assertEqual(Disbursement.objects.count(), 1)
        document.refresh_from_db()
        self.assertEqual(
            document.sha256,
            hashlib.sha256(bytes(document.content)).hexdigest(),
        )
        self.assertIsNotNone(document.signed_at)
        self.assertEqual(self.post(identity, "cancel/").status_code, 409)
        self.assertEqual(
            self.post(identity, "submit/").data["status"], "DISBURSED"
        )

    def test_counter_offer_uses_accepted_amount_and_keeps_requested_amount(
        self,
    ):
        identity = self.create("REVIEW")
        values = {
            "verdict": "counter",
            "reason": "Подтверждён меньший лимит",
            "amount": 900000,
            "term_months": 18,
            "annual_rate_percent": 20,
        }
        self.assertEqual(self.bank(identity, values).status_code, 201)
        self.login()
        offer = Offer.objects.get(application_id=identity)
        accepted = self.post(identity, f"offers/{offer.id}/accept/")
        self.assertEqual(accepted.data["amount"], VALUES["amount"])
        self.assertEqual(accepted.data["current_offer"]["amount"], 900000)
        doc = Document.objects.get(application_id=identity)
        signed = self.post(
            identity, "sign/", {"document_id": str(doc.id), "consent": True}
        )
        self.assertEqual(signed.data["disbursement"]["amount"], 900000)

    def test_need_info_upload_rescore_preserves_context_then_bank_decides(
        self,
    ):
        identity = self.create("REVIEW")
        old_events = Application.objects.get(pk=identity).events.count()
        decision = {
            "verdict": "need_info",
            "reason": "Подтвердите выручку выпиской",
            "requested_fields": ["monthly_revenue"],
            "document_required": True,
        }
        self.assertEqual(self.bank(identity, decision).status_code, 201)
        self.login()
        app = Application.objects.get(pk=identity)
        info = app.info_requests.get(status="open")
        route = f"info-requests/{info.id}/respond/"
        self.assertEqual(
            self.post(
                identity, route, {"monthly_revenue": 1800000}
            ).status_code,
            400,
        )
        doc = self.upload(identity)
        self.assertEqual(doc.status_code, 201, doc.data)
        with patch("api.scoring.call_ml", return_value=result()) as model:
            reply = self.post(
                identity,
                route,
                {
                    "monthly_revenue": 1800000,
                    "document_ids": [str(doc.data["id"])],
                    "message": "Уточнено",
                },
            )
            self.assertEqual(reply.data["status"], "REVIEW")
            model.assert_called_once()
        self.assertEqual(
            self.post(
                identity,
                route,
                {
                    "monthly_revenue": 1800000,
                    "document_ids": [str(doc.data["id"])],
                },
            ).status_code,
            409,
        )
        app.refresh_from_db()
        self.assertEqual(app.monthly_revenue, 1800000)
        self.assertGreater(app.events.count(), old_events)
        self.assertEqual(app.documents.count(), 1)
        self.assertEqual(app.info_requests.get().status, "answered")
        self.assertEqual(
            self.bank(
                identity,
                {"verdict": "approve", "reason": "Сведения проверены"},
            ).status_code,
            201,
        )

    def test_documents_are_scoped_and_downloaded_with_safe_headers(self):
        identity = self.create()
        uploaded = self.upload(identity)
        self.assertEqual(uploaded.status_code, 201, uploaded.data)
        docid = str(uploaded.data["id"])
        route = f"/api/v1/applications/{identity}/documents/{docid}/download/"
        downloaded = self.client.get(route)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["X-Content-Type-Options"], "nosniff")
        self.assertEqual(downloaded["Cache-Control"], "private, no-store")
        self.assertTrue(
            b"".join(downloaded.streaming_content).startswith(b"%PDF-")
        )
        self.login("yellow")
        self.assertEqual(self.client.get(route).status_code, 404)
        self.assertEqual(
            self.client.get(
                f"/api/v1/applications/{identity}/documents/"
            ).status_code,
            404,
        )
        self.login("underwriter")
        bank_docs = self.client.get(
            f"/api/v1/bank/applications/{identity}/documents/"
        )
        self.assertEqual(bank_docs.status_code, 200)
        self.assertNotIn("content", bank_docs.data[0])
        self.assertEqual(self.client.get(route).status_code, 200)

    def test_upload_validation_and_count_limit(self):
        identity = self.create()
        self.assertEqual(
            self.upload(identity, "bad.pdf", b"text").status_code, 400
        )
        self.assertEqual(self.upload(identity, "run.exe").status_code, 400)
        self.assertEqual(
            self.upload(
                identity, "huge.pdf", b"a" * (10 * 1024 * 1024 + 1)
            ).status_code,
            400,
        )
        data = BytesIO()
        with ZipFile(data, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("xl/workbook.xml", "<workbook/>")
        self.assertEqual(
            self.upload(
                identity, "statement.xlsx", data.getvalue()
            ).status_code,
            201,
        )
        for _ in range(5):
            self.assertEqual(self.upload(identity).status_code, 201)
        self.assertEqual(self.upload(identity).status_code, 400)

    def test_invalid_and_foreign_operations_do_not_change_state(self):
        identity = self.create("REVIEW")
        self.assertEqual(
            self.bank(
                identity, {"verdict": "counter", "reason": "Нет условий"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.bank(
                identity, {"verdict": "need_info", "reason": "Нет запроса"}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.bank(
                identity,
                {
                    "verdict": "need_info",
                    "reason": "Поле",
                    "requested_fields": ["score"],
                },
            ).status_code,
            400,
        )
        self.assertEqual(
            self.bank(
                identity, {"verdict": "approve", "reason": "Проверено"}
            ).status_code,
            201,
        )
        offer = Offer.objects.get(application_id=identity)
        self.login("yellow")
        self.assertEqual(
            self.post(identity, f"offers/{offer.id}/accept/").status_code, 404
        )
        self.login()
        self.assertEqual(
            self.post(identity, f"offers/{uuid.uuid4()}/accept/").status_code,
            404,
        )
        self.assertEqual(
            self.post(
                identity,
                "sign/",
                {"document_id": str(uuid.uuid4()), "consent": True},
            ).status_code,
            404,
        )
        declined = self.post(identity, f"offers/{offer.id}/decline/")
        self.assertEqual(declined.data["status"], "CANCELLED")
        self.assertEqual(
            self.post(identity, f"offers/{offer.id}/accept/").status_code, 409
        )
