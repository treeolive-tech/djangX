"""
WSGI config.

It exposes the WSGI callable as a module-level variable named ``app``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

from os import environ

from django.core.wsgi import get_wsgi_application

from .utils import DJANGO_SETTINGS_MODULE

assert DJANGO_SETTINGS_MODULE is not None
environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)
application = get_wsgi_application()
