from django.http import JsonResponse


def health_check(request):
    """Return a lightweight process health response."""

    return JsonResponse({"status": "ok"})
