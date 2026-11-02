"""Build paper/main.docx from paper/main.tex:  python paper/docx/build_docx.py   (needs pandoc 3.x and python-docx; MiKTeX only for the figure PNGs).

1. prepare.py: pandoc friendly copy of main.tex, figure PNGs, the [VERIFY] notes as a Lua table.
2. pandoc with citeproc and the IEEE CSL style (paper/ieee.csl) and filter.lua: numbered sections, figures and tables, highlighted markers, comments.
3. python-docx: Times New Roman 10 pt, IEEE like headings and captions, red highlight on Pending runs, yellow on Todo runs, table rules, and a two
   column body after the abstract (title, authors, abstract and keywords stay one column).
"""
import copy
import os
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).parent
PAPER = HERE.parent
BUILD = HERE / "_build"
OUT = PAPER / "main.docx"
PANDOC = Path.home() / "AppData/Local/Pandoc/pandoc.exe"

subprocess.run([sys.executable, "-I", str(HERE / "prepare.py")], check=True)
env = dict(os.environ, VERIFY_NOTES=str(BUILD / "verify_notes.lua"))
raw = BUILD / "pandoc_out.docx"
subprocess.run(
    [str(PANDOC), "-s", "-f", "latex", "main_docx.tex", "-o", str(raw), "--citeproc", "--bibliography", str(PAPER / "refs.bib"),
     "--csl", str(PAPER / "ieee.csl"), "--lua-filter", str(HERE / "filter.lua"), "--resource-path", str(BUILD)],
    check=True, cwd=BUILD, env=env,
)

doc = Document(str(raw))
styles = doc.styles


def set_font(style, size, bold=None, italic=None, caps=None, color=None):
    f = style.font
    f.name = "Times New Roman"
    f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if caps is not None:
        f.small_caps = caps
    f.color.rgb = color or RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), "Times New Roman")
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]


for name in ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text", "Bibliography"):
    if name in [s.name for s in styles]:
        set_font(styles[name], 10)
for name in ("Body Text", "First Paragraph"):
    if name in [s.name for s in styles]:
        pf = styles[name].paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.space_before = Pt(0)
        pf.space_after = Pt(4)
set_font(styles["Title"], 22, bold=False)
styles["Title"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
for name in ("Author", "Date"):
    if name in [s.name for s in styles]:
        set_font(styles[name], 11)
        styles[name].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
for name in ("Abstract", "Abstract Title"):
    if name in [s.name for s in styles]:
        set_font(styles[name], 9, bold=True)
        styles[name].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
set_font(styles["Heading 1"], 10, bold=False, caps=True)
styles["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
styles["Heading 1"].paragraph_format.space_before = Pt(10)
styles["Heading 1"].paragraph_format.space_after = Pt(4)
set_font(styles["Heading 2"], 10, bold=False, italic=True)
styles["Heading 2"].paragraph_format.space_before = Pt(6)
styles["Heading 2"].paragraph_format.space_after = Pt(3)
for name in ("Image Caption", "Table Caption", "Caption"):
    if name in [s.name for s in styles]:
        set_font(styles[name], 8)
        styles[name].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
for name in ("Pending", "Todo"):
    if name not in [s.name for s in styles]:
        continue

# the custom character styles that the filter created
for st in styles:
    if st.name == "Pending":
        st.font.bold = True
        st.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    if st.name == "Todo":
        st.font.bold = True


def mark_runs(par_iter):
    red = yellow = 0
    for p in par_iter:
        for r in p.runs:
            sname = r.style.name if r.style is not None else ""
            if sname == "Pending":
                r.font.highlight_color = WD_COLOR_INDEX.RED
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.bold = True
                red += 1
            elif sname == "Todo":
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
                r.font.bold = True
                yellow += 1
    return red, yellow


def all_paragraphs(d):
    for p in d.paragraphs:
        yield p
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    yield p


red, yellow = mark_runs(all_paragraphs(doc))

# table rules like the IEEE tables: a line above and below the header and at the bottom, small font, centered
for t in doc.tables:
    tbl = t._tbl
    pr = tbl.tblPr
    for old in pr.findall(qn("w:tblBorders")):
        pr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for side, val in (("top", "single"), ("bottom", "single"), ("insideH", "nil"), ("left", "nil"), ("right", "nil"), ("insideV", "nil")):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:val"), val)
        e.set(qn("w:sz"), "6")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "000000")
        borders.append(e)
    pr.append(borders)
    for i, row in enumerate(t.rows):
        for c in row.cells:
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.size = Pt(8)
                if i == 0:
                    tcpr = c._tc.get_or_add_tcPr()
                    b = OxmlElement("w:tcBorders")
                    bt = OxmlElement("w:bottom")
                    bt.set(qn("w:val"), "single")
                    bt.set(qn("w:sz"), "6")
                    bt.set(qn("w:space"), "0")
                    bt.set(qn("w:color"), "000000")
                    b.append(bt)
                    tcpr.append(b)

# pictures at one column width
for shape in doc.inline_shapes:
    ratio = shape.height / shape.width
    shape.width = Inches(3.35)
    shape.height = int(Inches(3.35) * ratio)

# page: US Letter, IEEE margins; body in two columns after the Index Terms paragraph
body = doc.element.body
final = body.find(qn("w:sectPr"))
for tag, attrs in (("w:pgSz", {"w:w": "12240", "w:h": "15840"}), ("w:pgMar", {"w:top": "1080", "w:bottom": "1440", "w:left": "900", "w:right": "900", "w:header": "720", "w:footer": "720", "w:gutter": "0"})):
    e = final.find(qn(tag))
    if e is None:
        e = OxmlElement(tag)
        final.append(e)
    for k, v in attrs.items():
        e.set(qn(k), v)
for old in final.findall(qn("w:cols")):
    final.remove(old)
cols = OxmlElement("w:cols")
cols.set(qn("w:num"), "2")
cols.set(qn("w:space"), "360")
final.append(cols)

target = None
for p in doc.paragraphs:
    if p.text.startswith("Index Terms"):
        target = p
        break
if target is not None:
    sect = copy.deepcopy(final)
    for c in sect.findall(qn("w:cols")):
        sect.remove(c)
    one = OxmlElement("w:cols")
    one.set(qn("w:num"), "1")
    sect.append(one)
    typ = OxmlElement("w:type")
    typ.set(qn("w:val"), "continuous")
    sect.insert(0, typ)
    # the first section ends here: the sectPr describes the section that ENDS with this paragraph
    for t in sect.findall(qn("w:type")):
        sect.remove(t)
    target._p.get_or_add_pPr().append(sect)
    # the second (final) section starts on the same page
    ftype = final.find(qn("w:type"))
    if ftype is None:
        ftype = OxmlElement("w:type")
        final.insert(0, ftype)
    ftype.set(qn("w:val"), "continuous")

doc.save(str(OUT))
print(f"written {OUT}; highlighted runs: {red} pending (red), {yellow} todo (yellow)")
