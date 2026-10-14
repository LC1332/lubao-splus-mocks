"""Pillow board rendering and DOCX assembly for adjacent-number Sudoku."""
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


def _font(size: int):
    for path in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
                 "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_board(question: dict, path: Path, answer: bool = False) -> None:
    size, margin = 720, 48
    cell = (size - 2 * margin) // 4
    x0 = y0 = margin
    image = Image.new("RGB", (size, size), "#F4EBD6")
    draw = ImageDraw.Draw(image)
    grid = question["solution"]
    # Regular grid first, with no 2x2-box emphasis.
    for i in range(5):
        pos = margin + i * cell
        width = 6 if i in (0, 4) else 4
        draw.line((pos, margin, pos, margin + 4 * cell), fill="#222222", width=width)
        draw.line((margin, pos, margin + 4 * cell, pos), fill="#222222", width=width)
    # Red marks are centered on shared edges. LR describes neighboring cells,
    # so it is drawn vertically; UD is drawn horizontally.
    red = "#D32F2F"
    line_width = 15
    for r in range(4):
        for c in range(3):
            if question["left_right_red"][r][c]:
                x = x0 + (c + 1) * cell
                y1, y2 = y0 + r * cell + 5, y0 + (r + 1) * cell - 5
                draw.line((x, y1, x, y2), fill=red, width=line_width)
    for r in range(3):
        for c in range(4):
            if question["up_down_red"][r][c]:
                y = y0 + (r + 1) * cell
                x1, x2 = x0 + c * cell + 5, x0 + (c + 1) * cell - 5
                draw.line((x1, y, x2, y), fill=red, width=line_width)
    given = question["given"]
    font = _font(94)
    for r in range(4):
        for c in range(4):
            if not answer and (r != given["row"] or c != given["column"]):
                continue
            value = str(grid[r][c]) if answer else str(given["value"])
            box = draw.textbbox((0, 0), value, font=font, stroke_width=1)
            tw, th = box[2] - box[0], box[3] - box[1]
            x = x0 + c * cell + (cell - tw) / 2 - box[0]
            y = y0 + r * cell + (cell - th) / 2 - box[1] - 2
            draw.text((x, y), value, font=font, fill="#111111", stroke_width=1, stroke_fill="#111111")
    # Restore crisp boundaries where multiple red marks meet at intersections.
    # The shortened red endpoints preserve adjacent edge identity.
    image.save(path, format="PNG", dpi=(300, 300), optimize=True)


def _set_east_asia(run, name="宋体"):
    run.font.name = "Arial"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def _text(paragraph, text: str, size=10, bold=False):
    # Rasterize Chinese labels and instructions so the worksheet remains legible
    # in Word/LibreOffice environments that do not have a CJK font installed.
    dpi = 300
    font = _font(round(size * dpi / 72))
    max_width = round(6.95 * dpi)
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, current = [], ""
    for char in text:
        candidate = current + char
        if current and measure.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    spacing = max(3, round(size * dpi / 72 * .32))
    scratch = Image.new("RGBA", (max_width, max(1, len(lines) * (font.size + spacing) + 8)), (255, 255, 255, 0))
    draw = ImageDraw.Draw(scratch)
    y = 2
    for line in lines:
        draw.text((2, y), line, font=font, fill="#000000",
                  stroke_width=(1 if bold else 0), stroke_fill="#000000")
        y += font.size + spacing
    bbox = scratch.getbbox()
    if bbox:
        scratch = scratch.crop((0, 0, max(1, bbox[2] + 2), max(1, bbox[3] + 2)))
    stream = BytesIO()
    scratch.save(stream, format="PNG", dpi=(dpi, dpi))
    stream.seek(0)
    run = paragraph.add_run()
    pic = run.add_picture(stream, width=Inches(scratch.width / dpi), height=Inches(scratch.height / dpi))
    pic._inline.docPr.set("descr", text)
    return run


def _set_cell_margins(cell, top=0, start=70, bottom=0, end=70):
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = OxmlElement("w:tcMar")
    for edge, val in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        margins.append(node)
    tc_pr.append(margins)


def _no_borders(table):
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), "nil")
        borders.append(node)
    table._tbl.tblPr.append(borders)


def _add_question(doc: Document, q: dict, assets: Path):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(1)
    _text(p, f"第 {q['number']} 题", 14, True)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.05
    _text(p, "游戏规则：请把 1、2、3、4 填入空格，每行、每列数字不重复；标有红色线的两个格子里的数字是相邻数，没标红色线的两个格子里的数字不是相邻数。", 9.5)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    _text(p, "相邻数是相差 1 的两个数，如 1 和 2、2 和 3、3 和 4；1 和 4 不是相邻数。红线规则只检查上下、左右共用一条边的两个格子。", 9.5)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(3)
    pic = p.add_run().add_picture(str(assets / f"q{q['number']:02d}.png"), width=Inches(2.3), height=Inches(2.3))
    pic._inline.docPr.set("descr", f"第{q['number']}题，4乘4相邻数棋盘")


def make_docx(questions: list[dict], assets: Path, path: Path) -> None:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.top_margin, sec.bottom_margin = Inches(.43), Inches(.43)
    sec.left_margin, sec.right_margin = Inches(.62), Inches(.62)
    sec.header_distance, sec.footer_distance = Inches(.2), Inches(.2)

    # Exactly two cohesive puzzle blocks per page.
    for page_start in range(0, len(questions), 2):
        if page_start:
            doc.add_page_break()
        if page_start == 0:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(1)
            _text(p, "4×4 数独与相邻数练习", 19, True)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(4)
            _text(p, "姓名：____________　　日期：____________", 10)
        for q in questions[page_start:page_start + 2]:
            _add_question(doc, q, assets)

    # Answers begin on a fresh page; four answer boards fit per page.
    doc.add_page_break()
    for idx, q in enumerate(questions):
        if idx and idx % 4 == 0:
            doc.add_page_break()
        if idx % 4 == 0:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(5)
            _text(p, "参考答案", 19, True)
        table = doc.add_table(rows=1, cols=2)
        table.autofit = False
        table.columns[0].width = Inches(1.0)
        table.columns[1].width = Inches(2.0)
        _no_borders(table)
        label, board = table.cell(0, 0), table.cell(0, 1)
        label.width, board.width = Inches(1.0), Inches(2.0)
        label.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        board.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _set_cell_margins(label)
        _set_cell_margins(board)
        p = label.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        _text(p, f"第 {q['number']} 题", 11, True)
        p = board.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        pic = p.add_run().add_picture(str(assets / f"q{q['number']:02d}_answer.png"), width=Inches(1.55), height=Inches(1.55))
        pic._inline.docPr.set("descr", f"第{q['number']}题完整答案，含相邻约束红线")
        if idx % 4 != 3 and idx != len(questions) - 1:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.line_spacing = Pt(4)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
