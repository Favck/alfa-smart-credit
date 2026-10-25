"""Validate the imported fixture before activating PostgreSQL."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("fixture")

    def handle(self, *args, **options):
        records = json.loads(Path(options["fixture"]).read_text())
        for label, expected in Counter(r["model"] for r in records).items():
            actual = apps.get_model(label).objects.count()
            if actual != expected:
                raise CommandError(f"Import count mismatch: {label}")
        for record in records:
            if record["model"] == "auth.user":
                fields = record["fields"]
                user = get_user_model().objects.get(
                    username=fields["username"]
                )
                if user.pk != record["pk"]:
                    raise CommandError("Imported user ID mismatch")
                if user.password != fields["password"]:
                    raise CommandError("Imported password hash mismatch")
        Document = apps.get_model("api", "Document")
        for document in Document.objects.all().iterator():
            if (
                hashlib.sha256(bytes(document.content)).hexdigest()
                != document.sha256
            ):
                raise CommandError("Imported document hash mismatch")
        self.stdout.write(
            "Legacy users, counts, password hashes and documents verified."
        )
