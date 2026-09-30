"""Genere la version autonome du mur de tracts, a envoyer telle quelle.

Les cartes sont pre-generees en HTML et tout le JavaScript est supprime : les
liens fonctionnent donc partout, y compris la ou les scripts inline sont
bloques (ouverture locale, piece jointe, iframe, composant Incorporer).

Les apercus sont re-rendus en basse resolution et embarques en base64 : aucun
dossier d'images n'est necessaire a cote du fichier.
"""

import base64
import html
import os
import re
from urllib.parse import quote

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = HERE
SRC = os.path.join(BASE, "index.html")
DST = os.path.join(BASE, "index_standalone.html")
SHAREPOINT_BASE_URL = (
    "https://nokia.sharepoint.com/sites/CGT39/Shared%20Documents/"
    "salari%C3%A9s/tracts%20diffus%C3%A9s/"
)

TARGET_WIDTH = 520  # px
JPEG_QUALITY = 65

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


def render_thumb(rel_path):
    """Retourne les octets JPEG reduits pour un chemin d'apercu relatif."""
    jpg_path = os.path.join(BASE, rel_path.replace("/", os.sep))
    pdf_path = re.sub(r"_page-0001\.jpg$", ".pdf", jpg_path)

    source = pdf_path if os.path.exists(pdf_path) else jpg_path
    if not os.path.exists(source):
        return None

    with pymupdf.open(source) as doc:
        page = doc.load_page(0)
        zoom = TARGET_WIDTH / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        if pix.alpha:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        return pix.tobytes("jpg", jpg_quality=JPEG_QUALITY)


def sharepoint_file_url(rel_path):
    """Construit une URL directe depuis un chemin relatif de l'index."""
    encoded_path = "/".join(quote(part, safe="") for part in rel_path.split("/"))
    return SHAREPOINT_BASE_URL + encoded_path


def parse_tracts(source):
    """Retourne {annee: [tract, ...]} dans l'ordre chronologique croissant."""
    block = re.search(r"const tractsData = \{(.*?)\n        \};", source, re.S)
    if not block:
        raise SystemExit("Bloc tractsData introuvable")

    entry_re = re.compile(
        r"id:\s*(\d+),\s*"
        r"title:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"pdfPath:\s*'((?:[^'\\]|\\.)*)',\s*"
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
                "pdfPath": unescape_js(pdf_path),
                "previewPath": unescape_js(preview_path),
                "url": sharepoint_file_url(unescape_js(pdf_path)),
                "hasLink": bool(pdf_path),
            }
            for tid, title, pdf_path, preview_path in entry_re.findall(body)
        ]
    return years


def parse_info(source):
    block = re.search(r"const tractsInfo = \{(.*?)\n        \};", source, re.S)
    if not block:
        return {}

    entry_re = re.compile(
        r"(\d+):\s*\{\s*"
        r"subject:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"date:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"summary:\s*'((?:[^'\\]|\\.)*)'\s*\}"
    )
    return {
        int(tid): {
            "subject": unescape_js(subject),
            "date": unescape_js(date),
            "summary": unescape_js(summary),
        }
        for tid, subject, date, summary in entry_re.findall(block.group(1))
    }


def parse_previews(source):
    return {
        tract["id"]: tract["previewPath"]
        for year_tracts in source.values()
        for tract in year_tracts
        if tract["previewPath"]
    }


def build_card(tract, info, data_uri):
    e = html.escape
    title = tract["title"]

    if data_uri:
        preview = f'<img src="{data_uri}" alt="{e(title)}">'
    else:
        preview = (
            f'<div class="card-preview-placeholder"><p>&#128196; {e(title)}</p></div>'
        )

    heading = info.get("subject") if info and info.get("subject") else title
    meta = info.get("date", "") if info else ""
    summary = info.get("summary", "") if info else ""

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
    infos = parse_info(source)
    previews = parse_previews(tracts)

    data_uris = {}
    total = 0
    for tract_id, rel_path in previews.items():
        data = render_thumb(rel_path)
        if data is None:
            print(f"  [!] apercu introuvable : {rel_path}")
            continue
        total += len(data)
        data_uris[tract_id] = "data:image/jpeg;base64," + base64.b64encode(
            data
        ).decode("ascii")

    sections = []
    for year in sorted(tracts, reverse=True):
        cards = "\n                ".join(
            build_card(t, infos.get(t["id"]), data_uris.get(t["id"]))
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

    with open(DST, "w", encoding="utf-8") as f:
        f.write(out)

    count = sum(len(v) for v in tracts.values())
    print(
        f"\n{count} tracts, {len(data_uris)} apercus embarques "
        f"({total // 1024} Ko d'images)"
    )
    print(f"{os.path.basename(DST)} : {os.path.getsize(DST) // 1024} Ko")


if __name__ == "__main__":
    main()
