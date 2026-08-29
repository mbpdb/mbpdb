"""Gunicorn config: access logging for Container Apps traffic analysis.

Loaded explicitly via `gunicorn -c gunicorn.conf.py` in start.sh.

Why: Container Apps has no ingress access logs enabled and Django logs no
requests, so there is currently no way to tell what wakes the container from
scale-to-zero (~37 cold starts/day). This ships per-request lines to stdout,
which Container Apps forwards to Log Analytics (ContainerAppConsoleLogs_CL).

The real client IP arrives as X-Forwarded-For from nginx; gunicorn's own
%(h)s would only ever show 127.0.0.1.
"""

import logging

accesslog = "-"   # stdout
errorlog = "-"    # stderr
access_log_format = (
    '%({x-forwarded-for}i)s "%(r)s" %(s)s %(b)s %(M)sms '
    'ref="%(f)s" ua="%(a)s"'
)


class _SkipHealthCheck(logging.Filter):
    """Drop access-log lines for /health/.

    The ACA startup and readiness probes hit /health/ every 3-10s; logging
    every one would add ~20k noise lines/day and bury the traffic we want to
    characterise.
    """

    def filter(self, record):
        return "/health/" not in record.getMessage()


def post_worker_init(worker):
    # Added here (not on_starting) so it lands on the logger after gunicorn has
    # finished configuring logging in the worker process.
    logging.getLogger("gunicorn.access").addFilter(_SkipHealthCheck())
