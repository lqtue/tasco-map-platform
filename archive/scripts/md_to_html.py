#!/usr/bin/env python3
"""Render a Markdown file to a clean standalone HTML (and optional PDF).

No third-party Markdown dependency (none is installed here) — a compact converter
covering the constructs our docs use: headings, GFM tables, fenced code, blockquotes,
ordered/unordered lists, hr, and inline **bold** / `code` / [links](url).

Usage:
    python3 scripts/md_to_html.py docs/vision/road-attribute-editor-plan.md          # -> .html
    python3 scripts/md_to_html.py docs/vision/road-attribute-editor-plan.md --pdf    # + .pdf (needs weasyprint)
"""
import base64
import html
import re
import sys
from pathlib import Path

CSS = """
:root { --ink:#1f2933; --muted:#6b7280; --line:#dde3ec; --accent:#1a2e5c; --navy:#1a2e5c; }
* { box-sizing: border-box; }
body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       color: var(--ink); line-height: 1.6; max-width: 860px; margin: 40px auto;
       padding: 0 32px; font-size: 15px; }
.doc-header { display:flex; align-items:center; justify-content:space-between;
              padding-bottom: 18px; margin-bottom: 28px;
              border-bottom: 3px solid var(--navy); }
.doc-header img { height: 36px; width: auto; }
.doc-header .div-label { font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
                          color: var(--muted); font-weight: 600; text-align: right; }
h1 { font-size: 28px; line-height: 1.2; margin: 0 0 6px; color: var(--navy); }
h2 { font-size: 19px; margin: 36px 0 10px; padding-bottom: 6px;
     border-bottom: 2px solid var(--line); color: var(--navy); }
h3 { font-size: 15px; margin: 22px 0 8px; color: #2c3e66; }
p { margin: 10px 0; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
       font-size: 0.88em; background: #f0f3f8; padding: 1px 5px; border-radius: 4px; }
pre { background: #0f172a; color: #e2e8f0; padding: 14px 16px; border-radius: 8px;
      overflow-x: auto; line-height: 1.45; }
pre code { background: none; color: inherit; padding: 0; font-size: 13px; }
blockquote { margin: 14px 0; padding: 8px 16px; border-left: 4px solid #7a96c4;
             background: #f5f7fb; color: #44505e; border-radius: 0 6px 6px 0; }
blockquote p { margin: 4px 0; }
ul, ol { margin: 10px 0; padding-left: 24px; }
li { margin: 5px 0; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; }
th, td { border: 1px solid var(--line); padding: 8px 11px; text-align: left; vertical-align: top; }
th { background: #edf0f7; color: var(--navy); font-weight: 600; }
tr:nth-child(even) td { background: #f8f9fc; }
hr { border: 0; border-top: 1px solid var(--line); margin: 28px 0; }
figure { margin: 24px 0; text-align: center; }
figure svg { max-width: 100%; height: auto; }
figcaption { font-size: 13px; color: var(--muted); margin-top: 8px; text-align: center; }
.doc-footer { margin-top: 48px; padding-top: 14px; border-top: 1px solid var(--line);
              font-size: 12px; color: var(--muted); }
@media print {
  body { margin: 0; max-width: none; font-size: 11pt; padding: 0 24px; }
  .doc-header { padding-bottom: 14px; margin-bottom: 20px; }
  h1 { font-size: 22pt; }
  h2 { page-break-after: avoid; font-size: 14pt; }
  pre, table, blockquote { page-break-inside: avoid; }
  pre { background: #f3f5f9; color: #0f172a; }
}
"""


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\s][^*]*?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def split_row(line: str):
    line = line.strip().strip("|")
    cells = re.split(r"(?<!\\)\|", line)
    return [c.strip().replace("\\|", "|") for c in cells]


def is_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$", line))


def convert(md: str) -> str:
    lines = md.split("\n")
    out, i, n = [], 0, len(md.split("\n"))
    para = []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < n:
        line = lines[i]
        # fenced code
        if line.startswith("```"):
            flush()
            buf, i = [], i + 1
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>")
            i += 1; continue
        # raw HTML block (figure / svg / div / section) — passthrough verbatim until a blank line
        if re.match(r"^<(figure|svg|div|section)\b", line):
            flush()
            buf = [line]; i += 1
            while i < n and lines[i].strip():
                buf.append(lines[i]); i += 1
            out.append("\n".join(buf)); continue
        # table: header row + separator
        if "|" in line and i + 1 < n and is_sep(lines[i + 1]):
            flush()
            head = split_row(line)
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>")
            i += 2
            while i < n and "|" in lines[i] and lines[i].strip():
                cells = split_row(lines[i])
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
                i += 1
            out.append("</tbody></table>"); continue
        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2).strip())}</h{lvl}>"); i += 1; continue
        # hr
        if re.match(r"^---+\s*$", line):
            flush(); out.append("<hr>"); i += 1; continue
        # blockquote
        if line.startswith(">"):
            flush(); buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(inline(re.sub(r"^>\s?", "", lines[i]))); i += 1
            out.append("<blockquote>" + "".join(f"<p>{b}</p>" for b in buf if b) + "</blockquote>"); continue
        # lists
        if re.match(r"^\s*[-*]\s+", line):
            flush(); items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(inline(re.sub(r"^\s*[-*]\s+", "", lines[i]))); i += 1
            out.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>"); continue
        if re.match(r"^\s*\d+\.\s+", line):
            flush(); items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(inline(re.sub(r"^\s*\d+\.\s+", "", lines[i]))); i += 1
            out.append("<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>"); continue
        # blank / paragraph
        if not line.strip():
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def _logo_tag(src: Path) -> str:
    for candidate in [src.parent / "assets/tasco-logo.png",
                      src.parent.parent / "docs/assets/tasco-logo.png"]:
        if candidate.exists():
            data = base64.b64encode(candidate.read_bytes()).decode()
            return f'<img src="data:image/png;base64,{data}" alt="TASCO">'
    return '<strong style="font-size:22px;letter-spacing:.05em;color:#1a2e5c">TASCO</strong>'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    src = Path(args[0])
    md = src.read_text(encoding="utf-8")
    title = next((l[2:].strip() for l in md.split("\n") if l.startswith("# ")), src.stem)
    header = (f'<div class="doc-header">{_logo_tag(src)}'
              f'<div class="div-label">Mapping Division<br>Confidential</div></div>')
    footer = '<div class="doc-footer">TASCO Mapping Division · VTII · TASCO Group · Confidential</div>'
    doc = (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
           f"<meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
           f"<body>{header}{convert(md)}{footer}</body></html>")
    out_html = src.with_suffix(".html")
    out_html.write_text(doc, encoding="utf-8")
    print(f"wrote {out_html}")
    if "--pdf" in sys.argv:
        from weasyprint import HTML  # noqa: import-late so HTML-only runs need no dep
        out_pdf = src.with_suffix(".pdf")
        HTML(string=doc, base_url=str(src.parent)).write_pdf(out_pdf)
        print(f"wrote {out_pdf}")


if __name__ == "__main__":
    main()
