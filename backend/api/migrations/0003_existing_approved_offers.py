from decimal import Decimal

from django.db import migrations


def create_offers(apps, schema_editor):
    Application = apps.get_model("api", "Application")
    Offer = apps.get_model("api", "Offer")
    rates = {
        "working_capital": "22.00",
        "equipment_purchase": "19.00",
        "overdraft": "24.00",
    }
    for application in Application.objects.filter(
        status="APPROVED"
    ).iterator():
        if Offer.objects.filter(application_id=application.id).exists():
            continue
        rate = Decimal(rates[application.product_id])
        r = float(rate) / 1200
        payment = (
            None
            if application.product_id == "overdraft"
            else round(
                application.amount
                * r
                / (1 - (1 + r) ** -application.term_months)
            )
        )
        Offer.objects.create(
            application_id=application.id,
            kind="approved",
            amount=application.amount,
            term_months=application.term_months,
            annual_rate_percent=rate,
            monthly_payment=payment,
            explanation=(
                "Предложение по ранее одобренной демонстрационной заявке."
            ),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_offer_document_disbursement_inforequest_and_more")
    ]
    operations = [
        migrations.RunPython(create_offers, migrations.RunPython.noop)
    ]
