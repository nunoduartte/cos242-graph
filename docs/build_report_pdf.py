"""Builds docs/relatorio_parte3.pdf from docs/relatorio_parte3.md (A4, same look as Part 2).

Usage (from the repository root, with a Python that has the `markdown` package):
  ~/.venvs/cos242-accel/bin/python docs/build_report_pdf.py [--md docs/relatorio_parte3.md]
Needs Google Chrome or Chromium (headless print to PDF). Images referenced by the
Markdown are resolved relative to docs/. The page count is printed (limit: 5).
"""
import argparse
import os
import re
import shutil
import subprocess
import tempfile

import markdown

CSS = """
@page { size: A4; margin: 13mm 14mm 13mm 14mm; }
:root { --navy:#14213D; --blue:#1C5CAB; --ink:#1f2933; --muted:#5b6573; --line:#c9d3e0; --head:#e8eff9; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "DejaVu Sans", "Liberation Sans", Arial, sans-serif; font-size: 8.8pt; line-height: 1.32;
       color: var(--ink); margin: 0; text-align: justify; hyphens: auto; }
.eyebrow { color: var(--blue); font-size: 7.4pt; letter-spacing: .14em; text-transform: uppercase; margin: 0 0 2px; }
h1 { color: var(--navy); font-size: 17pt; margin: 0 0 2px; }
h1 + p { margin-top: 0; color: var(--muted); border-bottom: 1.5px solid var(--navy); padding-bottom: 4px; }
h2 { color: var(--navy); font-size: 12pt; margin: 9px 0 3px; border-bottom: 1px solid var(--line); padding-bottom: 1px; }
h3 { color: var(--navy); font-size: 10.2pt; margin: 7px 0 2px; }
p { margin: 3px 0; }
ul, ol { margin: 2px 0 3px; padding-left: 16px; }
li { margin: 1px 0; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 7.8pt; background: #f1f4f8; padding: 0 2px;
       border-radius: 2px; color: var(--blue); }
a { color: var(--blue); text-decoration: none; }
table { border-collapse: collapse; width: 100%; margin: 3px 0 4px; font-size: 7.6pt; line-height: 1.25;
        text-align: left; page-break-inside: avoid; }
th { background: var(--head); color: var(--navy); font-weight: bold; }
th, td { border: 1px solid var(--line); padding: 1.5px 4px; vertical-align: top; }
td.num, th.num { text-align: right; }
.caption, em.caption { color: var(--muted); font-size: 7.3pt; }
figure { margin: 3px 0; text-align: center; page-break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { color: var(--muted); font-size: 7.3pt; }
.two { display: flex; gap: 10px; }
.two > div { flex: 1; min-width: 0; }
"""

NUMERIC = re.compile(r"^[\s\-−+≈~<>≥≤]*[\d.,]+(\s?(s|h|%|GiB|MB|×))?[\s\d.,±()/a-z×%−]*$")


def to_html(md_text: str, title: str) -> str:
    body = markdown.markdown(md_text, extensions=["tables", "md_in_html", "attr_list"])

    def align(match):  # right-align cells that are numbers
        tag, attrs, content = match.group(1), match.group(2), match.group(3)
        plain = re.sub(r"<[^>]+>", "", content).strip()
        if plain and NUMERIC.match(plain) and re.search(r"\d", plain):
            attrs = (attrs or "") + ' class="num"'
        return f"<{tag}{attrs or ''}>{content}</{tag}>"
    body = re.sub(r"<(td)([^>]*)>(.*?)</td>", align, body, flags=re.S)
    return (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>{title}</title>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")


def chrome() -> str:
    for name in ("google-chrome", "chromium", "chromium-browser", "google-chrome-stable"):
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("Chrome/Chromium not found")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", default="docs/relatorio_parte3.md")
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--title", default="Relatório – Parte 3")
    a = ap.parse_args()
    pdf = os.path.abspath(a.pdf or os.path.splitext(a.md)[0] + ".pdf")
    with open(a.md, encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    html_path = os.path.join(os.path.dirname(os.path.abspath(a.md)), ".relatorio_build.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(to_html(text, a.title))
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([chrome(), "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}",
                        "--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file://" + html_path],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(html_path)
    out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    pages = re.search(r"Pages:\s+(\d+)", out)
    print(f"{pdf}: {pages.group(1) if pages else '?'} pages")


if __name__ == "__main__":
    main()
