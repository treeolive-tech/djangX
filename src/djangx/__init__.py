from pathlib import Path
from typing import Final


class Package:
    name: Final[str] = Path(__file__).resolve().parent.name  # djangx
    verbose_name: Final[str] = name[:-1] + name[-1].upper()  # djangX
    core: Final[str] = f"{name}.core"
    components: Final[str] = f"{name}.components"
