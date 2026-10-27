__all__: list[str] = ["HELP_COMMANDS", "PROJECT_COMMANDS", "SCRIPT_COMMANDS"]

HELP_COMMANDS: set[str] = {"help", "-h"}

SCRIPT_COMMANDS: set[str] = {"cp", "platform", "random", "rm"}

PROJECT_COMMANDS: set[str] = {"compile_scss", "runserver"}
