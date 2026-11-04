# ramani: src/djangx/__init__.py
from pathlib import Path

PKG_DIR: Path = Path(__file__).resolve().parent

PKG_NAME: str = PKG_DIR.name

PKG_VERBOSE_NAME: str = PKG_NAME[:-1] + PKG_NAME[-1].upper()
