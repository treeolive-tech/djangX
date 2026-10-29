"""
ASGI config.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/asgi/
"""

from os import environ

from django.core.asgi import get_asgi_application

from .utils import settings_module

environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module())
application = get_asgi_application()
