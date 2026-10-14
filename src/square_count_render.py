"""Render retained square cells as clean yellow grids."""
from pathlib import Path
from PIL import Image, ImageDraw


def draw_grid(matrix: list[list[int]], path: Path, cell_px: int = 96, dpi: int = 300) -> None:
    cells = [(r, c) for r, row in enumerate(matrix) for c, value in enumerate(row) if value]
    if not cells:
        raise ValueError("不能绘制空图形")
    r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
    c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
    pad = 24
    width, height = (c1 - c0 + 1) * cell_px + 2 * pad, (r1 - r0 + 1) * cell_px + 2 * pad
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    segments = set()
    for r, c in cells:
        x0, y0 = pad + (c - c0) * cell_px, pad + (r - r0) * cell_px
        draw.rectangle((x0, y0, x0 + cell_px, y0 + cell_px), fill="#FFD84D")
        segments.update({((r, c), (r, c + 1)), ((r + 1, c), (r + 1, c + 1)),
                         ((r, c), (r + 1, c)), ((r, c + 1), (r + 1, c + 1))})
    for a, b in segments:
        ar, ac = a
        br, bc = b
        x1, y1 = pad + (ac - c0) * cell_px, pad + (ar - r0) * cell_px
        x2, y2 = pad + (bc - c0) * cell_px, pad + (br - r0) * cell_px
        draw.line((x1, y1, x2, y2), fill="#1A1A1A", width=4)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, dpi=(dpi, dpi), optimize=True)
