# Methode de mise a jour des tracts

## Principe

Le fichier `tracts.xlsx` est la source de verite pour les informations des tracts.

Ce fichier `.md` est la memoire de la methode. Le mettre a jour avant un commit s'il y a du nouveau (colonnes, chemins, procedure, structure HTML).

`tracts_html_files/tracts-cgt-2023-2026.html` est la seule page du mur. Les cartes sont ecrites directement dans cette page. Le logo et le bandeau sont dans `tracts_html_files/images/`, et les apercus dans `tracts_html_files/previews/`. Il n'y a pas de script de generation.

## Structure du fichier Excel

Feuille : `Sheet1`

Les ressources sont dans `tracts_html_files/` : PDF dans `copies/`, apercus dans `previews/`, logo et bandeau dans `images/`.

Les noms dans H et I doivent correspondre **exactement** aux fichiers existants (`tracts_html_files/copies/` et `tracts_html_files/previews/`). On aligne Excel et `tracts_html_files/tracts-cgt-2023-2026.html` sur les fichiers, on ne renomme pas les fichiers pour coller au tableau.

| Colonne | En-tete | Contenu | Destination HTML |
| --- | --- | --- | --- |
| A | Annee | Annee de diffusion | Section de l'annee dans la page |
| B | ID | Identifiant unique | Reste dans le classeur |
| C | Titre (tractsData) | Titre affiche | Attribut `title` de la carte |
| D | Objet du courriel | Objet exact du mail | `h3.card-title` |
| E | Date de diffusion | Date (serie Excel ou texte) | `p.card-meta`, en francais |
| F | Resume | Resume du tract | `p.card-summary` |
| G | URL PDF | URL SharePoint du PDF | `href` de la carte |
| H | filename pdf | Nom du fichier dans `tracts_html_files/copies/` (extension `.pdf`) | Dernier segment de l'URL |
| I | preview filename | Nom du fichier dans `tracts_html_files/previews/` (extension `.jpg`) | `img` de la carte : `previews/` + I |

Convention d'apercu : `{stem du PDF}_page-0001.jpg`.

Les tracts 2022 (IDs 102 a 117) peuvent avoir D et F vides.

Chaque nouveau tract doit avoir un ID unique.

## Procedure pour un nouveau tract

1. Ajouter le PDF dans `tracts_html_files/copies/` et l'image d'apercu dans `tracts_html_files/previews/`.
2. Ajouter une ligne dans `tracts.xlsx`.
3. Verifier les champs C a I :
   - titre ;
   - objet exact du mail ;
   - date de diffusion ;
   - resume ;
   - URL PDF ;
   - nom de fichier PDF (H, identique au fichier dans `tracts_html_files/copies/`) ;
   - nom de fichier JPG (I, identique au fichier dans `tracts_html_files/previews/`).
4. Ajouter la carte dans la section de la bonne annee de `tracts_html_files/tracts-cgt-2023-2026.html` : lien vers l'URL PDF, apercu `previews/` + nom JPG, objet, date et resume.
5. Verifier le resultat dans la page.

## Dates Excel

Une date peut etre stockee dans le XLSX comme un nombre de serie Excel, et non comme du texte.

Exemple : `46295` correspond au `30 septembre 2026`.

Pour convertir une date Excel en Python :

```python
from datetime import datetime, timedelta

date_excel = 46295
date_lisible = datetime(1899, 12, 30) + timedelta(days=date_excel)
print(date_lisible.strftime("%d/%m/%Y"))
```

Dans la page, ecrire la date en francais, par exemple `30 septembre 2026`.

```html
<a class="card" href="https://.../tracts_html_files/copies/fichier.pdf" target="_self" rel="noopener noreferrer" title="Titre du tract">
    <div class="card-preview"><img src="previews/fichier_page-0001.jpg" alt="Titre du tract"></div>
    <div class="card-content">
        <h3 class="card-title">Objet du courriel</h3>
        <p class="card-meta">30 septembre 2026</p>
        <p class="card-summary">Resume du tract.</p>
    </div>
</a>
```

## Controle apres mise a jour

Verifier les points suivants :

- le PDF existe dans `tracts_html_files/copies/` et le JPG dans `tracts_html_files/previews/` ;
- l'ID est unique ;
- H se termine par `.pdf` et I par `.jpg` ;
- H et I correspondent exactement aux noms de fichiers ;
- `tracts_html_files/tracts-cgt-2023-2026.html` reprend les memes noms (URL du PDF et `src` de l'apercu) ;
- l'objet, la date et le resume viennent du fichier Excel ;
- le nouveau tract apparait dans `tracts_html_files/tracts-cgt-2023-2026.html`.

La lecture de `tracts.xlsx` peut se faire avec Excel ou un lecteur XLSX. Si `openpyxl` n'est pas installe, il ne faut pas modifier le classeur pour cette raison : la structure XLSX peut etre lue avec les bibliotheques deja disponibles.
