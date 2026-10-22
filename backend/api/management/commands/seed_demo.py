from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from api.demo_data import PROFILES


class Command(BaseCommand):
    help = (
        "Создать три синтетических клиентских профиля и "
        "одного андеррайтера. Без регистрации и паролей."
    )

    def handle(self, *args, **options):
        if not settings.DEMO_MODE:
            raise CommandError(
                "Для создания демо-пользователей включите DEMO_MODE=true."
            )
        for profile in PROFILES:
            user, created = get_user_model().objects.get_or_create(
                username=f"demo_{profile['id']}",
                defaults={
                    "first_name": profile["name"],
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            if created or user.has_usable_password():
                user.set_unusable_password()
                user.save(update_fields=["password"])
            self.stdout.write(
                f"{profile['id']}: {'created' if created else 'exists'}"
            )
        self.stdout.write(self.style.SUCCESS("Демо-профили готовы."))
