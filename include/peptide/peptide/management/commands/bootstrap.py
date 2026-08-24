"""
Single-process startup bootstrap: migrate + clearsessions + optional
superuser creation.

start.sh used to shell out to three separate `python manage.py ...`
invocations for this, each paying its own interpreter start + django.setup()
cost on a single-vCPU container. Folding them into one command means that
cost is paid once, and it's paid regardless of whether
DJANGO_SUPERUSER_USERNAME/PASSWORD are set (the superuser check itself is
now just an ORM query inside a process that's already up, not a whole extra
`manage.py shell` invocation).
"""
import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run startup migrations, clear expired sessions, and ensure the configured superuser exists."

    def handle(self, *args, **options):
        self.stdout.write("Running database migrations...")
        try:
            call_command("migrate", "--run-syncdb", interactive=False)
        except Exception as exc:
            self.stderr.write(f"WARNING: Migrations failed: {exc}")

        call_command("clearsessions")

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if username and password:
            User = get_user_model()
            if not User.objects.filter(username=username).exists():
                self.stdout.write("Creating superuser...")
                User.objects.create_superuser(
                    username, os.environ.get("DJANGO_SUPERUSER_EMAIL", ""), password
                )
                self.stdout.write("Superuser created successfully")
            else:
                self.stdout.write("Superuser already exists")
