#!/usr/bin/env python
"""Convert src/hdf5_manager/icon.png to a Windows .ico file for PyInstaller.

Creates build/icon.ico with standard Windows icon sizes (16-256px).
The source image is centered on a transparent square canvas before
generating each resolution.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

SOURCE = Path("src/hdf5_manager/icon.png")
OUTPUT = Path("build/icon.ico")
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def _make_square(image: Image.Image, size: int) -> Image.Image:
    """Return a square RGBA thumbnail of *image* with transparent padding."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    image = image.copy()
    image.thumbnail((size, size), Image.LANCZOS)
    offset = ((size - image.width) // 2, (size - image.height) // 2)
    canvas.paste(image, offset, image if image.mode == "RGBA" else None)
    return canvas


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA")
    square = _make_square(source, max(ICO_SIZES))
    square.save(
        OUTPUT,
        format="ICO",
        sizes=[(size, size) for size in ICO_SIZES],
    )
    print(f"Wrote {OUTPUT} with sizes {ICO_SIZES}")


if __name__ == "__main__":
    main()
