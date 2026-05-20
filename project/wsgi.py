"""
WSGI config for project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

import django
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')


def run_startup_tasks():
    if os.environ.get("RUN_STARTUP_TASKS", "false").lower() != "true":
        return

    # Render free plans do not execute pre-deploy commands, so we bootstrap the
    # schema and demo catalog during process startup.
    django.setup()
    call_command("migrate", interactive=False, verbosity=0)
    call_command("seed_initial_data", verbosity=0)


run_startup_tasks()
application = get_wsgi_application()
