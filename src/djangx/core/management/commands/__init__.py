from pathlib import Path

BUILTIN_COMMANDS: set[str] = {
    path.stem
    for path in Path(__file__).resolve().parent.glob("*.py")
    if path.name != "__init__.py"
}

HELP_COMMANDS: set[str] = {"help", "-h"}
