"""Food picture and Word layout helpers."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


PALETTE = ["#F7B8AA", "#B9DDF4", "#F8D979", "#C8E5B7", "#D7C4F1", "#F3C4D8", "#A9D9CE", "#F2C18C"]


def cjk_font(size: int):
    for path in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
                 "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _center(draw, xy, text, font, fill="#202020"):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((xy[0] - (box[2] - box[0]) / 2, xy[1]), text, font=font, fill=fill)


def _food_icon(draw, center, category: str, index: int, color: str):
    x, y = center
    # Distinct, clean food pictograms drawn locally; no network or emoji assets.
    if any(k in category for k in ("饮", "汁", "酸奶")):
        draw.rounded_rectangle((x-30, y-39, x+30, y+35), radius=10, fill="#FFFFFF", outline="#5B6470", width=3)
        draw.rounded_rectangle((x-26, y-1, x+26, y+31), radius=5, fill=color)
        draw.rectangle((x-19, y-44, x+19, y-37), fill="#FFFFFF", outline="#5B6470", width=3)
        draw.line((x+9, y-39, x+18, y-60), fill="#5B6470", width=4)
        draw.ellipse((x-9, y+5, x+9, y+23), fill="#FFFFFF")
    elif any(k in category for k in ("蛋糕", "甜点", "松饼", "派", "挞")):
        draw.polygon([(x-40,y+26),(x+39,y+26),(x+25,y-8),(x-27,y-8)], fill=color, outline="#664C48")
        draw.rectangle((x-34,y+26,x+33,y+40), fill="#F4D2AA", outline="#664C48", width=2)
        draw.arc((x-36,y-29,x+36,y+2), 180, 360, fill="#FFFFFF", width=12)
        draw.ellipse((x-7,y-37,x+7,y-23), fill="#D95752")
    elif any(k in category for k in ("面包", "点心", "能量")):
        draw.rounded_rectangle((x-41,y-25,x+41,y+31), radius=23, fill=color, outline="#805A3B", width=3)
        for dx in (-18, 0, 18):
            draw.arc((x+dx-5,y-14,x+dx+6,y+9), 185, 340, fill="#FFF4D8", width=3)
    elif any(k in category for k in ("三明治", "主食", "小菜", "水果")):
        draw.rounded_rectangle((x-39,y-31,x+39,y+31), radius=9, fill="#F2D6A4", outline="#725843", width=3)
        draw.rectangle((x-32,y-8,x+32,y+12), fill=color)
        draw.line((x-31,y-13,x+31,y-13), fill="#67965B", width=8)
        draw.line((x-31,y+16,x+31,y+16), fill="#D68C63", width=5)
    else:
        draw.ellipse((x-34,y-34,x+34,y+34), fill=color, outline="#725843", width=3)
        draw.arc((x-23,y-22,x+23,y+22), 10, 300, fill="#FFF1CC", width=4)
    # Small decorative mark changes each variation without encoding price.
    mark_x = x + (index % 3 - 1) * 9
    draw.ellipse((mark_x-4,y+44,mark_x+4,y+52), fill="#F08B69")


def draw_question(q: dict, path: Path) -> None:
    width, height = 1600, 610
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    label_font, item_font, price_font = cjk_font(30), cjk_font(25), cjk_font(31)
    groups = (q["group_a"], q["group_b"])
    for row, group in enumerate(groups):
        y0 = 14 + row * 296
        draw.text((30, y0), f"{group['category']}：", fill="#25344A", font=label_font)
        items = group["items"]
        left, right = 200, width - 24
        cell_w = (right - left) / len(items)
        for i, item in enumerate(items):
            cx = round(left + (i + .5) * cell_w)
            top = y0 + 47
            draw.rounded_rectangle((round(left+i*cell_w+8), top, round(left+(i+1)*cell_w-8), y0+283),
                                   radius=20, fill="#FCFCFD", outline="#E5E8ED", width=2)
            _food_icon(draw, (cx, top+82), group["category"], i, PALETTE[(i + row * 3 + q["number"]) % len(PALETTE)])
            _center(draw, (cx, top+153), item["name"], item_font)
            _center(draw, (cx, top+202), f"{item['price']} 元", price_font, "#173D72")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, dpi=(220, 220))


def _set_font(run, size: float, bold: bool = False):
    run.font.name = "Arial"
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "宋体")
    run.font.size = Pt(size)
    run.bold = bold


def _add_text(paragraph, text: str, size: float, bold: bool = False):
    # Embed rasterized CJK text for reliable display on machines without Chinese fonts.
    dpi = 300
    font = cjk_font(round(size * dpi / 72))
    pad = round(dpi / 36)
    scratch = Image.new("RGBA", (8, 8), (255, 255, 255, 0))
    measure = ImageDraw.Draw(scratch)
    max_width = round(dpi * 6.55)
    lines, current = [], ""
    for piece in re.findall(r"\d+|.", text):
        candidate = current + piece
        if current and measure.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = piece
        else:
            current = candidate
    if current:
        lines.append(current)
    display = "\n".join(lines)
    box = measure.multiline_textbbox((0, 0), display, font=font, spacing=round(size * dpi / 100))
    w, h = max(1, box[2]-box[0]+2*pad), max(1, box[3]-box[1]+2*pad)
    raster = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    ImageDraw.Draw(raster).multiline_text((pad-box[0],pad-box[1]),display,font=font,fill="#171717",spacing=round(size*dpi/100))
    stream = BytesIO()
    raster.save(stream, format="PNG", dpi=(dpi,dpi))
    stream.seek(0)
    run = paragraph.add_run()
    run.add_picture(stream, width=Inches(w/dpi), height=Inches(h/dpi))
    return run


def _cell_text(cell, text: str, size: float, bold: bool = False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    _add_text(p, text, size, bold)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _shade(cell, color: str):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    cell._tc.get_or_add_tcPr().append(shd)


def _no_table_borders(table):
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "D8DEE8")
        borders.append(el)
    table._tbl.tblPr.append(borders)


def _witness_text(q: dict) -> tuple[str, str]:
    by_id = {i["id"]: i for g in (q["group_a"],q["group_b"]) for i in g["items"]}
    dw = q["duplicate_price_witness"]
    one = by_id[dw["item_ids"][0]]["name"]
    two = by_id[dw["item_ids"][1]]["name"]
    pw = q["equal_difference_witness"]
    items = [by_id[pw[k]] for k in ("x_high_id", "y_low_id", "x_low_id", "y_high_id")]
    diff = pw["difference"]
    cross = f"{items[0]['name']} {items[0]['price']}元 + {items[1]['name']} {items[1]['price']}元 = " \
            f"{items[2]['name']} {items[2]['price']}元 + {items[3]['name']} {items[3]['price']}元 = {pw['equal_total']}元；"
    cross += f"两组对应单价都相差 {diff} 元。"
    return f"{one}和{two}单价相同，搭配同一项时会重复得到相同总价。", cross


def make_docx(questions: list[dict], assets: Path, output: Path) -> None:
    doc = Document()
    title_style_ppr = doc.styles["Title"]._element.get_or_add_pPr()
    for border in title_style_ppr.findall(qn("w:pBdr")):
        title_style_ppr.remove(border)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.top_margin, sec.bottom_margin = Inches(.52), Inches(.52)
    sec.left_margin, sec.right_margin = Inches(.65), Inches(.65)
    sec.header_distance = sec.footer_distance = Inches(.25)
    for index, q in enumerate(questions):
        if index % 2 == 0 and index:
            doc.add_page_break()
        if index == 0:
            p = doc.add_paragraph()
            p.style = doc.styles["Title"]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(4)
            _add_text(p, "食物搭配与不同总价", 20, True)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(8)
            _add_text(p, "姓名：________________　日期：________________", 11)
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        row = table.rows[0]
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        cell = row.cells[0]
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(2)
        _add_text(p, f"{q['number']}．{q['prompt']}", 12, True)
        p = cell.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        pic = p.add_run().add_picture(str(assets / f"q{q['number']:02d}.png"), width=Inches(6.75))
        pic._inline.docPr.set("descr", f"第{q['number']}题：{q['group_a']['category']}与{q['group_b']['category']}商品和价格")
        p = cell.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_after = Pt(4)
        _add_text(p, "（　　　　）种", 13)
        if index % 2 == 0:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)

    doc.add_page_break()
    for index, q in enumerate(questions):
        if index % 2 == 0 and index:
            doc.add_page_break()
        if index == 0:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(8)
            _add_text(p, "参考答案", 20, True)
        kind = "明确询问不同总价" if q["question_type"] == "distinct_totals" else "保留原题问法：不同价格的搭配方法"
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(3)
        _add_text(p, f"第 {q['number']} 题（{kind}）：{q['answer']} 种。商品搭配共有 {q['product_pairing_count']} 种（辅助数量）。", 10.5, True)

        ga, gb = q["group_a"], q["group_b"]
        table = doc.add_table(rows=1+len(ga["items"]), cols=1+len(gb["items"]))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        _no_table_borders(table)
        _cell_text(table.cell(0,0), f"{ga['category']} / {gb['category']}", 8.5, True)
        _shade(table.cell(0,0), "E9EFF8")
        for j, b in enumerate(gb["items"],1):
            _cell_text(table.cell(0,j), f"{b['name']}（{b['price']}元）", 8.5, True)
            _shade(table.cell(0,j), "E9EFF8")
        for i,a in enumerate(ga["items"],1):
            _cell_text(table.cell(i,0), f"{a['name']}（{a['price']}元）", 8.5, True)
            _shade(table.cell(i,0), "F3F6FA")
            for j,b in enumerate(gb["items"],1):
                _cell_text(table.cell(i,j), f"{a['price']}+{b['price']}={a['price']+b['price']}", 9)

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(1)
        _add_text(p, "总价从小到大：" + "、".join(f"{t}元" for t in q["distinct_totals"]), 9.5)
        one, two = _witness_text(q)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        _add_text(p, "同价商品例子：" + one, 9.5)
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        _add_text(p, "不同单价也得到同一总价：" + two, 9.5)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
