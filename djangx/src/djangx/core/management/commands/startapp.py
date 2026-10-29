import re
from contextlib import suppress
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import CommandError
from django.core.management.commands.startapp import Command as StartAppCommand


class Command(StartAppCommand):
    help = "Create an app in `APP_DIR` with its AppConfig `name` set to `<APP_DIR name>.<app name>`."

    def handle(self, **options: Any) -> None:
        """Create `APP_DIR/<name>` from Django's app template, then prefix the AppConfig `name`.

        Examples::

            djx startapp blog  # app/blog/ is created and apps.py has name = "app.blog"
            djx startapp blog elsewhere  # CommandError: apps are always created in app/
        """
        prefix: str = settings.APP_DIR.name
        if options["directory"]:
            raise CommandError(
                f"Apps are always created in {prefix}/; omit the directory."
            )

        target: Path = settings.APP_DIR / options["name"]
        target.mkdir(parents=True, exist_ok=True)  # Django needs the folder to exist
        try:
            super().handle(**{**options, "directory": str(target)})
        except CommandError:
            with suppress(OSError):
                target.rmdir()  # only removes the folder if it is still empty
            raise

        apps_py = target / "apps.py"
        apps_py.write_text(
            re.sub(
                r"^([ \t]+name = ['\"])",
                rf"\g<1>{prefix}.",
                apps_py.read_text(),
                count=1,
                flags=re.MULTILINE,
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"Created {prefix}.{options['name']} in {target}")
        )
