"""Formatting helpers for the runbook Word document (python-docx)."""
import re

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

NAVY = RGBColor(0x1F, 0x38, 0x64)
GREY = RGBColor(0x59, 0x59, 0x59)
CODE_FONT = "Consolas"
BODY_FONT = "Calibri"

CALLOUT = {
    "note": ("Note", "DEEAF6", "2E75B6"),
    "important": ("Important", "FFF2CC", "BF9000"),
    "caution": ("Caution", "FCE4D6", "C55A11"),
    "evidence": ("Evidence", "E2EFDA", "548235"),
    "decision": ("Decision", "E4DFEC", "7030A0"),
}


def _shade(element, fill):
    pr = element.get_or_add_tcPr() if hasattr(element, "get_or_add_tcPr") else element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def _cell_margins(tbl, top=60, bottom=60, left=90, right=90):
    tblPr = tbl._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)


def _borders(tbl, color="A6A6A6", size=4):
    tblPr = tbl._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        b.append(el)
    tblPr.append(b)


def _fix_grid(tbl, widths_cm):
    """LibreOffice lays tables out from tblGrid, Word from tcW; set both and a fixed layout."""
    tblPr = tbl._tbl.tblPr
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(int(sum(widths_cm) * 567)))
    tw.set(qn("w:type"), "dxa")
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    tblPr.append(tw)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    grid = tbl._tbl.tblGrid
    for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
        gc.set(qn("w:w"), str(int(widths_cm[i] * 567)))


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _no_split(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _field(paragraph, instr, placeholder="1"):
    run = paragraph.add_run()
    b = OxmlElement("w:fldChar")
    b.set(qn("w:fldCharType"), "begin")
    run._r.append(b)
    run = paragraph.add_run()
    t = OxmlElement("w:instrText")
    t.set(qn("xml:space"), "preserve")
    t.text = instr
    run._r.append(t)
    run = paragraph.add_run()
    s = OxmlElement("w:fldChar")
    s.set(qn("w:fldCharType"), "separate")
    run._r.append(s)
    paragraph.add_run(placeholder)
    run = paragraph.add_run()
    e = OxmlElement("w:fldChar")
    e.set(qn("w:fldCharType"), "end")
    run._r.append(e)


def _fld_char(paragraph, kind):
    run = paragraph.add_run()
    el = OxmlElement("w:fldChar")
    el.set(qn("w:fldCharType"), kind)
    run._r.append(el)
    return run


def _instr(paragraph, text):
    run = paragraph.add_run()
    t = OxmlElement("w:instrText")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    run._r.append(t)


def add_hyperlink(paragraph, url, text, size=None):
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), r_id)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "2E75B6")
    rPr.append(c)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rPr.append(u)
    if size:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(size * 2)))
        rPr.append(sz)
    r.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    h.append(r)
    paragraph._p.append(h)


LABEL = re.compile(r"\{ref:([a-z0-9_]+)\}")
INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[R\d+(?:, ?R\d+)*\])")


class Builder:
    def __init__(self, title, short_title, refs, known_labels=None):
        self.doc = Document()
        self.known_labels = known_labels or {}
        self.labels = {}
        self.title = title
        self.short_title = short_title
        self.refs = refs
        self.h = [0, 0, 0]
        self.app = None
        self.fig_no = 0
        self.tab_no = 0
        self.headings = []
        self.figures = []
        self.tables = []
        self.cited = set()
        self._styles()
        self._page_setup()

    # ---------- setup ----------
    def _styles(self):
        st = self.doc.styles
        normal = st["Normal"]
        normal.font.name = BODY_FONT
        normal.font.size = Pt(10.5)
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
        pf = normal.paragraph_format
        pf.space_after = Pt(6)
        pf.line_spacing = 1.12
        for lvl, size, before, after in ((1, 16, 0, 10), (2, 13, 14, 6), (3, 11.5, 10, 4)):
            s = st[f"Heading {lvl}"]
            s.font.name = BODY_FONT
            s.element.rPr.rFonts.set(qn("w:asciiTheme"), "")
            s.element.rPr.rFonts.set(qn("w:hAnsi"), BODY_FONT)
            s.element.rPr.rFonts.set(qn("w:ascii"), BODY_FONT)
            s.font.size = Pt(size)
            s.font.bold = True
            s.font.italic = False
            s.font.color.rgb = NAVY
            s.paragraph_format.space_before = Pt(before)
            s.paragraph_format.space_after = Pt(after)
            s.paragraph_format.keep_with_next = True
        for name in ("List Bullet", "List Bullet 2", "List Number"):
            s = st[name]
            s.font.name = BODY_FONT
            s.font.size = Pt(10.5)
            s.paragraph_format.space_after = Pt(3)
        fh = st.add_style("Front Heading", 1)
        fh.base_style = st["Normal"]
        fh.font.size = Pt(16)
        fh.font.bold = True
        fh.font.color.rgb = NAVY
        fh.paragraph_format.space_after = Pt(10)
        fh.paragraph_format.keep_with_next = True
        cap = st["Caption"]
        cap.font.name = BODY_FONT
        cap.font.size = Pt(9.5)
        cap.font.bold = True
        cap.font.italic = False
        cap.font.color.rgb = NAVY
        for lvl in (1, 2, 3):
            name = f"TOC {lvl}"
            try:
                s = st[name]
            except KeyError:
                s = st.add_style(name, 1)
            s.base_style = st["Normal"]
            s.font.size = Pt(10.5 if lvl == 1 else 10)
            s.font.bold = lvl == 1
            s.paragraph_format.left_indent = Cm(0.6 * (lvl - 1))
            s.paragraph_format.space_after = Pt(2 if lvl > 1 else 3)
            s.paragraph_format.space_before = Pt(5 if lvl == 1 else 0)
            s.paragraph_format.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

    def _page_setup(self):
        sec = self.doc.sections[0]
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.left_margin = sec.right_margin = Cm(2.2)
        sec.top_margin = Cm(2.3)
        sec.bottom_margin = Cm(2.0)
        sec.header_distance = Cm(1.0)
        sec.footer_distance = Cm(0.9)
        sec.different_first_page_header_footer = True
        hp = sec.header.paragraphs[0]
        hp.text = ""
        r = hp.add_run(self.short_title)
        r.font.size = Pt(8.5)
        r.font.color.rgb = GREY
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        self._bottom_border(hp)
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("Customer Confidential    |    Page ")
        r.font.size = Pt(8.5)
        r.font.color.rgb = GREY
        _field(fp, "PAGE")
        r = fp.add_run(" of ")
        r.font.size = Pt(8.5)
        r.font.color.rgb = GREY
        _field(fp, "NUMPAGES")
        for run in fp.runs:
            run.font.size = Pt(8.5)
            run.font.color.rgb = GREY

    @staticmethod
    def _bottom_border(p):
        pPr = p._p.get_or_add_pPr()
        b = OxmlElement("w:pBdr")
        bt = OxmlElement("w:bottom")
        bt.set(qn("w:val"), "single")
        bt.set(qn("w:sz"), "4")
        bt.set(qn("w:space"), "1")
        bt.set(qn("w:color"), "A6A6A6")
        b.append(bt)
        pPr.append(b)

    # ---------- text ----------
    def _resolve(self, text):
        def sub(m):
            key = m.group(1)
            if key in self.known_labels:
                return self.known_labels[key]
            return "Figure 00" if key.startswith("fig_") else "Table 00"
        return LABEL.sub(sub, text)

    def _runs(self, p, text, size=None, color=None, bold=False, italic=False):
        text = self._resolve(text)
        for part in INLINE.split(text):
            if not part:
                continue
            if part.startswith("**") and part.endswith("**"):
                r = p.add_run(part[2:-2])
                r.bold = True
            elif part.startswith("`") and part.endswith("`"):
                r = p.add_run(part[1:-1])
                r.font.name = CODE_FONT
                r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), CODE_FONT)
                r.font.size = Pt((size or 10.5) - 1)
                r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
            elif re.fullmatch(r"\[R\d+(?:, ?R\d+)*\]", part):
                ids = re.findall(r"R\d+", part)
                for i in ids:
                    if i not in self.refs:
                        raise KeyError(f"unknown reference {i}")
                    self.cited.add(i)
                r = p.add_run(part)
                r.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)
            else:
                r = p.add_run(part)
                if bold:
                    r.bold = True
            if size:
                r.font.size = Pt(size)
            if color is not None and not (part.startswith("[R")):
                r.font.color.rgb = color
            if italic:
                r.italic = True
        return p

    def p(self, text, style=None, size=None, align=None, bold=False, italic=False, color=None, after=None, keep=False):
        para = self.doc.add_paragraph(style=style)
        self._runs(para, text, size=size, color=color, bold=bold, italic=italic)
        if align == "center":
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if after is not None:
            para.paragraph_format.space_after = Pt(after)
        if keep:
            para.paragraph_format.keep_with_next = True
        return para

    def bullets(self, items, level=1):
        style = "List Bullet" if level == 1 else "List Bullet 2"
        for it in items:
            if isinstance(it, (list, tuple)):
                self.bullets(it, level=2)
            else:
                self.p(it, style=style)

    def steps(self, items):
        for i, it in enumerate(items, 1):
            para = self.doc.add_paragraph()
            para.paragraph_format.left_indent = Cm(0.75)
            para.paragraph_format.first_line_indent = Cm(-0.75)
            para.paragraph_format.space_after = Pt(3)
            para.paragraph_format.tab_stops.add_tab_stop(Cm(0.75))
            r = para.add_run(f"{i}.\t")
            r.bold = True
            self._runs(para, it)

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # ---------- headings ----------
    def h1(self, text, appendix=None):
        if appendix:
            self.app = appendix
            self.h = [0, 0, 0]
            num = f"Appendix {appendix}"
            label = f"{num}. {text}"
        else:
            self.h = [self.h[0] + 1, 0, 0]
            num = str(self.h[0])
            label = f"{num}  {text}"
        para = self.doc.add_paragraph(style="Heading 1")
        para.paragraph_format.page_break_before = True
        para.add_run(label)
        self.headings.append((1, label))
        return para

    def h2(self, text):
        self.h[1] += 1
        self.h[2] = 0
        prefix = self.app if self.app else str(self.h[0])
        label = f"{prefix}.{self.h[1]}  {text}"
        self.doc.add_paragraph(style="Heading 2").add_run(label)
        self.headings.append((2, label))

    def h3(self, text):
        self.h[2] += 1
        prefix = self.app if self.app else str(self.h[0])
        label = f"{prefix}.{self.h[1]}.{self.h[2]}  {text}"
        self.doc.add_paragraph(style="Heading 3").add_run(label)
        self.headings.append((3, label))

    # ---------- blocks ----------
    def callout(self, kind, text):
        title, fill, edge = CALLOUT[kind]
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _borders(tbl, color=edge, size=6)
        _cell_margins(tbl, 80, 80, 140, 140)
        _fix_grid(tbl, [16.6])
        _no_split(tbl.rows[0])
        cell = tbl.rows[0].cells[0]
        _shade(cell._tc, fill)
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(2)
        r = para.add_run(title + ". ")
        r.bold = True
        r.font.size = Pt(10)
        texts = text if isinstance(text, (list, tuple)) else [text]
        self._runs(para, texts[0], size=10)
        for t in texts[1:]:
            q = cell.add_paragraph()
            q.paragraph_format.space_after = Pt(2)
            self._runs(q, t, size=10)
        self._spacer()

    def _spacer(self, pts=4):
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(0)
        sp.paragraph_format.space_before = Pt(0)
        r = sp.add_run("")
        r.font.size = Pt(pts)
        sp.paragraph_format.line_spacing = Pt(pts)

    def code(self, text, title=None):
        if title:
            t = self.p(title, size=9, bold=True, color=GREY, after=2, keep=True)
        tbl = self.doc.add_table(rows=1, cols=1)
        _borders(tbl, color="BFBFBF", size=4)
        _cell_margins(tbl, 70, 70, 120, 120)
        _fix_grid(tbl, [16.6])
        cell = tbl.rows[0].cells[0]
        _shade(cell._tc, "F3F3F3")
        lines = text.strip("\n").split("\n")
        if len(lines) <= 60:
            _no_split(tbl.rows[0])
        para = cell.paragraphs[0]
        for i, line in enumerate(lines):
            if i:
                para = cell.add_paragraph()
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = 1.0
            r = para.add_run(line if line else " ")
            r.font.name = CODE_FONT
            r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), CODE_FONT)
            r.font.size = Pt(8)
        self._spacer()

    def table(self, headers, rows, widths=None, caption=None, size=9, first_col_bold=False, header_fill="1F3864", zebra=True, label=None):
        if caption:
            self.tab_no += 1
            if label:
                self.labels["tab_" + label] = f"Table {self.tab_no}"
            cap = self.doc.add_paragraph(style="Caption")
            cap.paragraph_format.keep_with_next = True
            cap.paragraph_format.space_before = Pt(4)
            cap.add_run(f"Table {self.tab_no}. {caption}")
            self.tables.append(f"Table {self.tab_no}. {caption}")
        tbl = self.doc.add_table(rows=1, cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        _borders(tbl)
        _cell_margins(tbl)
        total = 16.6
        if widths is None:
            widths = [total / len(headers)] * len(headers)
        else:
            s = sum(widths)
            widths = [w * total / s for w in widths]
        _fix_grid(tbl, widths)
        hdr = tbl.rows[0]
        _repeat_header(hdr)
        _no_split(hdr)
        for i, h in enumerate(headers):
            c = hdr.cells[i]
            c.width = Cm(widths[i])
            _shade(c._tc, header_fill)
            para = c.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            r = para.add_run(h)
            r.bold = True
            r.font.size = Pt(size)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for ri, row in enumerate(rows):
            cells = tbl.add_row()
            _no_split(cells)
            for i, val in enumerate(row):
                c = cells.cells[i]
                c.width = Cm(widths[i])
                if zebra and ri % 2 == 1:
                    _shade(c._tc, "F2F5FA")
                parts = val if isinstance(val, (list, tuple)) else [val]
                for k, part in enumerate(parts):
                    para = c.paragraphs[0] if k == 0 else c.add_paragraph()
                    para.paragraph_format.space_after = Pt(1)
                    para.paragraph_format.line_spacing = 1.0
                    self._runs(para, str(part), size=size, bold=(first_col_bold and i == 0))
        self._spacer(6)
        return tbl

    def figure(self, path, caption, source, width_cm=16.0, label=None):
        self.fig_no += 1
        if label:
            self.labels["fig_" + label] = f"Figure {self.fig_no}"
        para = self.doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.keep_with_next = True
        para.paragraph_format.space_after = Pt(2)
        para.add_run().add_picture(str(path), width=Cm(width_cm))
        cap = self.doc.add_paragraph(style="Caption")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.keep_with_next = True
        cap.paragraph_format.space_after = Pt(0)
        cap.add_run(f"Figure {self.fig_no}. {caption}")
        self.figures.append(f"Figure {self.fig_no}. {caption}")
        src = self.doc.add_paragraph()
        src.alignment = WD_ALIGN_PARAGRAPH.CENTER
        src.paragraph_format.space_after = Pt(10)
        self._runs(src, source, size=8.5, color=GREY, italic=True)

    # ---------- table of contents ----------
    def toc(self, entries, pages, title="Contents"):
        para = self.doc.add_paragraph(style="Front Heading")
        para.paragraph_format.page_break_before = True
        para.add_run(title)
        first = True
        for idx, (lvl, label) in enumerate(entries):
            q = self.doc.add_paragraph(style=f"TOC {lvl}")
            if first:
                _fld_char(q, "begin")
                _instr(q, ' TOC \\o "1-2" \\h \\z \\u ')
                _fld_char(q, "separate")
                first = False
            q.add_run(label.replace("  ", " ", 1) if lvl > 1 else label)
            q.add_run("\t" + str(pages.get(label, "")))
            if idx == len(entries) - 1:
                _fld_char(q, "end")

    def static_list(self, title, items, pages):
        para = self.doc.add_paragraph(style="Front Heading")
        para.paragraph_format.page_break_before = True
        para.add_run(title)
        for it in items:
            q = self.doc.add_paragraph(style="TOC 2")
            q.paragraph_format.left_indent = Cm(0)
            q.add_run(it)
            q.add_run("\t" + str(pages.get(it, "")))

    def save(self, path):
        self.doc.save(str(path))
