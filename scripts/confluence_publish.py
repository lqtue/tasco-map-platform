#!/usr/bin/env python3
"""Publish the osm-enrichment wiki + plan + geocode README to Confluence Cloud.

Reads Markdown (the source of truth), converts to Confluence *storage* XHTML,
uploads referenced images as page attachments, and upserts the pages (create or
new version). Stdlib only — no third-party deps, no pandoc.

Env (Confluence Cloud, HTTP Basic = email:API-token):
    CONFLUENCE_BASE_URL   e.g. https://<site>.atlassian.net/wiki
    CONFLUENCE_EMAIL      Atlassian account email
    CONFLUENCE_TOKEN      API token (id.atlassian.com → Security → API tokens)

Per-page target space key + parent nesting live in the PAGES manifest below.

Usage:
    python3 scripts/confluence_publish.py --dry-run   # print XHTML, no network
    python3 scripts/confluence_publish.py             # publish for real
"""
import base64, json, mimetypes, os, re, sys, urllib.error, urllib.parse, urllib.request, uuid

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# key, markdown path (relative to repo), Confluence title, parent (None=space root,
# or another page's key for nesting), Confluence space key.
PAGES = [
    ("wiki",    "osm-enrichment/wiki/01-bo-wiki-luat-internal.md",    "OSM Luật Internal — Wiki",                 None,   "NR"),
    ("matrix",  "osm-enrichment/wiki/02-bang-quyet-dinh-theo-luat.md","Bảng Quyết Định theo Luật",                "wiki", "NR"),
    ("plan",    "osm-enrichment/plans/maxspeed-name-edit-plan.md",    "Maxspeed/Name Edit — Kế hoạch triển khai", "wiki", "NR"),
    ("geocode", "geocode/README.md",                                  "VN Admin Geocode — Dataset",               None,   "GSPA"),
]

# ── Markdown → Confluence storage XHTML ─────────────────────────────────────

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def inline(s):
    """Inline markdown → XHTML (storage). Code spans are protected so that `*` or
    `[` inside them are not treated as emphasis/link syntax."""
    s = esc(s)
    s = s.replace("&lt;br/&gt;", "<br/>").replace("&lt;br&gt;", "<br/>")
    # pull code spans out behind sentinels so emphasis/links don't touch them
    spans = []
    def _stash(m):
        spans.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(spans)-1}\x00"
    s = re.sub(r"`([^`]+)`", _stash, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], s)
    return s

IMG_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")

def md_to_storage(md):
    """Return (xhtml, [image_src_paths]). image src paths are as written in md."""
    lines = md.split("\n")
    out, images, i, n = [], [], 0, len(lines)
    while i < n:
        line = lines[i]
        # image on its own line
        m = IMG_RE.match(line)
        if m:
            alt, src = m.group(1), m.group(2)
            images.append(src)
            fn = os.path.basename(src)
            out.append(f'<p><ac:image ac:alt="{esc(alt)}"><ri:attachment ri:filename="{esc(fn)}"/></ac:image></p>')
            i += 1; continue
        # blank
        if not line.strip():
            i += 1; continue
        # heading
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1)); out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1; continue
        # horizontal rule
        if re.match(r"^\s*---+\s*$", line):
            out.append("<hr/>"); i += 1; continue
        # table: header row followed by a |---| separator
        if line.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1]):
            def cells(row):
                row = row.strip()
                if row.startswith("|"): row = row[1:]
                if row.endswith("|"): row = row[:-1]
                return [c.strip() for c in row.split("|")]
            header = cells(line); i += 2
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append(cells(lines[i])); i += 1
            t = ["<table><tbody>"]
            t.append("<tr>" + "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr>")
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t)); continue
        # blockquote (consecutive > lines, blank-> paragraph break)
        if line.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            paras = []
            cur = []
            for b in buf:
                if b.strip(): cur.append(inline(b))
                elif cur: paras.append(" ".join(cur)); cur = []
            if cur: paras.append(" ".join(cur))
            out.append("<blockquote>" + "".join(f"<p>{p}</p>" for p in paras) + "</blockquote>")
            continue
        # unordered list
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(inline(re.sub(r"^\s*[-*]\s+", "", lines[i]))); i += 1
            out.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            continue
        # ordered list
        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(inline(re.sub(r"^\s*\d+\.\s+", "", lines[i]))); i += 1
            out.append("<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>")
            continue
        # paragraph (accumulate until blank)
        buf = [line]; i += 1
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|\s*[-*]\s|\s*\d+\.\s|>|\|)", lines[i]) and not IMG_RE.match(lines[i]):
            buf.append(lines[i]); i += 1
        out.append("<p>" + inline(" ".join(buf)) + "</p>")
    return "\n".join(out), images

# ── Confluence REST client ──────────────────────────────────────────────────

class Confluence:
    def __init__(self, base, email, token):
        self.base = base.rstrip("/")
        self.auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()

    def _req(self, method, path, data=None, headers=None, raw=False):
        url = path if path.startswith("http") else self.base + path
        h = {"Authorization": self.auth, "Accept": "application/json"}
        if headers: h.update(headers)
        body = data if raw else (json.dumps(data).encode() if data is not None else None)
        if data is not None and not raw: h["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        try:
            with urllib.request.urlopen(req) as r:
                txt = r.read().decode()
                return json.loads(txt) if txt else {}
        except urllib.error.HTTPError as e:
            raise SystemExit(f"HTTP {e.code} {method} {url}\n{e.read().decode()}")

    def find(self, title, space):
        q = urllib.parse.urlencode({"spaceKey": space, "title": title, "expand": "version"})
        res = self._req("GET", f"/rest/api/content?{q}")
        r = res.get("results") or []
        return r[0] if r else None

    def upsert(self, title, storage, parent_id, space):
        existing = self.find(title, space)
        body = {
            "type": "page", "title": title, "space": {"key": space},
            "body": {"storage": {"value": storage, "representation": "storage"}},
        }
        if parent_id: body["ancestors"] = [{"id": str(parent_id)}]
        if existing:
            body["id"] = existing["id"]
            body["version"] = {"number": existing["version"]["number"] + 1}
            res = self._req("PUT", f"/rest/api/content/{existing['id']}", body)
            action = "updated"
        else:
            res = self._req("POST", "/rest/api/content", body)
            action = "created"
        return res["id"], action

    def attach(self, page_id, filepath):
        fn = os.path.basename(filepath)
        ctype = mimetypes.guess_type(fn)[0] or "application/octet-stream"
        boundary = uuid.uuid4().hex
        with open(filepath, "rb") as f: content = f.read()
        parts = []
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                     f"filename=\"{fn}\"\r\nContent-Type: {ctype}\r\n\r\n".encode())
        parts.append(content)
        parts.append(f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"minorEdit\"\r\n\r\ntrue\r\n".encode())
        parts.append(f"--{boundary}--\r\n".encode())
        payload = b"".join(parts)
        # POST to child/attachment creates, or adds a new version if filename exists
        self._req("POST", f"/rest/api/content/{page_id}/child/attachment", data=payload, raw=True,
                  headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                           "X-Atlassian-Token": "nocheck"})
        return fn

# ── main ────────────────────────────────────────────────────────────────────

def main():
    dry = "--dry-run" in sys.argv
    rendered = []  # (key, title, parent_key, space, storage, [abs_image_paths])
    for key, rel, title, parent, space in PAGES:
        md_path = os.path.join(REPO, rel)
        with open(md_path) as f: md = f.read()
        storage, imgs = md_to_storage(md)
        img_paths = [os.path.normpath(os.path.join(os.path.dirname(md_path), s)) for s in imgs]
        rendered.append((key, title, parent, space, storage, img_paths))

    if dry:
        for key, title, parent, space, storage, imgs in rendered:
            print(f"\n{'='*78}\n# [{space}] {title}   (key={key}, parent={parent or 'space root'})")
            print(f"# images: {[os.path.basename(p) for p in imgs]}")
            print(f"{'-'*78}\n{storage}")
        print(f"\n[dry-run] {len(rendered)} page(s) rendered; no network calls made.")
        return

    base = os.environ.get("CONFLUENCE_BASE_URL"); email = os.environ.get("CONFLUENCE_EMAIL")
    token = os.environ.get("CONFLUENCE_TOKEN")
    missing = [k for k, v in [("CONFLUENCE_BASE_URL", base), ("CONFLUENCE_EMAIL", email),
                              ("CONFLUENCE_TOKEN", token)] if not v]
    if missing:
        raise SystemExit("Missing env vars: " + ", ".join(missing) + "  (use --dry-run to preview)")

    cf = Confluence(base, email, token)
    ids = {}  # key -> page id
    for key, title, parent, space, storage, imgs in rendered:
        parent_id = ids.get(parent) if parent else None
        page_id, action = cf.upsert(title, storage, parent_id, space)
        ids[key] = page_id
        for p in imgs:
            if not os.path.exists(p):
                print(f"  ! missing image, skipped: {p}"); continue
            cf.attach(page_id, p)
        url = f"{base.rstrip('/')}/spaces/{space}/pages/{page_id}"
        print(f"{action:8} [{space}] {title}  →  {url}  ({len(imgs)} image(s))")

if __name__ == "__main__":
    main()
