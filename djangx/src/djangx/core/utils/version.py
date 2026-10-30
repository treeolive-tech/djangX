"""Version lookup utilities."""

from typing import Literal, NamedTuple, final

from .exit import ExitCode

__all__: list[str] = ["Version", "VersionResult", "print_version"]


class VersionResult(NamedTuple):
    """A version string paired with an error message (empty on success).

    Examples::

        output, error = Version.get("django")
        Version.get("django").output
    """

    output: str
    error: str


@final
class Version:
    """Namespace for looking up installed package versions.

    Examples::

        Version.get("django").output  # "5.1.0"
    """

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    @staticmethod
    def placeholder() -> Literal["X.Y.Z"]:
        """Return the placeholder used when a version cannot be found.

        Examples::

            Version.placeholder()  # "X.Y.Z"
        """
        return "X.Y.Z"

    @staticmethod
    def get(package: str) -> VersionResult:
        """Return the installed version of *package*, or a placeholder on failure.

        Examples::

            Version.get("django")             # VersionResult("5.1.0", "")
            Version.get("not-installed-pkg")  # VersionResult("X.Y.Z", "Package ... not installed ...")
        """
        try:
            from importlib.metadata import PackageNotFoundError, version

            return VersionResult(version(distribution_name=package), error="")
        except PackageNotFoundError:
            return VersionResult(
                output=Version.placeholder(),
                error=f"Package '{package}' is not installed or could not be found.",
            )
        except Exception as e:  # noqa: BLE001 - must always return a VersionResult
            return VersionResult(
                output=Version.placeholder(),
                error=f"Could not determine version for '{package}': {type(e).__name__}: {e}",
            )


def print_version(package: str) -> ExitCode:
    """Print the installed version of *package* and return an exit code.

    Examples::

        print_version("django")  # prints "5.1.0", returns ExitCode.SUCCESS
        print_version("nope")    # prints an error, returns ExitCode.ERROR
    """
    result: VersionResult = Version.get(package)

    if result.error:
        print(f"Could not determine version for package '{package}'.\n{result.error}")
        return ExitCode.ERROR
    else:
        print(result.output)
        return ExitCode.SUCCESS
