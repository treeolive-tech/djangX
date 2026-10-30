"""Copy a file, a directory or plain text (to the clipboard)."""

from os.path import expandvars
from pathlib import Path
from shutil import copy2, copytree, rmtree
from typing import TypeAlias

from .console import Style, cprint

__all__: list[str] = ["copy"]

_PathLike: TypeAlias = str | Path


def copy(
    source: _PathLike, destination: _PathLike | None = None, verbose: bool = True
) -> bool:
    """Copy a file or directory to `destination`, or text to the clipboard if it is omitted.

    Returns ``True`` on success; errors are printed and return ``False``. An existing
    destination directory is replaced only after a ``y`` at the prompt.

    Examples::

        copy("hello world")  # True (text copied to clipboard)
        copy("/tmp/file.txt", "/backup/file.txt")  # True
        copy("/tmp/mydir", "/backup/mydir", verbose=False)  # True, no success message
        copy("/missing", "/backup/x")  # False
    """
    if destination is None:
        return _clipboard_copy(str(source), verbose=verbose)

    src = _resolve_path(source)
    dst = _resolve_path(destination)

    if src.is_file():
        kind = "file"
    elif src.is_dir():
        kind = "directory"
    else:
        problem = (
            "is neither a file nor a directory" if src.exists() else "does not exist"
        )
        cprint(f"Source path {problem}: {src}", Style.ERROR)
        return False

    try:
        if kind == "file":
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy2(src, dst)
        else:
            if dst.exists():
                if not _prompt_overwrite(dst):
                    cprint("Copy aborted.", Style.WARNING)
                    return False
                rmtree(dst)
            copytree(src, dst)
    except PermissionError:
        cprint(
            "Permission denied. Check read/write permissions for source and destination.",
            Style.ERROR,
        )
        return False
    except Exception as e:  # noqa: BLE001  # report any failure, don't crash the caller
        cprint(f"Failed to copy {kind}: {type(e).__name__}: {e}", Style.ERROR)
        return False

    if verbose:
        cprint(
            [
                (f"✓ {kind.capitalize()} copied successfully from ", Style.SUCCESS),
                (str(src), Style.HIGHLIGHT),
                (" to ", Style.SUCCESS),
                (str(dst), Style.HIGHLIGHT),
            ]
        )
    return True


def _resolve_path(value: _PathLike) -> Path:
    """Expand environment variables and ``~``, then resolve a filesystem path."""
    return Path(expandvars(str(value))).expanduser().resolve()


def _prompt_overwrite(destination: Path) -> bool:
    """Ask whether to overwrite `destination`; only an explicit ``y`` means yes.

    Examples::

        _prompt_overwrite(Path("backup"))  # True if the user types "y", else False
    """
    cprint(f"\n{destination} already exists.", Style.WARNING)
    return input("Overwrite? [y/N]: ").strip().lower() == "y"


def _clipboard_copy(text: str, verbose: bool = True) -> bool:
    """Copy `text` to the clipboard with ``pyperclip`` (Linux also needs ``xclip`` or ``xsel``).

    Examples::

        _clipboard_copy("hello")  # True
    """
    try:
        import pyperclip

        pyperclip.copy(text)
    except ImportError:
        cprint("pyperclip is not installed. Run: pip install pyperclip", Style.ERROR)
        return False
    except Exception as e:  # noqa: BLE001  # report any failure, don't crash the caller
        cprint(f"Failed to copy to clipboard: {type(e).__name__}: {e}", Style.ERROR)
        return False

    if verbose:
        cprint([("✓ Copied to clipboard: ", Style.SUCCESS), (text, Style.HIGHLIGHT)])
    return True
