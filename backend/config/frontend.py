"""Serve the compiled cabinet from the backend image."""

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect


def index(request):
    path = settings.FRONTEND_ROOT / "index.html"
    if not path.is_file():
        return HttpResponseRedirect("/api/docs/")
    response = HttpResponse(
        path.read_bytes(), content_type="text/html; charset=utf-8"
    )
    response["Cache-Control"] = "no-cache, no-store"
    return response
