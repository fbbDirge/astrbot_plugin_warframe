"""Resolve full-source PNGs or compact, offline market artwork."""
from pathlib import Path

def image_path(path):
    path=Path(path)
    if path.is_file():return path
    compact=path.with_suffix('.webp')
    return compact if compact.is_file() else path
