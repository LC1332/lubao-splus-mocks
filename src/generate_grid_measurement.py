#!/usr/bin/env python3
"""Generate a 12-question grid-length worksheet as an editable DOCX."""

from __future__ import annotations

import argparse
from io import BytesIO
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
CELL = 44
SCALE = 2
CANVAS_W, CANVAS_H = 760, 380
INK = (55, 67, 78)
PALETTE = ["#E8A94B", "#65A9A0", "#E98772", "#8199CC", "#9A83B7", "#A8A653"]
OBJECTS = ["杯子", "盘子", "书本", "橡皮", "饼干", "小鱼图形", "花盆", "肥皂", "手提包", "小汽车", "叶片图形", "蛋糕"]


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    choices = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for candidate in choices:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def px(x: float) -> int:
    return int(round(x * SCALE))


def create_spec(index: int) -> dict:
    # Each second measurement is 6-9 units, and its ruler is a cropped, nonzero section.
    first_length = 2 + index % 4
    first_start = 2 + (index * 3 % 6)
    second_length = 6 + index % 4
    second_start = 3 + (index * 2 % 5)
    first = {
        "length": first_length,
        "start": first_start,
        "end": first_start + first_length,
        "visible_start": 0,
        "visible_end": 12,
        "cropped": False,
    }
    second = {
        "length": second_length,
        "start": second_start,
        "end": second_start + second_length,
        "visible_start": max(1, second_start - 3),
        "visible_end": min(18, second_start + second_length + 3),
        "cropped": True,
    }
    assert first["end"] <= first["visible_end"]
    assert second["start"] > second["visible_start"]
    assert second["end"] < second["visible_end"]
    assert second_length > 5
    return {"number": index + 1, "first": first, "second": second}


def shape(draw: ImageDraw.ImageDraw, name: str, box: tuple[int, int, int, int], color: str) -> None:
    x0, y0, x1, y1 = box
    outline = "#596775"
    fill = color
    mid = (y0 + y1) // 2
    if name == "盘子":
        draw.ellipse(box, fill="#F5E9D6", outline=outline, width=px(2))
        draw.ellipse((x0 + px(9), y0 + px(10), x1 - px(9), y1 - px(10)), outline=fill, width=px(3))
    elif name == "杯子":
        # The widest left and right points are the side endpoints, exactly at x0/x1.
        pts = [(x0, mid - px(22)), (x0 + px(4), mid + px(17)),
               (x0 + px(18), y1 - px(2)), (x1 - px(18), y1 - px(2)),
               (x1 - px(4), mid + px(17)), (x1, mid - px(22)),
               (x1 - px(7), y0 + px(3)), (x0 + px(7), y0 + px(3))]
        draw.polygon(pts, fill=fill, outline=outline)
        draw.line((x0 + px(5), y0 + px(6), x1 - px(5), y0 + px(6)), fill="#FFFFFF", width=px(3))
    elif name in ("书本", "橡皮", "肥皂"):
        draw.rounded_rectangle(box, radius=px(7), fill=fill, outline=outline, width=px(2))
        draw.line((x0 + px(8), mid, x1 - px(8), mid), fill="#FFFFFF", width=px(2))
        if name == "书本":
            draw.line((x0 + px(14), y0 + px(7), x0 + px(14), y1 - px(7)), fill=outline, width=px(2))
    elif name == "小汽车":
        wheel_y = y1 - px(3)
        draw.rounded_rectangle((x0, mid - px(8), x1, wheel_y - px(6)), radius=px(10), fill=fill, outline=outline, width=px(2))
        draw.polygon([(x0 + px(12), mid - px(8)), (x0 + px(26), y0 + px(5)),
                      (x1 - px(19), y0 + px(5)), (x1 - px(5), mid - px(8))], fill=fill, outline=outline)
        draw.ellipse((x0 + px(12), wheel_y - px(7), x0 + px(28), wheel_y + px(9)), fill=outline)
        draw.ellipse((x1 - px(28), wheel_y - px(7), x1 - px(12), wheel_y + px(9)), fill=outline)
    elif name == "小鱼图形":
        # Use a bounded fish silhouette whose leftmost and rightmost points are its endpoints.
        draw.ellipse((x0, y0 + px(4), x1 - px(20), y1 - px(4)), fill=fill, outline=outline, width=px(2))
        draw.polygon([(x1 - px(20), mid), (x1, y0 + px(9)), (x1, y1 - px(9))], fill=fill, outline=outline)
        draw.ellipse((x0 + px(12), mid - px(4), x0 + px(20), mid + px(4)), fill=outline)
    elif name == "花盆":
        draw.polygon([(x0, y0 + px(4)), (x1, y0 + px(4)), (x1 - px(10), y1), (x0 + px(10), y1)], fill=fill, outline=outline)
        draw.line((x0 + px(3), y0 + px(10), x1 - px(3), y0 + px(10)), fill="#FFFFFF", width=px(2))
    elif name == "手提包":
        draw.rounded_rectangle((x0, mid - px(12), x1, y1 - px(1)), radius=px(9), fill=fill, outline=outline, width=px(2))
        draw.arc((x0 + px(18), y0, x1 - px(18), mid + px(6)), 180, 360, fill=outline, width=px(3))
    elif name == "叶片图形":
        draw.ellipse(box, fill=fill, outline=outline, width=px(2))
        draw.line((x0 + px(5), y1 - px(8), x1 - px(5), y0 + px(8)), fill="#FFFFFF", width=px(3))
    elif name == "蛋糕":
        draw.rectangle((x0, mid - px(14), x1, y1), fill=fill, outline=outline, width=px(2))
        draw.polygon([(x0, mid - px(14)), (x0 + px(13), y0), (x1, y0 + px(8)), (x1, mid - px(14))], fill="#F2D49A", outline=outline)
        draw.ellipse((x0 + px(10), y0 + px(3), x0 + px(19), y0 + px(12)), fill="#E98772")
    else:  # 饼干
        draw.ellipse(box, fill=fill, outline=outline, width=px(2))
        for ox, oy in ((.25, .35), (.49, .56), (.72, .33), (.68, .72), (.35, .72)):
            cx, cy = int(x0 + (x1 - x0) * ox), int(y0 + (y1 - y0) * oy)
            draw.ellipse((cx - px(3), cy - px(3), cx + px(3), cy + px(3)), fill="#875D43")


def draw_measurement(spec: dict, item_name: str, color: str, out_path: Path) -> None:
    im = Image.new("RGB", (px(CANVAS_W), px(CANVAS_H)), "white")
    d = ImageDraw.Draw(im)
    ruler_y, ruler_h = 286, 57
    view_start, view_end = spec["visible_start"], spec["visible_end"]
    xbase = (CANVAS_W - (view_end - view_start) * CELL) / 2
    x_for = lambda tick: px(xbase + (tick - view_start) * CELL)
    left, right = spec["start"], spec["end"]
    x0, x1 = x_for(left), x_for(right)
    top, bottom = px(87), px(230)
    shape(d, item_name, (x0, top, x1, bottom), color)

    # Endpoint guides share exact x coordinates with the silhouette extrema and ruler boundaries.
    for ex in (x0, x1):
        y = px(60)
        while y < px(ruler_y):
            d.line((ex, y, ex, min(y + px(9), px(ruler_y))), fill="#68727A", width=px(1.4))
            y += px(15)

    # Ruler board and grid boundaries; the count is the interval count between guides.
    ruler_box = (x_for(view_start), px(ruler_y), x_for(view_end), px(ruler_y + ruler_h))
    d.rounded_rectangle(ruler_box, radius=px(6), fill="#EAF2F8", outline="#7892A8", width=px(2))
    for tick in range(view_start, view_end + 1):
        tx = x_for(tick)
        d.line((tx, px(ruler_y), tx, px(ruler_y + ruler_h)), fill="#AABAC6", width=px(1))
    for tick in range(view_start, view_end):
        label = str(tick + 1)
        bbox = d.textbbox((0, 0), label, font=font(px(14)))
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        cx = (x_for(tick) + x_for(tick + 1)) // 2
        d.text((cx - tw // 2, px(ruler_y + 22) - th // 2), label, fill=INK, font=font(px(14)))

    if spec["cropped"]:
        # Distinctive zigzag crop edges sit outside the measured span.
        for edge, direction in ((x_for(view_start), 1), (x_for(view_end), -1)):
            yy = px(ruler_y + ruler_h // 2)
            d.line([(edge, yy - px(8)), (edge + direction * px(7), yy - px(3)),
                    (edge, yy + px(2)), (edge + direction * px(7), yy + px(7))], fill="#557996", width=px(2))

    caption = ImageDraw.Draw(im)
    txt = item_name
    bb = caption.textbbox((0, 0), txt, font=font(px(21)))
    caption.text((im.width // 2 - (bb[2] - bb[0]) // 2, px(22)), txt, fill=INK, font=font(px(21)))
    im.resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS).save(out_path, dpi=(240, 240))


def set_cell_margins(cell, top=30, start=25, bottom=20, end=25):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    margins = tcPr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tcPr.append(margins)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def add_rendered_text(paragraph, text: str, size_pt=11, bold=False, color="#263746"):
    """Insert crisp Chinese text as a high-resolution inline image.

    The worksheet remains editable in Word; this text image keeps Chinese
    glyphs intact in headless renderers that lack a CJK font fallback.
    """
    dpi = 300
    fnt = font(round(size_pt * dpi / 72))
    pad = round(dpi / 30)
    scratch = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    measure = ImageDraw.Draw(scratch)
    bbox = measure.textbbox((0, 0), text, font=fnt, stroke_width=0)
    width, height = bbox[2] - bbox[0] + pad * 2, bbox[3] - bbox[1] + pad * 2
    raster = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    ImageDraw.Draw(raster).text((pad - bbox[0], pad - bbox[1]), text, font=fnt,
                                fill=color, stroke_width=(1 if bold else 0), stroke_fill=color)
    data = BytesIO()
    raster.save(data, format="PNG", dpi=(dpi, dpi))
    data.seek(0)
    run = paragraph.add_run()
    picture = run.add_picture(data, width=Inches(width / dpi), height=Inches(height / dpi))
    picture._inline.docPr.set("descr", text)


def make_docx(specs: list[dict], assets_dir: Path, output: Path, with_answers: bool = True) -> None:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.top_margin, sec.bottom_margin = Inches(.48), Inches(.45)
    sec.left_margin, sec.right_margin = Inches(.62), Inches(.62)
    sec.header_distance, sec.footer_distance = Inches(.2), Inches(.2)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_after = Pt(1)
    add_rendered_text(title, "用格子测量物品长度", 20, True)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.paragraph_format.space_after = Pt(8)
    add_rendered_text(sub, "每一格表示 1 格长度。请看清物品两端，再数两条虚线之间的格子。", 10)

    for i, spec in enumerate(specs):
        if i and i % 2 == 0:
            doc.add_page_break()
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(1)
            add_rendered_text(p, "用格子测量物品长度", 18, True)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(7)
            add_rendered_text(p, "每一格表示 1 格长度。数一数两条虚线之间有几格。", 10)

        q = doc.add_paragraph()
        q.paragraph_format.space_before = Pt(7)
        q.paragraph_format.space_after = Pt(2)
        add_rendered_text(q, f"第 {spec['number']} 题　", 13, True, "#365B70")
        add_rendered_text(q, "量一量物品横向占了几格，写在括号里。", 11)
        table = doc.add_table(rows=1, cols=2)
        table.autofit = False
        table.columns[0].width = Inches(3.48)
        table.columns[1].width = Inches(3.48)
        for j, part in enumerate(("first", "second")):
            cell = table.cell(0, j)
            cell.width = Inches(3.48)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            image = assets_dir / f"q{spec['number']:02d}_{part}.png"
            p.add_run().add_picture(str(image), width=Inches(3.32))
            answer = cell.add_paragraph()
            answer.alignment = WD_ALIGN_PARAGRAPH.CENTER
            answer.paragraph_format.space_before = Pt(0)
            answer.paragraph_format.space_after = Pt(0)
            add_rendered_text(answer, "（　　　）格", 11)

    if with_answers:
        doc.add_page_break()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(10)
        add_rendered_text(p, "参考答案", 20, True)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(9)
        add_rendered_text(p, "长度看两条虚线之间的格数。尺子被截断时，也只数两个端点之间的间隔。", 11)
        t = doc.add_table(rows=1, cols=3)
        t.style = "Table Grid"
        headers = ["题号", "第一次测量", "第二次测量"]
        for c, label in zip(t.rows[0].cells, headers):
            c.text = ""
            add_rendered_text(c.paragraphs[0], label, 11, True)
        for spec in specs:
            cells = t.add_row().cells
            for cell, text in zip(cells, [str(spec["number"]), f"{spec['first']['length']} 格", f"{spec['second']['length']} 格"]):
                cell.text = ""
                add_rendered_text(cell.paragraphs[0], text, 11)

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261014, help="固定随机种子，默认 20261014")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "generated", help="输出目录，默认 generated")
    args = parser.parse_args()
    rng = random.Random(args.seed)
    out_dir = args.output_dir.expanduser().resolve()
    assets_dir = out_dir / "格子测量素材"
    assets_dir.mkdir(parents=True, exist_ok=True)

    specs = [create_spec(i) for i in range(12)]
    names = OBJECTS[:]
    rng.shuffle(names)
    colors = PALETTE[:]
    rng.shuffle(colors)
    for i, spec in enumerate(specs):
        for j, part in enumerate(("first", "second")):
            name = names[(i * 2 + j) % len(names)]
            color = colors[(i + j * 2) % len(colors)]
            spec[part]["object"] = name
            spec[part]["color"] = color
            image = assets_dir / f"q{spec['number']:02d}_{part}.png"
            draw_measurement(spec[part], name, color, image)
    answers = [
        {"question": s["number"], "first_length": s["first"]["length"], "second_length": s["second"]["length"],
         "first_object": s["first"]["object"], "second_object": s["second"]["object"]}
        for s in specs
    ]
    (assets_dir / "题目参数与答案.json").write_text(json.dumps({"seed": args.seed, "questions": specs, "answers": answers}, ensure_ascii=False, indent=2), encoding="utf-8")
    make_docx(specs, assets_dir, out_dir / "大班数学格子测量练习.docx")
    print(f"已生成：{out_dir / '大班数学格子测量练习.docx'}")
    print(f"题目：{len(specs)} 道；第二次测量答案：{[s['second']['length'] for s in specs]}")


if __name__ == "__main__":
    main()
