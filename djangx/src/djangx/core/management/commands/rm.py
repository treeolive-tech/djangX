import shutil
from pathlib import Path

from ...utils.commands import NonSystemCheckedCommand
from ...utils.console import Style, cprint
from ...utils.exit import ExitCode


class Command(NonSystemCheckedCommand):
    help = "Delete a file or folder from a directory."

    def add_arguments(self, parser) -> None:
        """Register `--file` or `--folder` (exactly one), `--dir`, `--recursive` and `--verbose`."""
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--file",
            dest="file_name",
            help="Name or relative path of the file to delete.",
        )
        group.add_argument(
            "--folder",
            dest="folder_name",
            help="Name or relative path of the folder to delete.",
        )

        parser.add_argument(
            "--dir",
            dest="base_dir",
            default=".",
            help="Base directory to search from (default: current working directory).",
        )
        parser.add_argument(
            "--recursive",
            action="store_true",
            help="Recursively search subdirectories for the target.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Print the path of each deleted file or folder.",
        )

    def handle(self, *args, **options) -> None:
        """Delete the matching file or folder; exit with `ExitCode.ERROR` on failure.

        Examples::

            djx rm --file app.log --dir logs
            djx rm --folder __pycache__ --recursive --verbose
        """
        base_dir = Path(options["base_dir"]).resolve()
        if not base_dir.is_dir():
            cprint(f"Directory not found: {base_dir}", Style.ERROR)
            raise SystemExit(ExitCode.ERROR)

        target = options["file_name"] or options["folder_name"]
        targets = self._resolve_targets(base_dir, target, options["recursive"])

        if options["file_name"]:
            deleted = self._delete_files(targets, options["verbose"])
            target_kind = "file"
        else:
            deleted = self._delete_folders(targets, options["verbose"])
            target_kind = "folder"

        if deleted == 0:
            suffix = " recursively" if options["recursive"] else ""
            cprint(
                f"No matching {target_kind} found for '{target}' in {base_dir}{suffix}.",
                Style.WARNING,
            )
            raise SystemExit(ExitCode.ERROR)

        cprint(f"✓ Deleted {deleted} {target_kind}(s).", Style.SUCCESS)

    def _resolve_targets(
        self, base_dir: Path, target: str, recursive: bool
    ) -> list[Path]:
        """Return existing paths matching `target`; a sub-path is never searched for.

        Examples::

            self._resolve_targets(base, "logs/app.log", True)  # [base / "logs/app.log"]
            self._resolve_targets(base, "__pycache__", True)  # every __pycache__ under base
            self._resolve_targets(base, "__pycache__", False)  # only base / "__pycache__"
        """
        if recursive and len(Path(target).parts) == 1:
            return [path for path in base_dir.rglob(target) if path.exists()]

        candidate = (base_dir / target).resolve()
        return [candidate] if candidate.exists() else []

    def _delete_files(self, paths: list[Path], verbose: bool) -> int:
        """Unlink each file or symlink in `paths` and return how many were deleted.

        Examples::

            self._delete_files([Path("a.log"), Path("b.log")], verbose=False)  # 2
        """
        deleted = 0
        for path in paths:
            if (
                path.is_file() or path.is_symlink()
            ):  # is_file() is False for dangling links
                path.unlink()
                if verbose:
                    cprint(f"Deleted file: {path}", Style.INFO)
                deleted += 1
        return deleted

    def _delete_folders(self, paths: list[Path], verbose: bool) -> int:
        """Remove each folder in `paths`, deepest first, and return how many were deleted.

        Examples::

            self._delete_folders([Path("a"), Path("a/b")], verbose=False)  # 2 ("a/b" goes first)
        """
        deleted = 0
        # Deepest first, so a parent's rmtree doesn't remove a child still in the list.
        for path in sorted(paths, key=lambda p: len(p.parts), reverse=True):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
                if verbose:
                    cprint(f"Deleted folder: {path}", Style.INFO)
                deleted += 1
        return deleted
