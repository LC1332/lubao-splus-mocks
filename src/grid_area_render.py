"""Drawing and Word layout for the grid-area worksheet."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

CELL, PAD, TOP = 66, 24, 48
YELLOW, TEAL, ORANGE = "#F5CB58", "#71C7C0", "#F2A45B"
INK = "#263746"


def font(size):
    for path in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
                 "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def xy(point):
    x, y = point
    return PAD + x * CELL, TOP + y * CELL


def draw_board(question, side, path):
    if side == "left":
        cols, rows = 7, 7
        im = Image.new("RGB", (PAD * 2 + cols * CELL, TOP + rows * CELL + PAD), "white")
        d = ImageDraw.Draw(im)
        for p in question["left"]["pieces"]:
            x, y = p["cell"]
            if p["kind"] == "square":
                verts = [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]
            else:
                tl, tr, br, bl = (x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)
                verts = ((tl, tr, br), (tl, tr, bl), (tl, br, bl), (tr, br, bl))[p["orientation"]]
            d.polygon([xy(v) for v in verts], fill=YELLOW)
    else:
        cols, rows = 8, 7
        im = Image.new("RGB", (PAD * 2 + cols * CELL, TOP + rows * CELL + PAD), "white")
        d = ImageDraw.Draw(im)
        tris = question["right"]["triangles"]
        palette = [TEAL] * 4 + [ORANGE]
        for tri, color in zip(tris, palette):
            d.polygon([xy(v) for v in tri], fill=color)
    d = ImageDraw.Draw(im)
    # Pink unit marker is separate from the countable figure.
    d.rectangle((PAD, TOP, PAD + CELL, TOP + CELL), fill="#F3B6CE")
    unit = question[f"{side}_unit"]
    f = font(36)
    box = d.textbbox((0, 0), str(unit), font=f)
    d.text((PAD + CELL // 2 - (box[2] - box[0]) // 2, TOP + CELL // 2 - (box[3] - box[1]) // 2 - box[1]), str(unit), fill="#1D2730", font=f)
    # Draw the entire grid on top so the lines remain visible within colored regions.
    for x in range(cols + 1):
        xx = PAD + x * CELL
        d.line((xx, TOP, xx, TOP + rows * CELL), fill="#303942", width=2)
    for y in range(rows + 1):
        yy = TOP + y * CELL
        d.line((PAD, yy, PAD + cols * CELL, yy), fill="#303942", width=2)
    im.save(path, dpi=(240, 240))


def _text_image(text, pt=11, bold=False, color=INK):
    dpi = 300
    f = font(round(pt * dpi / 72))
    pad = 10
    canvas = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    box = ImageDraw.Draw(canvas).textbbox((0, 0), text, font=f)
    w, h = box[2] - box[0] + pad * 2, box[3] - box[1] + pad * 2
    img = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    ImageDraw.Draw(img).text((pad - box[0], pad - box[1]), text, font=f, fill=color,
                             stroke_width=1 if bold else 0, stroke_fill=color)
    out = BytesIO()
    img.save(out, format="PNG", dpi=(dpi, dpi))
    out.seek(0)
    return out, w / dpi


def add_text(paragraph, text, pt=11, bold=False, color=INK):
    data, width = _text_image(text, pt, bold, color)
    run = paragraph.add_run()
    picture = run.add_picture(data, width=Inches(width))
    picture._inline.docPr.set("descr", text)


def cell_margins(cell, top=50, start=50, bottom=35, end=50):
    tcpr = cell._tc.get_or_add_tcPr()
    margins = tcpr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tcpr.append(margins)
    for edge, val in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")


def create_docx(questions, assets_dir, output):
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.top_margin, sec.bottom_margin = Inches(.42), Inches(.42)
    sec.left_margin, sec.right_margin = Inches(.56), Inches(.56)
    sec.header_distance = sec.footer_distance = Inches(.2)
    for i, q in enumerate(questions):
        if i % 2 == 0:
            if i:
                doc.add_page_break()
            title = doc.add_paragraph()
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title.paragraph_format.space_after = Pt(4)
            add_text(title, "方格中的图形面积与单位换算", 19, True)
            if i == 0:
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(5)
                add_text(p, "姓名：_______________　日期：_______________", 10)
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(1)
        add_text(p, f"{q['number']}．", 13, True, "#365B70")
        add_text(p, q["prompt"], 10.5)
        table = doc.add_table(rows=1, cols=2)
        table.autofit = False
        for col in range(2):
            table.columns[col].width = Inches(3.55)
            cell = table.cell(0, col)
            cell.width = Inches(3.55)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell_margins(cell)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            p.add_run().add_picture(str(assets_dir / f"q{q['number']:02d}_{('left' if col == 0 else 'right')}.png"), width=Inches(2.75 if col == 0 else 3.05))
            caption = cell.add_paragraph()
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
            caption.paragraph_format.space_after = Pt(0)
            add_text(caption, "表示（　　　　）", 10.5)

    doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(8)
    add_text(p, "参考答案", 19, True)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(8)
    add_text(p, "先数出图案占几个整格，再把半格拼成整格；最后乘以每格代表的数。右图五种颜色中的橙色部分也计入面积。", 10)
    for q in questions:
        left = q["left"]
        right = q["right"]
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(1)
        add_text(p, f"{q['number']}．左图：{left['squares']} 个整格 + {left['half_triangles']} 个半格 = {left['equivalent_cells']:g} 格；每格代表 {q['left_unit']}，表示 {left['answer']}。", 10.5)
        areas = "、".join(f"{a/2:g}" for a in right["triangle_area2"])
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        add_text(p, f"　右图：5 个三角形面积依次为 {areas} 格，合计 {right['equivalent_cells']:g} 格；每格代表 {q['right_unit']}，表示 {right['answer']}。", 10.5)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
