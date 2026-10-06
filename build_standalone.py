"""Genere la version autonome du mur de tracts, a envoyer telle quelle.

Les cartes sont pre-generees en HTML et tout le JavaScript est supprime : les
liens fonctionnent donc partout, y compris la ou les scripts inline sont
bloques (ouverture locale, piece jointe, iframe, composant Incorporer).

Les apercus sont re-rendus en basse resolution et embarques en base64. Le logo
et le bandeau du titre sont aussi embarques. Aucun dossier d'images n'est
necessaire a cote du fichier.
"""

import base64
import html
import os
import re

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = HERE
SRC = os.path.join(BASE, "index.html")
DST = os.path.join(BASE, "index_standalone.html")

TARGET_WIDTH = 520  # px
JPEG_QUALITY = 65
IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}

EXTRA_CSS = """
        a.card {
            text-decoration: none;
            color: inherit;
        }

        .card-preview img {
            display: block;
        }
"""


def unescape_js(raw):
    """Decode les echappements JS (\\uXXXX, \\') d'un litteral de chaine."""
    raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
    return re.sub(r"\\(.)", r"\1", raw)


def local_pdf_path(preview_path):
    """Retrouve le PDF local a partir du chemin d'apercu."""
    if not preview_path:
        return ""
    rel = preview_path.replace("/", os.sep)
    if rel.startswith("previews" + os.sep):
        rel = "copies" + rel[len("previews") :]
    rel = re.sub(r"_page-0001\.jpe?g$", ".pdf", rel, flags=re.IGNORECASE)
    return os.path.join(BASE, rel)


def render_thumb(preview_path):
    """Retourne les octets JPEG reduits, de preference depuis le PDF."""
    pdf_path = local_pdf_path(preview_path)
    jpg_path = (
        os.path.join(BASE, preview_path.replace("/", os.sep)) if preview_path else ""
    )
    if pdf_path and os.path.exists(pdf_path):
        source = pdf_path
    elif jpg_path and os.path.exists(jpg_path):
        source = jpg_path
    else:
        return None

    with pymupdf.open(source) as doc:
        page = doc.load_page(0)
        zoom = TARGET_WIDTH / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        if pix.alpha:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        return pix.tobytes("jpg", jpg_quality=JPEG_QUALITY)


def parse_tracts(source):
    """Retourne {annee: [tract, ...]} dans l'ordre chronologique croissant."""
    block = re.search(r"const tractsData = \{(.*?)\n        \};", source, re.S)
    if not block:
        raise SystemExit("Bloc tractsData introuvable")

    entry_re = re.compile(
        r"id:\s*(\d+),\s*"
        r"title:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"subject:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"date:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"summary:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"pdfUrl:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"previewPath:\s*'((?:[^'\\]|\\.)*)'"
    )

    years = {}
    for year, body in re.findall(
        r"'(\d{4})':\s*\[(.*?)\n            \]", block.group(1), re.S
    ):
        years[year] = [
            {
                "id": int(tid),
                "title": unescape_js(title),
                "subject": unescape_js(subject),
                "date": unescape_js(date),
                "summary": unescape_js(summary),
                "pdfUrl": unescape_js(pdf_path),
                "previewPath": unescape_js(preview_path),
                "url": unescape_js(pdf_path),
                "hasLink": bool(pdf_path),
            }
            for tid, title, subject, date, summary, pdf_path, preview_path in entry_re.findall(
                body
            )
        ]
    return years


def embed_local_images(page):
    """Remplace les src locaux des balises img par des data URI base64."""
    total = 0

    def replace(match):
        nonlocal total
        src = match.group(1)
        if src.startswith(("data:", "http://", "https://")):
            return match.group(0)

        path = os.path.join(BASE, src.replace("/", os.sep))
        if not os.path.isfile(path):
            print(f"  [!] image introuvable : {src}")
            return match.group(0)

        mime = IMAGE_MIME.get(os.path.splitext(path)[1].lower())
        if not mime:
            print(f"  [!] type d'image non pris en charge : {src}")
            return match.group(0)

        with open(path, "rb") as image:
            data = image.read()
        total += len(data)
        uri = "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii")
        print(f"  image embarquee : {src} ({len(data) // 1024} Ko)")
        return match.group(0).replace(src, uri, 1)

    return re.sub(r'<img\b[^>]*\bsrc="([^"]+)"', replace, page), total


def build_card(tract, data_uri):
    e = html.escape
    title = tract["title"]

    if data_uri:
        preview = f'<img src="{data_uri}" alt="{e(title)}">'
    else:
        preview = (
            f'<div class="card-preview-placeholder"><p>&#128196; {e(title)}</p></div>'
        )

    heading = tract.get("subject") or title
    meta = tract.get("date") or ""
    summary = tract.get("summary") or ""

    content = [f'<h3 class="card-title">{e(heading)}</h3>']
    if meta:
        content.append(f'<p class="card-meta">{e(meta)}</p>')
    if summary:
        content.append(f'<p class="card-summary">{e(summary)}</p>')

    inner = (
        f'\n                    <div class="card-preview">{preview}</div>'
        f'\n                    <div class="card-content">'
        + "".join(f"\n                        {line}" for line in content)
        + "\n                    </div>\n                "
    )

    if tract["hasLink"] and tract["url"]:
        return (
            f'<a class="card" href="{e(tract["url"])}" target="_self" '
            f'rel="noopener noreferrer" title="{e(title)}">{inner}</a>'
        )
    return f'<div class="card" title="{e(title)}">{inner}</div>'


def main():
    with open(SRC, encoding="utf-8") as f:
        source = f.read()

    tracts = parse_tracts(source)

    data_uris = {}
    total = 0
    for year_tracts in tracts.values():
        for tract in year_tracts:
            data = render_thumb(tract["previewPath"])
            if data is None:
                print(f"  [!] apercu introuvable : {tract['previewPath']}")
                continue
            total += len(data)
            data_uris[tract["id"]] = "data:image/jpeg;base64," + base64.b64encode(
                data
            ).decode("ascii")

    sections = []
    for year in sorted(tracts, reverse=True):
        cards = "\n                ".join(
            build_card(t, data_uris.get(t["id"]))
            for t in reversed(tracts[year])
        )
        sections.append(
            '        <section class="year-section">\n'
            '            <div class="year-separator">\n'
            f'                <span class="year-separator-label">{year}</span>\n'
            "            </div>\n"
            '            <div class="grid">\n'
            f"                {cards}\n"
            "            </div>\n"
            "        </section>"
        )

    out = source.replace("    </style>", EXTRA_CSS + "    </style>", 1)
    out = out.replace(
        '        <div id="content"></div>', "\n".join(sections).lstrip(), 1
    )
    out = re.sub(r"\n    <script>.*?</script>\n", "\n", out, flags=re.S)
    out, static_total = embed_local_images(out)

    with open(DST, "w", encoding="utf-8") as f:
        f.write(out)

    count = sum(len(v) for v in tracts.values())
    print(
        f"\n{count} tracts, {len(data_uris)} apercus embarques "
        f"({total // 1024} Ko d'apercus, {static_total // 1024} Ko d'images fixes)"
    )
    print(f"{os.path.basename(DST)} : {os.path.getsize(DST) // 1024} Ko")


if __name__ == "__main__":
    main()
