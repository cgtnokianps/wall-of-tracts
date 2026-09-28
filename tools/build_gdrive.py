"""Genere la version Google Drive du mur de tracts.

Reprend wall_of_tracts_sharepoint.html et remplace :
  - les liens SharePoint par des liens Drive vers le PDF correspondant ;
  - les chemins d'apercus locaux par des miniatures Drive.

Prerequis : gdrive_ids.csv, produit par gdrive_list_ids.gs (Apps Script),
au format "chemin/relatif.pdf;FILE_ID" (une ligne par fichier).
"""

import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SRC = os.path.join(BASE, "wall_of_tracts_sharepoint.html")
DST = os.path.join(BASE, "wall_of_tracts_gdrive.html")
IDS = os.path.join(HERE, "gdrive_ids.csv")

THUMB_WIDTH = 800

# PDF dont le nom ne se deduit pas de celui de l'apercu.
PDF_OVERRIDES = {
    8: "2023/tract-noel-2023-V3.pdf",
    17: "2025/CGT-NPS-Voeux-2025.pdf",
    28: "2025/tract evaluation objectifs v2--3p.pdf",
}


def key(path):
    """Cle de recherche insensible a la casse et a la forme Unicode."""
    path = unicodedata.normalize("NFC", path).replace("\\", "/")
    return path.replace("\u00a0", " ").strip().casefold()


def unescape_js(raw):
    raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
    return re.sub(r"\\(.)", r"\1", raw)


def escape_js(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


def load_ids():
    if not os.path.exists(IDS):
        sys.exit(
            f"{IDS} introuvable.\n"
            "Executez gdrive_list_ids.gs sur script.google.com, puis enregistrez "
            "la sortie ici (une ligne 'chemin;FILE_ID' par fichier)."
        )
    ids = {}
    with open(IDS, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or ";" not in line:
                continue
            path, file_id = line.rsplit(";", 1)
            ids[key(path)] = file_id.strip()
    return ids


def main():
    ids = load_ids()
    with open(SRC, encoding="utf-8") as f:
        source = f.read()

    block_re = re.compile(r"(const previewsById = \{)(.*?)(\n        \};)", re.S)
    block = block_re.search(source)
    if not block:
        sys.exit("Bloc previewsById introuvable")

    previews = {
        int(tid): unescape_js(path)
        for tid, path in re.findall(
            r"(\d+):\s*'((?:[^'\\]|\\.)*)'", block.group(2)
        )
    }

    missing = []
    fallbacks = []
    thumb_urls = {}
    pdf_urls = {}

    for tract_id, rel_jpg in previews.items():
        jpg_id = ids.get(key(rel_jpg))
        if jpg_id:
            thumb_urls[tract_id] = (
                f"https://drive.google.com/thumbnail?id={jpg_id}&sz=w{THUMB_WIDTH}"
            )
        else:
            missing.append(("jpg", tract_id, rel_jpg))

        rel_pdf = PDF_OVERRIDES.get(
            tract_id, re.sub(r"_page-0001\.jpg$", ".pdf", rel_jpg)
        )
        target_id = ids.get(key(rel_pdf))
        if not target_id and jpg_id:
            target_id = jpg_id
            fallbacks.append((tract_id, rel_pdf))
        if target_id:
            pdf_urls[tract_id] = f"https://drive.google.com/file/d/{target_id}/view"
        else:
            missing.append(("pdf", tract_id, rel_pdf))

    # Liens des cartes
    entry_re = re.compile(
        r"(id:\s*(\d+),\s*title:\s*'(?:[^'\\]|\\.)*',\s*url:\s*')"
        r"((?:[^'\\]|\\.)*)(')",
        re.S,
    )

    def swap_url(m):
        tract_id = int(m.group(2))
        url = pdf_urls.get(tract_id)
        if not url:
            return m.group(0)
        return m.group(1) + escape_js(url) + m.group(4)

    out = entry_re.sub(swap_url, source)

    # Apercus
    def swap_previews(m):
        body = re.sub(
            r"(\d+):\s*'(?:[^'\\]|\\.)*'",
            lambda e: f"{e.group(1)}: '{escape_js(thumb_urls[int(e.group(1))])}'"
            if int(e.group(1)) in thumb_urls
            else e.group(0),
            m.group(2),
        )
        return m.group(1) + body + m.group(3)

    out = block_re.sub(swap_previews, out)
    out = out.replace("const PREVIEW_BASE = './';", "const PREVIEW_BASE = '';")

    # Les miniatures Drive refusent les requetes avec Referer externe.
    out = out.replace(
        "            const img = document.createElement('img');\n"
        "            img.alt = tract.title;",
        "            const img = document.createElement('img');\n"
        "            img.referrerPolicy = 'no-referrer';\n"
        "            img.alt = tract.title;",
        1,
    )

    # Les URLs Drive sont deja encodees.
    out = out.replace(
        "img.src = PREVIEW_BASE + relPath.split('/').map(encodeURIComponent).join('/');",
        "img.src = PREVIEW_BASE + relPath;",
        1,
    )

    # Metadonnees SharePoint internes, sans objet sur une page publique.
    out = re.sub(
        r"\n<!--\[if gte mso 9\]>.*?<!\[endif\]-->\n", "\n", out, flags=re.S
    )

    with open(DST, "w", encoding="utf-8") as f:
        f.write(out)

    print(f"{os.path.basename(DST)} genere")
    print(f"  apercus Drive : {len(thumb_urls)}/{len(previews)}")
    print(f"  liens PDF Drive : {len(pdf_urls)}/{len(previews)}")
    if fallbacks:
        print(f"\n  {len(fallbacks)} PDF absent(s), lien reporte sur l'apercu :")
        for tract_id, path in fallbacks:
            print(f"    id {tract_id} : {path}")
    if missing:
        print(f"\n  {len(missing)} fichier(s) sans ID Drive :")
        for kind, tract_id, path in missing:
            print(f"    [{kind}] id {tract_id} : {path}")


if __name__ == "__main__":
    main()
