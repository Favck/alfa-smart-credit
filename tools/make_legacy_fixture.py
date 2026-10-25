"""CI-only SQLite fixture exercising the production migration's data types."""

import hashlib
import os
from pathlib import Path
import sys

os.environ["DATABASE_ENGINE"] = "sqlite"
if os.getenv("CI") != "true":
    raise SystemExit("This fixture generator runs only in CI.")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import django

django.setup()
from django.contrib.auth import get_user_model
from django.core.management import call_command
from api.demo_data import COMPANIES
from api.models import (
    Application,
    Decision,
    Disbursement,
    Document,
    InfoRequest,
    Offer,
    StatusEvent,
)

call_command("migrate", verbosity=0)
call_command("seed_demo", verbosity=0)
User = get_user_model()
User.objects.create_superuser("legacy-admin", password="ci-only-password")
app = Application.objects.create(
    owner=User.objects.get(username="demo_green"),
    company=COMPANIES[0],
    product_id="working_capital",
    amount=2000000,
    term_months=24,
    monthly_revenue=1500000,
    current_monthly_payments=40000,
    status="DISBURSED",
    scoring={"score": 700},
)
offer = Offer.objects.create(
    application=app,
    kind="approved",
    amount=app.amount,
    term_months=24,
    annual_rate_percent=22,
    monthly_payment=100000,
    status="accepted",
    explanation="Проверка переноса",
)
content = b"%PDF-1.7\nCI migration test\n%%EOF"
Document.objects.create(
    application=app,
    offer=offer,
    kind="contract",
    filename="test.pdf",
    content_type="application/pdf",
    size_bytes=len(content),
    content=content,
    sha256=hashlib.sha256(content).hexdigest(),
)
Disbursement.objects.create(
    application=app,
    offer=offer,
    amount=app.amount,
    account="DEMO",
    reference="CI-MIGRATION",
)
InfoRequest.objects.create(
    application=app,
    message="Проверка",
    requested_fields=["monthly_revenue"],
    status="answered",
    response={"monthly_revenue": 1500000},
)
Decision.objects.create(
    application=app,
    verdict="approve",
    reason="Проверка",
    actor_role="bank",
    application_status="APPROVED",
)
StatusEvent.objects.create(
    application=app,
    from_status="SIGNING",
    to_status="DISBURSED",
    message="Проверка",
    actor_role="client",
)
with open(sys.argv[1], "w", encoding="utf8") as out:
    call_command(
        "dumpdata",
        natural_foreign=True,
        exclude=["contenttypes", "auth.permission"],
        stdout=out,
    )
print(
    "SQLite migration fixture prepared, including administrator and binary document."
)
