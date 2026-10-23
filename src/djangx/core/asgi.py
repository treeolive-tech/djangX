"""
ASGI config.

It exposes the ASGI callable as a module-level variable named ``app``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

from os import environ

from django.core.asgi import get_asgi_application

from .utils import DJANGO_SETTINGS_MODULE

assert DJANGO_SETTINGS_MODULE is not None
environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)
application = get_asgi_application()
