"""Small, local PDF contracts. These have no legal effect."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def contract_pdf(application, offer, signed_at=None):
    name = "AlfaDemo"
    if name not in pdfmetrics.getRegisteredFontNames():
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        font = next((p for p in paths if Path(p).is_file()), None)
        if not font:
            raise RuntimeError("Install fonts-dejavu-core for PDF contracts")
        pdfmetrics.registerFont(TTFont(name, font))
    out = BytesIO()
    document = SimpleDocTemplate(
        out,
        pagesize=A4,
        rightMargin=48,
        leftMargin=48,
        topMargin=46,
        bottomMargin=46,
    )
    title = ParagraphStyle(
        "title",
        fontName=name,
        fontSize=21,
        leading=28,
        textColor=colors.HexColor("#172033"),
        spaceAfter=18,
    )
    body = ParagraphStyle(
        "body",
        fontName=name,
        fontSize=10,
        leading=16,
        textColor=colors.HexColor("#30394a"),
        spaceAfter=12,
    )
    warning = ParagraphStyle(
        "warning", parent=body, textColor=colors.HexColor("#dc233e")
    )
    amount = f"{offer.amount:,}".replace(",", " ")
    payment = (
        f"{offer.monthly_payment:,} ₽".replace(",", " ")
        if offer.monthly_payment is not None
        else "Зависит от использования лимита"
    )
    paragraphs = [
        ("Альфа.Поток · ITigers", title),
        ("ДЕМОНСТРАЦИОННЫЙ ДОКУМЕНТ. НЕ ЯВЛЯЕТСЯ ДОГОВОРОМ БАНКА.", warning),
        (f"Заявка {application.number}. Предложение {offer.id}.", body),
        (
            f"Получатель: {escape(application.company_name)}. "
            f"ИНН {escape(application.company['inn'])}.",
            body,
        ),
        (
            f"Сумма финансирования: {amount} ₽. "
            f"Срок: {offer.term_months} мес. "
            f"Демонстрационная ставка: {offer.annual_rate_percent}% годовых.",
            body,
        ),
        (f"Ориентировочный ежемесячный платёж: {payment}.", body),
        (
            "Документ создан для автономного прототипа хакатона. Все сведения "
            "и операции синтетические. Комиссии, реальные банковские счета, "
            "денежные переводы и юридически значимая электронная подпись "
            "не используются.",
            body,
        ),
        (
            "В демосценарии клиент знакомится с условиями, "
            "подтверждает согласие "
            "в кабинете и запускает имитацию выдачи. Повторное подтверждение "
            "не создаёт вторую выдачу.",
            body,
        ),
        (
            (
                (
                    "ДЕМО-ПОДПИСЬ ЗАФИКСИРОВАНА. Время UTC: "
                    + signed_at.isoformat()
                )
                if signed_at
                else (
                    "Документ ожидает демонстрационного "
                    "подписания в кабинете."
                )
            ),
            warning,
        ),
        (
            "Не использовать для реальных финансовых "
            "или юридических операций.",
            warning,
        ),
    ]
    document.build(
        [
            element
            for text, style in paragraphs
            for element in (Paragraph(text, style), Spacer(1, 8))
        ]
    )
    return out.getvalue()
