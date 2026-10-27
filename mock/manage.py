"""Vercel reads this for the settings module. For development, run `djangx` or `djx` instead."""

from os import environ

from django.core.asgi import get_asgi_application
from django.core.wsgi import get_wsgi_application
from djangx.core.utils import DJANGO_SETTINGS_MODULE

assert DJANGO_SETTINGS_MODULE is not None
environ.setdefault(key="DJANGO_SETTINGS_MODULE", value=DJANGO_SETTINGS_MODULE)

asgi = get_asgi_application()
wsgi = get_wsgi_application()

if __name__ == "__main__":
    from sys import argv

    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)
