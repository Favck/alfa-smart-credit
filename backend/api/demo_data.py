(
    "Локальные синтетические справочники. Это не "
    "результаты действующего скоринга."
)

PROFILES = [
    {
        "id": "green",
        "name": "Иван Иванов",
        "role": "client",
        "company_id": "grain",
        "scenario": "green",
        "description": "ООО «Пекарня Зерно»: сценарий автоодобрения",
    },
    {
        "id": "yellow",
        "name": "Алексей Смирнов",
        "role": "client",
        "company_id": "smirnov",
        "scenario": "yellow",
        "description": (
            "ИП Смирнов А.В.: сценарий ручного разбора и " "встречных условий"
        ),
    },
    {
        "id": "red",
        "name": "Пётр Петров",
        "role": "client",
        "company_id": "vector",
        "scenario": "red",
        "description": "ООО «СтройВектор»: сценарий отказа по стоп-фактору",
    },
    {
        "id": "underwriter",
        "name": "Анна Аналитик",
        "role": "bank",
        "company_id": None,
        "scenario": None,
        "description": "Сотрудник банка: очередь заявок и принятие решений",
    },
]

COMPANIES = [
    {
        "id": "grain",
        "name": "ООО «Пекарня Зерно»",
        "inn": "7701234567",
        "ogrn": "1207700123456",
        "legal_form": "company",
        "okved": "10.71",
        "industry": "Производство хлебобулочных изделий",
        "status": "active",
        "registered_at": "2022-01-15",
        "monthly_revenue": 1500000,
        "current_monthly_payments": 40000,
        "news_category": "production",
    },
    {
        "id": "smirnov",
        "name": "ИП Смирнов А.В.",
        "inn": "780234567890",
        "ogrn": "322780000123456",
        "legal_form": "individual_entrepreneur",
        "okved": "47.11",
        "industry": "Розничная торговля",
        "status": "active",
        "registered_at": "2023-03-10",
        "monthly_revenue": 600000,
        "current_monthly_payments": 180000,
        "news_category": "trade",
    },
    {
        "id": "vector",
        "name": "ООО «СтройВектор»",
        "inn": "5003456789",
        "ogrn": "1215000123456",
        "legal_form": "company",
        "okved": "41.20",
        "industry": "Строительство",
        "status": "active",
        "registered_at": "2024-05-20",
        "monthly_revenue": 300000,
        "current_monthly_payments": 120000,
        "news_category": "construction",
    },
]

PRODUCTS = [
    {
        "id": "working_capital",
        "name": "Оборотный кредит",
        "description": "Для закупки сырья и товаров.",
        "min_amount": 500000,
        "max_amount": 5000000,
        "min_term_months": 6,
        "max_term_months": 36,
        "base_rate_percent": "22.00",
        "is_demo_rate": True,
    },
    {
        "id": "equipment_purchase",
        "name": "Кредит на оборудование",
        "description": "Для покупки техники и модернизации производства.",
        "min_amount": 1000000,
        "max_amount": 10000000,
        "min_term_months": 12,
        "max_term_months": 60,
        "base_rate_percent": "19.00",
        "is_demo_rate": True,
    },
    {
        "id": "overdraft",
        "name": "Овердрафт",
        "description": (
            "Для временных кассовых разрывов и платежей "
            "в ожидании поступления выручки."
        ),
        "min_amount": 50000,
        "max_amount": 3000000,
        "min_term_months": 1,
        "max_term_months": 12,
        "base_rate_percent": "24.00",
        "is_demo_rate": True,
    },
    {
        "id": "investment",
        "name": "Инвестиционный кредит",
        "description": "Для новых точек, ремонта и строительства.",
        "min_amount": 1000000,
        "max_amount": 10000000,
        "min_term_months": 24,
        "max_term_months": 120,
        "base_rate_percent": "21.00",
        "is_demo_rate": True,
    },
]

NEWS = [
    {
        "id": 1,
        "title": "Как подготовиться к сезонному росту спроса",
        "summary": "Планирование закупок и оборотного капитала.",
        "body": (
            "Оцените сезонный спрос, составьте план закупок и "
            "сопоставьте даты платежей с поступлением выручки. "
            "Это синтетический демонстрационный материал."
        ),
        "category": "trade",
        "published_at": "2026-10-20T09:00:00Z",
    },
    {
        "id": 2,
        "title": "Как планировать покупку оборудования",
        "summary": "Подготовка бизнеса к модернизации производства.",
        "body": (
            "Сравните стоимость оборудования, сроки запуска и "
            "ожидаемую дополнительную выручку. Это "
            "синтетический демонстрационный материал."
        ),
        "category": "production",
        "published_at": "2026-10-19T09:00:00Z",
    },
    {
        "id": 3,
        "title": "Как оценить долговую нагрузку",
        "summary": "Почему полезно учитывать все действующие платежи.",
        "body": (
            "Составьте календарь платежей по действующим "
            "обязательствам и оцените резерв ликвидности. Это "
            "синтетический демонстрационный материал."
        ),
        "category": "finance",
        "published_at": "2026-10-18T09:00:00Z",
    },
    {
        "id": 4,
        "title": "Кассовые разрывы в строительстве",
        "summary": "Планирование платежей между этапами проекта.",
        "body": (
            "Учитывайте разницу между оплатой материалов и "
            "поступлением денег от заказчика. Это синтетический"
            " демонстрационный материал."
        ),
        "category": "construction",
        "published_at": "2026-10-17T09:00:00Z",
    },
]
