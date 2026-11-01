"""``djx createdeploy``: create or remove the `deploy.yml` GitHub workflow.

Examples::

    djx createdeploy
    djx createdeploy --remove
"""

from pathlib import Path

from django.conf import settings

from ...utils.commands import FileCommand

DEPLOY_YML: str = """\
name: Build deploy branch

on:
  push:
    branches: [main]

permissions:
  contents: write

jobs:
  deploy-branch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - uses: astral-sh/setup-uv@07a047e608db84b3d8c06cd9a7c7dcc9c355c18e # v10.3.2
        with:
          enable-cache: false

      - name: Generate manage.py, asgi.py and wsgi.py, and point settings at them
        run: |
          uv run djx createmanage --overwrite
          uv run djx createasgi --overwrite --set
          uv run djx createwsgi --overwrite --set

      - name: Push to the deploy branch
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git switch -C deploy
          git add -f manage.py app/asgi.py app/wsgi.py app/settings.py
          git commit --allow-empty -m "Deploy build of ${GITHUB_SHA::7}"
          git push --force origin deploy
"""


class Command(FileCommand):
    help = "Create or remove the deploy.yml GitHub workflow."

    filename = "deploy.yml"
    template = DEPLOY_YML

    def default_dir(self) -> Path:
        return settings.BASE_DIR / ".github" / "workflows"
