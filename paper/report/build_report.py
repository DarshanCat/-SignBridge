"""Build paper/report/SignBridge_Project_Report.docx from the chapter files in paper/report/content/ and the figures in paper/report/figures/.

    python paper/report/build_report.py            build the Word file, update its fields (table of contents, lists of figures and tables) with Word and
                                                   export a PDF to count the pages. Needs python-docx; Word only for the field update (use --no-word to skip it).

Content markup (one block per paragraph, blank lines between blocks):
    # Chapter title            ## Section            ### Subsection          (chapters are numbered automatically)
    plain paragraph            - bullet               1. numbered item        ``` fenced code ```
    ![Caption text](figures/file.png){#fig:id w=5.5}                           a figure with its caption below
    Table: Caption text {#tab:id}  followed by a pipe table (header, separator, rows)
    Inline: **bold**  *italic*  `code`  [@bibkey; @otherkey]  [[fig:id]] [[tab:id]]
            {{PENDING}} or {{P:text}}      red bold marker for a number that waits for the three-seed runs
            {{3s:key}}                     value from docs/evaluation/three_seed_summary.json if that file has the key, else the red PENDING marker
            {{j:file.json:path.to.value:fmt}}   a number read from docs/evaluation/file.json (so the text cannot drift from the result files)
Rule checked at build time: no em dash and no double hyphen outside code blocks.
"""
import copy
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
EV = ROOT / "docs" / "evaluation"
CONTENT = HERE / "content"
OUT = HERE / "SignBridge_Project_Report.docx"
TODAY = datetime.date.today().strftime("%d %B %Y").lstrip("0")
RED = RGBColor(0xC0, 0x00, 0x00)
USE_WORD = "--no-word" not in sys.argv

THREE_SEED = json.load(open(EV / "three_seed_summary.json")) if (EV / "three_seed_summary.json").is_file() else {}
_json_cache: dict = {}


# ------------------------------------------------------------------ bibliography
def tex_clean(s: str) -> str:
    rep = {r"\textendash": "-", r"{\"e}": "\u00eb", r"{\~n}": "\u00f1", r"{\'e}": "\u00e9", r"{\'E}": "\u00c9"}
    for a, b in rep.items():
        s = s.replace(a, b)
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    return s.replace("{", "").replace("}", "").strip()


def parse_bib(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    entries = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, flags=re.S):
        kind, key, body = m.group(1).lower(), m.group(2).strip(), m.group(3)
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}", body):
            fields[fm.group(1).lower()] = fm.group(2).strip()
        entries[key] = (kind, fields)
    return entries


def initials(name: str) -> str:
    parts = tex_clean(name).split()
    if parts and parts[-1] in ("III", "Jr."):
        suffix = parts.pop()
    else:
        suffix = ""
    i = len(parts) - 1
    while i > 0 and parts[i - 1][:1].islower():  # van, de
        i -= 1
    last = " ".join(parts[i:]) + (" " + suffix if suffix else "")
    first = " ".join(p[0] + "." for p in parts[:i] if p)
    return f"{first} {last}".strip()


def authors_ieee(raw: str) -> str:
    names = [n.strip() for n in raw.split(" and ")]
    others = names and names[-1] == "others"
    if others:
        names = names[:-1]
    names = [initials(n) for n in names]
    if others or len(names) > 6:
        return names[0] + " et al."
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + (", and " if len(names) > 2 else " and ") + names[-1]


def format_ref(kind: str, f: dict):
    """list of (text, italic) runs in IEEE style"""
    year = f.get("year", "")
    pages = tex_clean(f.get("pages", ""))
    title = tex_clean(f.get("title", ""))
    runs = []
    who = authors_ieee(f["author"]) if "author" in f else (authors_ieee(f["editor"]) + ", Eds." if "editor" in f else "")
    if kind == "inproceedings":
        runs = [(f"{who}, \u201c{title},\u201d in ", False), (tex_clean(f["booktitle"]), True), (f", {year}" + (f", pp. {pages}" if pages else "") + ".", False)]
    elif kind == "article":
        j = tex_clean(f["journal"])
        tail = (f", vol. {f['volume']}" if "volume" in f else "") + (f", no. {f['number']}" if "number" in f else "") + (f", pp. {pages}" if pages else "") + f", {year}."
        runs = [(f"{who}, \u201c{title},\u201d ", False), (j, True), (tail, False)]
    elif kind == "book":
        runs = [(f"{who}, ", False), (title, True), (f". {tex_clean(f.get('publisher', ''))}, {year}.", False)]
    else:  # misc
        runs = [(f"{title}. {tex_clean(f.get('howpublished', ''))}, {year}.", False)]
    if f.get("doi"):
        runs.append((f" doi: {f['doi']}", False))
    return runs


BIB = parse_bib(HERE.parent / "refs.bib")
cited: list[str] = []


def cite_number(key: str) -> int:
    if key not in BIB:
        raise SystemExit(f"citation key {key} is not in paper/refs.bib")
    if key not in cited:
        cited.append(key)
    return cited.index(key) + 1


# ------------------------------------------------------------------ parsing
class Block:
    def __init__(self, kind, **kw):
        self.kind = kind
        self.__dict__.update(kw)


def parse_files(files):
    blocks = []
    for f in files:
        lines = f.read_text(encoding="utf-8").split("\n")
        i = 0
        while i < len(lines):
            ln = lines[i]
            if not ln.strip():
                i += 1
                continue
            if ln.startswith("```"):
                j = i + 1
                while j < len(lines) and not lines[j].startswith("```"):
                    j += 1
                blocks.append(Block("code", text="\n".join(lines[i + 1 : j])))
                i = j + 1
                continue
            m = re.match(r"^(#{1,3}) (.*)$", ln)
            if m:
                blocks.append(Block("h", level=len(m.group(1)), text=m.group(2).strip()))
                i += 1
                continue
            m = re.match(r"^!\[(.*)\]\((.*)\)\{#(fig:[\w-]+)(?: w=([\d.]+))?\}$", ln.strip())
            if m:
                blocks.append(Block("figure", caption=m.group(1), path=m.group(2), id=m.group(3), width=float(m.group(4) or 5.8)))
                i += 1
                continue
            m = re.match(r"^Table: (.*?) \{#(tab:[\w-]+)\}$", ln.strip())
            if m:
                j = i + 1
                rows = []
                while j < len(lines) and lines[j].strip().startswith("|"):
                    rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                    j += 1
                rows = [r for r in rows if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
                blocks.append(Block("table", caption=m.group(1), id=m.group(2), rows=rows))
                i = j
                continue
            if ln.startswith("- ") or re.match(r"^\d+\. ", ln):
                items = []
                ordered = not ln.startswith("- ")
                while i < len(lines) and (lines[i].startswith("- ") or re.match(r"^\d+\. ", lines[i])):
                    items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
                    i += 1
                blocks.append(Block("list", ordered=ordered, items=items))
                continue
            para = [ln]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3} |- |\d+\. |```|!\[|Table: )", lines[i]):
                para.append(lines[i])
                i += 1
            blocks.append(Block("p", text=" ".join(s.strip() for s in para)))
    return blocks


def prescan_citations(blocks):
    order = []
    for b in blocks:
        texts = []
        if b.kind in ("p", "h"):
            texts = [b.text]
        elif b.kind == "list":
            texts = b.items
        elif b.kind == "table":
            texts = [c for r in b.rows for c in r] + [b.caption]
        elif b.kind == "figure":
            texts = [b.caption]
        for t in texts:
            for m in re.finditer(r"\[@([^\]]+)\]", t):
                for k in m.group(1).split(";"):
                    k = k.strip().lstrip("@")
                    if k not in order:
                        order.append(k)
    return order


def check_text_rules(blocks):
    bad = []
    for b in blocks:
        texts = []
        if b.kind in ("p", "h"):
            texts = [b.text]
        elif b.kind == "list":
            texts = b.items
        elif b.kind == "table":
            texts = [c for r in b.rows for c in r] + [b.caption]
        elif b.kind == "figure":
            texts = [b.caption]
        for t in texts:
            if "\u2014" in t or "--" in t:
                bad.append(t[:80])
    if bad:
        raise SystemExit("em dash or double hyphen in prose: " + " | ".join(bad[:5]))


# ------------------------------------------------------------------ docx helpers
def set_cell_shade(cell, color):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcpr.append(shd)


def add_field(par, instr, placeholder="", bold=None):
    def fc(t):
        r = par.add_run()
        e = OxmlElement("w:fldChar")
        e.set(qn("w:fldCharType"), t)
        r._r.append(e)
        return r

    fc("begin")
    r = par.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr} "
    r._r.append(it)
    fc("separate")
    pr = par.add_run(placeholder)
    if bold is not None:
        pr.bold = bold
    fc("end")


def json_value(file, path, fmt):
    d = _json_cache.setdefault(file, json.load(open(EV / file, encoding="utf-8")))
    for k in path.split("."):
        d = d[int(k)] if isinstance(d, list) else d[k]
    return format(d, fmt) if fmt else str(d)


INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|\[@[^\]]+\]|\[\[(?:fig|tab):[\w-]+\]\]|\{\{[^}]+\}\})")


def add_inline(par, text, numbering, size=None, base_bold=False):
    for tok in INLINE.split(text):
        if not tok:
            continue
        run = None
        if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            run = par.add_run(tok[2:-2])
            run.bold = True
        elif tok.startswith("`") and tok.endswith("`"):
            run = par.add_run(tok[1:-1])
            run.font.name = "Consolas"
            run._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Consolas")
            run.font.size = Pt((size or 11) - 1.5)
        elif tok.startswith("[@"):
            keys = [k.strip().lstrip("@") for k in tok[2:-1].split(";")]
            run = par.add_run(", ".join(f"[{cite_number(k)}]" for k in keys))
        elif tok.startswith("[["):
            run = par.add_run(numbering[tok[2:-2]])
        elif tok.startswith("{{"):
            body = tok[2:-2]
            if body == "PENDING":
                run = par.add_run("PENDING")
                run.bold = True
                run.font.color.rgb = RED
            elif body.startswith("P:"):
                run = par.add_run("PENDING: " + body[2:].strip())
                run.bold = True
                run.font.color.rgb = RED
            elif body.startswith("3s:"):
                key = body[3:].strip()
                if key in THREE_SEED:
                    run = par.add_run(str(THREE_SEED[key]))
                else:
                    run = par.add_run("PENDING")
                    run.bold = True
                    run.font.color.rgb = RED
            elif body.startswith("j:"):
                _, f, path, *fmt = body.split(":", 3)
                run = par.add_run(json_value(f, path, fmt[0] if fmt else ""))
            else:
                raise SystemExit("unknown marker " + tok)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            run = par.add_run(tok[1:-1])
            run.italic = True
        else:
            run = par.add_run(tok)
        if base_bold:
            run.bold = True
        if size and not tok.startswith("`"):
            run.font.size = Pt(size)


def setup_styles(doc):
    st = doc.styles
    n = st["Normal"]
    n.font.name = "Times New Roman"
    n.font.size = Pt(11)
    n.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    n.paragraph_format.space_after = Pt(6)
    n.paragraph_format.line_spacing = 1.15
    for name, size, bold, italic, before, after in (("Heading 1", 17, True, False, 0, 14), ("Heading 2", 13.5, True, False, 14, 6), ("Heading 3", 11.5, True, True, 10, 4)):
        s = st[name]
        s.font.name = "Calibri"
        s.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
        s.element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        s.element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        s.font.size = Pt(size)
        s.font.bold = bold
        s.font.italic = italic
        s.font.color.rgb = RGBColor(0x0B, 0x2A, 0x4A)
        s.paragraph_format.space_before = Pt(before)
        s.paragraph_format.space_after = Pt(after)
        s.paragraph_format.keep_with_next = True
    st["Heading 1"].paragraph_format.page_break_before = True
    c = st["Caption"]
    c.font.name = "Calibri"
    c.element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    c.element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    c.font.size = Pt(9.5)
    c.font.bold = False
    c.font.italic = False
    c.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
    c.paragraph_format.space_after = Pt(8)
    for name in ("TOC 1", "TOC 2", "TOC 3", "Table of Figures"):
        try:
            st[name].font.name = "Times New Roman"
            st[name].font.size = Pt(10.5)
        except KeyError:
            pass


def page_number_footer(section, fmt=None, start=None, show=True):
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if show:
        add_field(p, "PAGE", "1")
    sp = section._sectPr
    for old in sp.findall(qn("w:pgNumType")):
        sp.remove(old)
    if fmt or start:
        pn = OxmlElement("w:pgNumType")
        if fmt:
            pn.set(qn("w:fmt"), fmt)
        if start:
            pn.set(qn("w:start"), str(start))
        sp.append(pn)


def emit_refs(doc):
    for idx, key in enumerate(cited, 1):
        kind, f = BIB[key]
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-1.0)
        p.paragraph_format.space_after = Pt(3)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.add_run(f"[{idx}]  ").font.size = Pt(10)
        for text, italic in format_ref(kind, f):
            r = p.add_run(text)
            r.italic = italic
            r.font.size = Pt(10)


def build():
    files = sorted(CONTENT.glob("*.md"))
    blocks = parse_files(files)
    check_text_rules(blocks)
    cited[:] = prescan_citations(blocks)
    for k in cited:
        if k not in BIB:
            raise SystemExit(f"citation key {k} is not in paper/refs.bib")
    # numbering of figures and tables, chapters and appendices
    numbering = {}
    nfig = ntab = 0
    for b in blocks:
        if b.kind == "figure":
            nfig += 1
            numbering[b.id] = f"Figure {nfig}"
        elif b.kind == "table":
            ntab += 1
            numbering[b.id] = f"Table {ntab}"

    doc = Document()
    setup_styles(doc)
    s0 = doc.sections[0]
    s0.page_width, s0.page_height = Cm(21.0), Cm(29.7)
    s0.left_margin = s0.right_margin = Cm(2.5)
    s0.top_margin = s0.bottom_margin = Cm(2.4)

    # ---- title page
    def centered(text, size, bold=False, italic=False, before=0, after=6, color=None):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        r = p.add_run(text)
        r.font.size = Pt(size)
        r.bold = bold
        r.italic = italic
        if color:
            r.font.color.rgb = color
        return p

    centered("Project Report", 14, before=90, after=24, color=RGBColor(0x47, 0x55, 0x69))
    centered("SignBridge", 40, bold=True, after=8, color=RGBColor(0x0B, 0x2A, 0x4A))
    centered("Bidirectional Indian Sign Language and English Communication with a 3D Avatar", 18, after=60)
    centered("Darshan BG", 16, bold=True, after=4)
    centered(TODAY, 12, after=90)
    centered("A research prototype. Every result is on the authors' predefined split of INCLUDE, signer independence not verified. No avatar clip has been reviewed by a signer. INCLUDE-derived material is shared for non-commercial use only under CC BY-NC-SA 4.0.", 10, italic=True, after=0, color=RGBColor(0x47, 0x55, 0x69))
    page_number_footer(s0, show=False)

    # ---- front matter
    s1 = doc.add_section(WD_SECTION.NEW_PAGE)
    page_number_footer(s1, fmt="lowerRoman", start=1)

    def front_heading(text):
        p = doc.add_paragraph()
        p.paragraph_format.page_break_before = True
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(17)
        r.bold = True
        r.font.color.rgb = RGBColor(0x0B, 0x2A, 0x4A)
        p.paragraph_format.space_after = Pt(12)
        return p

    # abstract is written in content/00_abstract.md (first chapter file with the title "Abstract"); take its blocks out of the numbered flow
    abstract_blocks, body_blocks = [], []
    in_abs = False
    for b in blocks:
        if b.kind == "h" and b.level == 1 and b.text == "Abstract":
            in_abs = True
            continue
        if b.kind == "h" and b.level == 1:
            in_abs = False
        (abstract_blocks if in_abs else body_blocks).append(b)
    front_heading("Abstract")
    for b in abstract_blocks:
        if b.kind == "p":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_inline(p, b.text, numbering)
    front_heading("Table of Contents")
    add_field(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u', "Right-click and choose Update Field to build the table of contents.")
    front_heading("List of Figures")
    add_field(doc.add_paragraph(), 'TOC \\h \\z \\c "Figure"', "Update the field to build the list of figures.")
    front_heading("List of Tables")
    add_field(doc.add_paragraph(), 'TOC \\h \\z \\c "Table"', "Update the field to build the list of tables.")

    # ---- body
    s2 = doc.add_section(WD_SECTION.NEW_PAGE)
    page_number_footer(s2, fmt="decimal", start=1)
    chap = sec = sub = 0
    appendix = 0
    fig_n = tab_n = 0
    first_in_section = True
    for b in body_blocks:
        if b.kind == "h":
            if b.level == 1:
                if b.text.startswith("Appendix"):
                    appendix += 1
                    label = f"Appendix {chr(64 + appendix)}: {b.text.split(':', 1)[1].strip()}"
                    sec = sub = 0
                elif b.text == "References":
                    label = "References"
                else:
                    chap += 1
                    sec = sub = 0
                    label = f"{chap}  {b.text}"
                h = doc.add_heading(label, level=1)
            elif b.level == 2:
                sec += 1
                sub = 0
                prefix = f"{chr(64 + appendix)}.{sec}" if appendix else f"{chap}.{sec}"
                h = doc.add_heading(f"{prefix}  {b.text}", level=2)
            else:
                sub += 1
                prefix = f"{chr(64 + appendix)}.{sec}.{sub}" if appendix else f"{chap}.{sec}.{sub}"
                h = doc.add_heading(f"{prefix}  {b.text}", level=3)
            if b.level == 1 and b.text == "References":
                emit_refs(doc)
        elif b.kind == "p":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            add_inline(p, b.text, numbering)
        elif b.kind == "list":
            for k, item in enumerate(b.items, 1):
                if b.ordered:
                    p = doc.add_paragraph()
                    p.paragraph_format.left_indent = Cm(1.0)
                    p.paragraph_format.first_line_indent = Cm(-0.6)
                    p.add_run(f"{k}.  ")
                else:
                    p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.space_after = Pt(2)
                add_inline(p, item, numbering)
            doc.paragraphs[-1].paragraph_format.space_after = Pt(8)
        elif b.kind == "code":
            for line in b.text.split("\n"):
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.left_indent = Cm(0.5)
                r = p.add_run(line if line else " ")
                r.font.name = "Consolas"
                r._r.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Consolas")
                r.font.size = Pt(8.5)
            doc.paragraphs[-1].paragraph_format.space_after = Pt(8)
        elif b.kind == "figure":
            fig_n += 1
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_after = Pt(3)
            path = HERE / b.path
            if not path.is_file():
                raise SystemExit(f"missing figure {path}")
            p.add_run().add_picture(str(path), width=Inches(b.width))
            cap = doc.add_paragraph(style="Caption")
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.add_run("Figure ").bold = True
            add_field(cap, "SEQ Figure \\* ARABIC", str(fig_n), bold=True)
            cap.add_run(". ").bold = True
            add_inline(cap, b.caption, numbering, size=9.5)
        elif b.kind == "table":
            tab_n += 1
            cap = doc.add_paragraph(style="Caption")
            cap.paragraph_format.keep_with_next = True
            cap.paragraph_format.space_after = Pt(3)
            cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
            cap.add_run("Table ").bold = True
            add_field(cap, "SEQ Table \\* ARABIC", str(tab_n), bold=True)
            cap.add_run(". ").bold = True
            add_inline(cap, b.caption, numbering, size=9.5)
            ncols = max(len(r) for r in b.rows)
            t = doc.add_table(rows=0, cols=ncols)
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for ri, row in enumerate(b.rows):
                cells = t.add_row().cells
                for ci in range(ncols):
                    txt = row[ci] if ci < len(row) else ""
                    par = cells[ci].paragraphs[0]
                    par.paragraph_format.space_after = Pt(1)
                    par.paragraph_format.line_spacing = 1.0
                    add_inline(par, txt, numbering, size=8.5, base_bold=(ri == 0))
                    if ri == 0:
                        set_cell_shade(cells[ci], "DCE6F2")
            if b.rows:
                trpr = t.rows[0]._tr.get_or_add_trPr()
                th = OxmlElement("w:tblHeader")
                trpr.append(th)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)
    doc.core_properties.title = "SignBridge Project Report"
    doc.core_properties.author = "Darshan BG"
    doc.save(str(OUT))
    print(f"written {OUT}: {nfig} figures, {ntab} tables, {len(cited)} references, {chap} chapters, {appendix} appendices")
    return nfig, ntab


if __name__ == "__main__":
    nf, nt = build()
    if USE_WORD:
        ps = HERE / "update_fields.ps1"
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps), str(OUT)], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode:
            print(r.stderr.strip()[:600])
