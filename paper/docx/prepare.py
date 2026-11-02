"""Step 1 of the Word build: turn paper/main.tex into a pandoc friendly copy (paper/docx/_build/main_docx.tex), convert the figure PDFs to PNG and
write the [VERIFY] notes of refs.bib as a Lua table. Nothing in main.tex itself is changed."""
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
PAPER = HERE.parent
BUILD = HERE / "_build"
BUILD.mkdir(exist_ok=True)
PDFTOPPM = Path.home() / "AppData/Local/Programs/MiKTeX/miktex/bin/x64/miktex-pdftoppm.exe"

tex = (PAPER / "main.tex").read_text(encoding="utf-8")

# macros of the PDF build become markers that the Lua filter turns into highlighted text
tex = re.sub(r"\\newcommand\{\\(pending|todo|signbridge)\}.*\n", "", tex)
tex = tex.replace(r"\signbridge{}", "SignBridge")
tex = tex.replace(r"\begin{table*}", r"\begin{table}").replace(r"\end{table*}", r"\end{table}")
# math inside a marker cannot carry a highlight in Word, so the two symbols used there become plain characters
def _plain(m):
    return m.group(0).replace(r'$\pm$', '±').replace(r'$\Delta$', 'Δ')
tex = re.sub(r'\\pending\{[^{}]*}', _plain, tex)
tex = tex.replace(r"\pending{", r"\href{PENDING}{").replace(r"\todo{", r"\href{TODO}{")

# IEEE only constructs
tex = re.sub(r"\\documentclass\[conference\]\{IEEEtran\}", r"\\documentclass{article}", tex)
tex = re.sub(
    r"\\author\{\\IEEEauthorblockN\{(.*?)\}\n\\IEEEauthorblockA\{(.*?)\\\\\nEmail: (.*?)\}\}",
    lambda m: r"\author{" + m.group(1) + r"\\" + m.group(2) + r"\\Email: " + m.group(3) + "}",
    tex,
    flags=re.S,
)
tex = re.sub(r"\\begin\{IEEEkeywords\}\n(.*?)\n\\end\{IEEEkeywords\}", lambda m: r"\textbf{\emph{Index Terms}}: " + m.group(1), tex, flags=re.S)
tex = tex.replace(r"\bibliographystyle{IEEEtran}", "").replace(r"\bibliography{refs}", r"\section*{References}")

# figures: PDF to PNG (Word cannot embed PDF)
for pdf in sorted((PAPER / "figures").glob("fig_*.pdf")):
    subprocess.run([str(PDFTOPPM), "-r", "300", "-png", "-singlefile", str(pdf), str(BUILD / pdf.stem)], check=True, capture_output=True)
tex = re.sub(r"\\includegraphics\[[^\]]*\]\{figures/(fig_[a-z_]+)\.pdf\}", r"\\includegraphics[width=3.4in]{\1.png}", tex)
(BUILD / "main_docx.tex").write_text(tex, encoding="utf-8", newline="\n")

# [VERIFY] notes: the comment line before each bib entry
bib = (PAPER / "refs.bib").read_text(encoding="utf-8")
notes = {}
for m in re.finditer(r"%\s*\[VERIFY\]\s*(.*?)\n@\w+\{([^,]+),", bib):
    notes[m.group(2)] = m.group(1).strip()
lua = "return {\n" + "".join(f'  ["{k}"] = "{v.replace(chr(34), chr(39))}",\n' for k, v in notes.items()) + "}\n"
(BUILD / "verify_notes.lua").write_text(lua, encoding="utf-8", newline="\n")
print("prepared:", len(list(BUILD.glob("*.png"))), "figures,", len(notes), "VERIFY notes")
