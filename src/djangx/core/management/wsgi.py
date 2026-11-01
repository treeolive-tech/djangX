"""
WSGI config.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/
"""

from os import environ

from django.core.wsgi import get_wsgi_application

from ..utils.conf import settings_module

environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module())
application = get_wsgi_application()
