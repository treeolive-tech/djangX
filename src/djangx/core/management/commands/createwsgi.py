"""``djx createwsgi``: create/remove `wsgi.py` and set/reset `WSGI_APPLICATION`.

Examples::

    djx createwsgi --set
    djx createwsgi --remove --reset
"""

from ...utils.commands import ServerFileCommand


class Command(ServerFileCommand):
    help = "Create or remove wsgi.py, and set or reset WSGI_APPLICATION."

    filename = "wsgi.py"
