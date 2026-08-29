from django.http import HttpResponse


class HealthCheckMiddleware:
    """Answer the Container Apps health probe before host validation runs.

    ACA's probe agent sends its requests with ``Host: 100.100.1.254`` (the
    in-cluster probe address), which is not in ``ALLOWED_HOSTS``. Django's
    host check in ``HttpRequest.get_host()`` -- reached via CommonMiddleware /
    SecurityMiddleware / CsrfViewMiddleware -- then returns HTTP 400
    ``DisallowedHost``, so the probe never goes green and the revision is
    marked ``ActivationFailed``. This burned a deploy on 2026-08-28.

    Ordered first in MIDDLEWARE so ``/health/`` short-circuits here, before any
    code touches ``get_host()``. Everything else falls through untouched.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == '/health/':
            return HttpResponse('ok', content_type='text/plain')
        return self.get_response(request)
