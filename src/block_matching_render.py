"""Draw target diagrams and isometric unit-cube options with Pillow."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

INK = "#35404A"
UNIT = 54


def _font(size: int):
    for path in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
                 "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _save(im: Image.Image, path: Path) -> None:
    # Supersample the clean vector-like line art for sharp placement in Word.
    im = im.resize((im.width * 3, im.height * 3), Image.Resampling.LANCZOS)
    im.save(path, dpi=(300, 300), optimize=True)


def draw_floor(cells: list[list[int]], out: Path) -> None:
    cells_set = {tuple(p) for p in cells}
    max_x = max(x for x, _ in cells_set)
    max_y = max(y for _, y in cells_set)
    im = Image.new("RGB", (max_x * UNIT + 116, (max_y + 1) * UNIT + 132), "white")
    d = ImageDraw.Draw(im)
    ox, oy = 50, 30
    for x, y in cells_set:
        x0, y0 = ox + x * UNIT, oy + (max_y - y) * UNIT
        d.rectangle((x0, y0, x0 + UNIT, y0 + UNIT), fill="#D8AC72", outline="#765536", width=3)
        d.line((x0 + 8, y0 + 12, x0 + UNIT - 8, y0 + 12), fill="#C7955B", width=2)
        d.line((x0 + 12, y0 + 38, x0 + UNIT - 11, y0 + 38), fill="#E8C38C", width=2)
    cx = ox + (max_x + 1) * UNIT / 2
    base = oy + (max_y + 1) * UNIT + 17
    d.line((cx, base + 3, cx, base + 31), fill=INK, width=3)
    d.polygon([(cx, base + 36), (cx - 7, base + 24), (cx + 7, base + 24)], fill=INK)
    d.text((cx - 20, base + 37), "前方", font=_font(20), fill=INK)
    _save(im, out)


def draw_wall(cells: list[list[int]], out: Path) -> None:
    cell_set = {tuple(p) for p in cells}
    max_x = max(x for x, _ in cell_set)
    max_z = max(z for _, z in cell_set)
    cell = 48
    cols, rows = max_x + 1, max_z + 1
    margin = 26
    wall_cols, wall_rows = cols + 2, rows + 1
    im = Image.new("RGB", (wall_cols * cell + margin * 2, wall_rows * cell + margin * 2 + 38), "white")
    d = ImageDraw.Draw(im)
    # Build the wall from orange unit bricks around the exact white opening.
    for row in range(wall_rows):
        for col in range(wall_cols):
            x0, y0 = margin + col * cell, margin + row * cell
            d.rectangle((x0, y0, x0 + cell, y0 + cell), fill="#E8B45E", outline="#A56E37", width=2)
            d.line((x0 + 5, y0 + 12, x0 + cell - 5, y0 + 12), fill="#F2CC84", width=2)
    for x, z in cell_set:
        col, row = x + 1, rows - z
        x0, y0 = margin + col * cell, margin + row * cell
        d.rectangle((x0, y0, x0 + cell, y0 + cell), fill="white", outline="#704D32", width=3)
    ground_y = margin + wall_rows * cell
    d.line((margin - 4, ground_y, margin + wall_cols * cell + 4, ground_y), fill=INK, width=3)
    d.text((margin + cell, ground_y + 8), "左侧", font=_font(15), fill=INK)
    _save(im, out)


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _shade(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * factor))) for c in color)


PAINT = {"红": "#E4584F", "黄": "#F2C94C", "蓝": "#4D8FD6"}


def draw_option(matrix: tuple[tuple[int, ...], ...], cube_colors: dict[tuple[int, int, int], str], out: Path) -> None:
    cubes = {(x, y, z) for y, row in enumerate(matrix) for x, h in enumerate(row) for z in range(h)}
    u = 47
    dx, dy, dz = u, 34, 47
    depth_slope = .78
    xs = [x * dx + y * dy for x, y, _ in cubes]
    ys = [-z * dz - y * dy * depth_slope for _, y, z in cubes]
    pad = 36
    # Every option shares one fixed 4-by-2-by-3 drawing field, so Word's
    # common display width preserves exactly the same unit-cube size.
    width = 4 * dx + dy + 2 * pad
    height = 3 * dz + dy * depth_slope + 2 * pad
    im = Image.new("RGB", (int(width), int(height)), "white")
    d = ImageDraw.Draw(im)
    content_width = max(xs) - min(xs) + dx
    base_x = pad + (width - 2 * pad - content_width) / 2 - min(xs)
    base_y = height - pad
    # Painter's order: rear/deeper and lower blocks are drawn first. Shared faces are omitted.
    for x, y, z in sorted(cubes, key=lambda p: (-p[1], p[2], p[0])):
        base_color = _rgb(PAINT[cube_colors[(x, y, z)]])
        px, py = base_x + x * dx + y * dy, base_y - z * dz - y * dy * depth_slope
        p = (px, py)
        top = [(px, py - dz), (px + dx, py - dz),
               (px + dx + dy, py - dz - dy * depth_slope), (px + dy, py - dz - dy * depth_slope)]
        front = [p, (px + dx, py), (px + dx, py - dz), (px, py - dz)]
        right = [(px + dx, py), (px + dx + dy, py - dy * depth_slope),
                 (px + dx + dy, py - dy * depth_slope - dz), (px + dx, py - dz)]
        edge = "#39434C"
        if (x, y, z + 1) not in cubes:
            d.polygon(top, fill=_shade(base_color, 1.18), outline=edge)
        if (x, y - 1, z) not in cubes:
            d.polygon(front, fill=_shade(base_color, .92), outline=edge)
        if (x + 1, y, z) not in cubes:
            d.polygon(right, fill=_shade(base_color, .72), outline=edge)
    _save(im, out)
