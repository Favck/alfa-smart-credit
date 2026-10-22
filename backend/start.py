"""Простой старт демонстрационного стенда в Docker."""

import os
import sys

import django
from django.conf import settings
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

call_command("migrate", interactive=False)
if settings.DEMO_MODE:
    call_command("seed_demo")
os.execv(
    sys.executable,
    [sys.executable, "manage.py", "runserver", "0.0.0.0:8000", "--noreload"],
)
