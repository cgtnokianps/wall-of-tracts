"""Genere une version email du mur de tracts.

Mise en page en tableaux avec styles inline : c'est le seul rendu fiable dans
Outlook (moteur Word), qui ignore grid, flexbox et la plupart du CSS moderne.

Mode d'emploi :
  1. python build_email.py
  2. ouvrir wall_of_tracts_email.html dans le navigateur
  3. Ctrl+A puis Ctrl+C
  4. coller dans un nouveau message Outlook

Au collage, Outlook transforme les images base64 en pieces jointes integrees
(CID), ce qui les rend visibles chez les destinataires. Les miniatures sont
donc volontairement tres reduites pour limiter le poids du message.
"""

import base64
import html
import os
import re

import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SRC = os.path.join(BASE, "wall_of_tracts_sharepoint.html")
DST = os.path.join(BASE, "wall_of_tracts_email.html")

TARGET_WIDTH = 300  # px rendus, affiches a 150 px pour rester nets en HiDPI
DISPLAY_WIDTH = 150
JPEG_QUALITY = 55
COLUMNS = 3

BG = "#0f1115"
SURFACE = "#1a1d24"
BORDER = "#2e333d"
TEXT = "#e8eaed"
MUTED = "#9aa0aa"
ACCENT = "#e63946"

FONT = "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def unescape_js(raw):
    raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
    return re.sub(r"\\(.)", r"\1", raw)


def render_thumb(rel_path):
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


def parse_tracts(source):
    block = re.search(r"const tractsData = \{(.*?)\n        \};", source, re.S)
    if not block:
        raise SystemExit("Bloc tractsData introuvable")

    entry_re = re.compile(
        r"id:\s*(\d+),\s*"
        r"title:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"url:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"hasLink:\s*(true|false)"
    )

    years = {}
    for year, body in re.findall(
        r"'(\d{4})':\s*\[(.*?)\n            \]", block.group(1), re.S
    ):
        years[year] = [
            {
                "id": int(tid),
                "title": unescape_js(title),
                "url": unescape_js(url),
                "hasLink": has_link == "true",
            }
            for tid, title, url, has_link in entry_re.findall(body)
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
        int(tid): {"subject": unescape_js(s), "date": unescape_js(d)}
        for tid, s, d, _ in entry_re.findall(block.group(1))
    }


def parse_previews(source):
    block = re.search(r"const previewsById = \{(.*?)\n        \};", source, re.S)
    if not block:
        raise SystemExit("Bloc previewsById introuvable")
    return {
        int(tid): unescape_js(path)
        for tid, path in re.findall(r"(\d+):\s*'((?:[^'\\]|\\.)*)'", block.group(1))
    }


def build_cell(tract, info, data_uri):
    e = html.escape
    title = tract["title"]
    heading = info.get("subject") if info and info.get("subject") else title
    date = info.get("date", "") if info else ""
    url = tract["url"] if tract["hasLink"] else ""

    if data_uri:
        img = (
            f'<img src="{data_uri}" width="{DISPLAY_WIDTH}" alt="{e(title)}" '
            f'style="display:block;width:{DISPLAY_WIDTH}px;height:auto;'
            f'border:1px solid {BORDER};border-radius:6px;">'
        )
    else:
        img = (
            f'<div style="width:{DISPLAY_WIDTH}px;height:210px;background:{SURFACE};'
            f'border:1px solid {BORDER};border-radius:6px;"></div>'
        )

    link_style = (
        f"font-family:{FONT};font-size:13px;font-weight:600;line-height:1.35;"
        f"color:{TEXT};text-decoration:none;"
    )
    caption = f'<a href="{e(url)}" style="{link_style}">{e(heading)}</a>' if url else (
        f'<span style="{link_style}">{e(heading)}</span>'
    )

    meta = (
        f'<div style="font-family:{FONT};font-size:11px;color:{MUTED};'
        f'padding-top:4px;">{e(date)}</div>'
        if date
        else ""
    )

    thumb = f'<a href="{e(url)}">{img}</a>' if url else img

    return (
        f'<td width="{DISPLAY_WIDTH + 30}" valign="top" '
        f'style="padding:0 15px 28px 0;">'
        f"{thumb}"
        f'<div style="padding-top:8px;max-width:{DISPLAY_WIDTH}px;">{caption}{meta}</div>'
        f"</td>"
    )


def build_year(year, cells):
    rows = []
    for i in range(0, len(cells), COLUMNS):
        chunk = cells[i : i + COLUMNS]
        chunk += ["<td></td>"] * (COLUMNS - len(chunk))
        rows.append("<tr>" + "".join(chunk) + "</tr>")

    return (
        f'<tr><td colspan="{COLUMNS}" style="padding:10px 0 18px 0;">'
        f'<div style="font-family:{FONT};font-size:18px;font-weight:700;'
        f"letter-spacing:3px;color:{TEXT};border-bottom:1px solid {BORDER};"
        f'padding-bottom:8px;">{year}</div></td></tr>'
        + "".join(rows)
    )


def main():
    with open(SRC, encoding="utf-8") as f:
        source = f.read()

    tracts = parse_tracts(source)
    infos = parse_info(source)
    previews = parse_previews(source)

    data_uris = {}
    total = 0
    for tract_id, rel_path in previews.items():
        data = render_thumb(rel_path)
        if data is None:
            print(f"  [!] apercu introuvable : {rel_path}")
            continue
        total += len(data)
        data_uris[tract_id] = "data:image/jpeg;base64," + base64.b64encode(data).decode(
            "ascii"
        )

    body = []
    for year in sorted(tracts, reverse=True):
        cells = [
            build_cell(t, infos.get(t["id"]), data_uris.get(t["id"]))
            for t in reversed(tracts[year])
        ]
        body.append(build_year(year, cells))

    width = (DISPLAY_WIDTH + 30) * COLUMNS

    out = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Tracts CGT NPS</title>
</head>
<body style="margin:0;padding:24px;background:{BG};">
<table cellpadding="0" cellspacing="0" border="0" width="{width}"
       style="background:{BG};">
<tr><td colspan="{COLUMNS}" style="padding-bottom:24px;">
  <div style="font-family:{FONT};font-size:26px;font-weight:700;color:{TEXT};">
    Tracts CGT NPS
  </div>
  <div style="font-family:{FONT};font-size:13px;color:{MUTED};padding-top:6px;">
    Cliquez sur un tract pour l'ouvrir.
  </div>
</td></tr>
{''.join(body)}
<tr><td colspan="{COLUMNS}" style="padding-top:12px;border-top:1px solid {BORDER};">
  <div style="font-family:{FONT};font-size:12px;color:{MUTED};padding-top:12px;">
    CGT NPS &mdash; <span style="color:{ACCENT};">syndicat CGT Nokia</span>
  </div>
</td></tr>
</table>
</body>
</html>
"""

    with open(DST, "w", encoding="utf-8") as f:
        f.write(out)

    count = sum(len(v) for v in tracts.values())
    print(f"\n{count} tracts, {len(data_uris)} miniatures ({total // 1024} Ko d'images)")
    print(f"{os.path.basename(DST)} : {os.path.getsize(DST) // 1024} Ko")
    print("\nOuvrir dans le navigateur, Ctrl+A / Ctrl+C, puis coller dans Outlook.")


if __name__ == "__main__":
    main()
