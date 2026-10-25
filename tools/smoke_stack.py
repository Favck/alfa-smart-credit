"""Verify the compiled interface, PostgreSQL API and keyword fallback."""

import json
import re
import sys
import time
import urllib.request

base = sys.argv[1].rstrip("/")
token = ""


def call(path, data=None):
    request = urllib.request.Request(
        base + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": "Token " + token} if token else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read()


html = call("/").decode()
assert 'id="app"' in html
for path in re.findall(r'(?:src|href)="(/assets/[^"]+)"', html):
    assert call(path)
token = json.loads(call("/api/v1/auth/demo-login/", {"profile_id": "green"}))[
    "token"
]
assert len(json.loads(call("/api/v1/products/"))) == 4
for query, product in [
    ("Нечем платить зарплату завтра, клиент задерживает расчет", "overdraft"),
    ("Закупаем партию обуви на осенне-зимний сезон", "working_capital"),
    ("Открываем новую точку", "investment"),
    ("Купим станки и оборудование", "equipment_purchase"),
]:
    started = time.monotonic()
    result = json.loads(call("/api/v1/consultations/", {"user_query": query}))
    assert result["product"] == product and result["is_fallback"]
    assert time.monotonic() - started < 5.1
print(
    "PASS: three-service stack, compiled Vue, API, four rule-based product routes."
)
