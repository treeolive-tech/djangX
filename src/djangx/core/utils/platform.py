"""Platform and architecture detection utilities."""

from platform import machine, system
from typing import Final

__all__: list[str] = ["Platform"]


class Platform:
    """Detect the current OS and CPU architecture as normalised codes.

    Raises:
        OSError: If the OS is unsupported.
        ValueError: If the CPU architecture is unsupported.

    Examples::

        p = Platform()
        str(p)           # "macos-arm64"
        p.os_name        # "macos"
        p.architecture   # "arm64"
    """

    _PLATFORM_MAP: Final[dict[str, str]] = {
        "darwin": "macos",
        "linux": "linux",
        "windows": "windows",
        "android": "android",
    }

    _ARCH_MAP: Final[dict[str, str]] = {
        "x86_64": "x64",
        "amd64": "x64",
        "x64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
        "armv8": "arm64",
        "armv7l": "arm",
        "armv7": "arm",
        "armv6l": "arm",
    }

    def __init__(self) -> None:
        """Detect the current OS and architecture and store them on the instance."""
        self.os_name: str = self._detect_os()
        self.architecture: str = self._detect_architecture()

    def _detect_os(self) -> str:
        """Normalise :func:`platform.system`, e.g. ``"Darwin"`` -> ``"macos"``."""
        system_platform: str = system().lower()
        platform_name: str | None = self._PLATFORM_MAP.get(system_platform)
        if not platform_name:
            supported: str = ", ".join(dict.fromkeys(self._PLATFORM_MAP.values()))
            raise OSError(
                f"Unsupported operating system: {system_platform}. Supported: {supported}"
            )
        return platform_name

    def _detect_architecture(self) -> str:
        """Normalise :func:`platform.machine`, e.g. ``"aarch64"`` -> ``"arm64"``."""
        machine_platform: str = machine().lower()
        architecture: str | None = self._ARCH_MAP.get(machine_platform)
        if not architecture:
            supported: str = ", ".join(dict.fromkeys(self._ARCH_MAP.values()))
            raise ValueError(
                f"Unsupported architecture: {machine_platform}. Supported: {supported}"
            )
        return architecture

    def __str__(self) -> str:
        """Return ``"<os_name>-<architecture>"``.

        Examples::

            str(Platform())    # "linux-x64"
            f"{Platform()}"    # "macos-arm64"
            print(Platform())  # windows-x64
        """
        return f"{self.os_name}-{self.architecture}"
