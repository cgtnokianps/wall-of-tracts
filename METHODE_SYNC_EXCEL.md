# Methode de mise a jour des tracts

## Principe

Le fichier `tracts.xlsx` est la source de verite pour les informations des tracts.

Ce fichier `.md` est la memoire de la methode. Le mettre a jour avant un commit s'il y a du nouveau (colonnes, chemins, procedure, structure HTML).

Les fichiers HTML sont des sorties generees a partir de ces donnees :

- `index.html` contient toutes les informations des tracts dans `tractsData`.
- `index_standalone.html` est genere automatiquement par `build_standalone.py`.

Ne pas modifier directement `index_standalone.html` : toute modification serait perdue a la prochaine generation.

## Structure du fichier Excel

Feuille : `Sheet1`

Les noms dans H et I doivent correspondre **exactement** aux fichiers existants (`copies/` et `previews/`). On aligne Excel et `index.html` sur les fichiers, on ne renomme pas les fichiers pour coller au tableau.

| Colonne | En-tete | Contenu | Destination HTML |
| --- | --- | --- | --- |
| A | Annee | Annee de diffusion | Groupe `tractsData` |
| B | ID | Identifiant unique | `tractsData[id].id` |
| C | Titre (tractsData) | Titre affiche | `tractsData[id].title` |
| D | Objet du courriel | Objet exact du mail | `tractsData[id].subject` |
| E | Date de diffusion | Date (serie Excel ou texte) | `tractsData[id].date` |
| F | Resume | Resume du tract | `tractsData[id].summary` |
| G | URL PDF | URL SharePoint du PDF | `tractsData[id].pdfUrl` |
| H | filename pdf | Nom du fichier dans `copies/` (extension `.pdf`) | Dernier segment de `pdfUrl` |
| I | preview filename | Nom du fichier dans `previews/` (extension `.jpg`) | `tractsData[id].previewPath` = `previews/` + I |

Convention d'apercu : `{stem du PDF}_page-0001.jpg`.

Les tracts 2022 (IDs 102 a 117) peuvent avoir D et F vides.

Chaque nouveau tract doit avoir un ID unique.

## Procedure pour un nouveau tract

1. Ajouter le PDF dans `copies/` et l'image d'apercu dans `previews/`.
2. Ajouter une ligne dans `tracts.xlsx`.
3. Verifier les champs C a I :
   - titre ;
   - objet exact du mail ;
   - date de diffusion ;
   - resume ;
   - URL PDF ;
   - nom de fichier PDF (H, identique au fichier dans `copies/`) ;
   - nom de fichier JPG (I, identique au fichier dans `previews/`).
4. Ajouter l'entree correspondante dans le tableau `tractsData` de `index.html` (titre, objet, date, resume, URL PDF, apercu).
5. Verifier le resultat dans `index.html`.
6. Au moment du commit, regenerer la page autonome et l'inclure dans le commit :

```powershell
python build_standalone.py
```

Ne pas regenerer `index_standalone.html` pendant les etapes intermediaires. Exception : le faire immediatement si la verification ne peut pas se faire dans `index.html`.

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

Dans `tractsData`, utiliser une date lisible en francais, par exemple :

```javascript
{
    id: 36,
    title: 'Titre du tract',
    subject: 'Objet du courriel',
    date: '30 septembre 2026',
    summary: 'Resume du tract.',
    pdfUrl: 'https://.../copies/fichier.pdf',
    previewPath: 'previews/fichier_page-0001.jpg'
}
```

## Controle apres mise a jour

Verifier les points suivants :

- le PDF existe dans `copies/` et le JPG dans `previews/` ;
- l'ID est unique ;
- H se termine par `.pdf` et I par `.jpg` ;
- H et I correspondent exactement aux noms de fichiers ;
- `index.html` reprend les memes noms (URL PDF et `previewPath`) ;
- l'objet, la date et le resume viennent du fichier Excel ;
- le nouveau tract apparait dans `index.html`.

Au moment du commit seulement :

- `python build_standalone.py` se termine sans erreur ;
- le nouveau tract apparait dans `index_standalone.html` ;
- le nombre total de tracts affiche par le script a augmente de 1 ;
- aucun apercu n'est signale comme introuvable.

## En cas d'erreur de generation

Le script utilise PyMuPDF. Si l'import echoue :

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install PyMuPDF
python build_standalone.py
```

La lecture de `tracts.xlsx` peut se faire avec Excel ou un lecteur XLSX. Si `openpyxl` n'est pas installe, il ne faut pas modifier le classeur pour cette raison : la structure XLSX peut etre lue avec les bibliotheques deja disponibles.
