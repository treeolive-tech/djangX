# ramani: src/djangx/contrib/sass/types.py
from typing import Literal

__all__: list[str] = ["BootstrapIncludesType"]

type BootstrapIncludesType = list[str] | Literal["__all__"] | None
