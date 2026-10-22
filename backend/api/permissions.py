from rest_framework.permissions import BasePermission

from .demo_data import PROFILES


def get_profile(user):
    if not user.is_authenticated:
        return None
    return next(
        (p for p in PROFILES if user.username == f"demo_{p['id']}"), None
    )


class IsClient(BasePermission):
    message = "Операция доступна только клиенту."

    def has_permission(self, request, view):
        profile = get_profile(request.user)
        return bool(profile and profile["role"] == "client")


class IsBank(BasePermission):
    message = "Операция доступна только сотруднику банка."

    def has_permission(self, request, view):
        profile = get_profile(request.user)
        return bool(profile and profile["role"] == "bank")
