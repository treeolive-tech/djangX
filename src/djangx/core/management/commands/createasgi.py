# ramani: src/djangx/core/management/commands/createasgi.py
"""``djx createasgi``: create/remove `asgi.py` and set/reset `ASGI_APPLICATION`.

Examples::

    djx createasgi --set
    djx createasgi --remove --reset
"""

from ...apps import CoreConfig
from ...utils.commands import ServerFileCommand


class Command(ServerFileCommand):
    help = "Create or remove asgi.py, and set or reset ASGI_APPLICATION."

    filename = "asgi.py"
    template_file = CoreConfig.resources / "templates" / "createfile" / "asgi.py-tpl"
