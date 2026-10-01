# Methode de mise a jour des tracts

## Principe

Le fichier `tracts.xlsx` est la source de verite pour les informations des tracts.

Les fichiers HTML sont des sorties generees a partir de ces donnees :

- `index.html` contient les chemins et titres dans `tractsData`, ainsi que les informations d'affichage dans `tractsInfo`.
- `index_standalone.html` est genere automatiquement par `build_standalone.py`.

Ne pas modifier directement `index_standalone.html` : toute modification serait perdue a la prochaine generation.

## Structure du fichier Excel

Feuille : `Sheet1`

| Colonne | Contenu | Destination HTML |
| --- | --- | --- |
| A | Annee | Groupe `tractsData` |
| B | ID | Identifiant commun entre `tractsData` et `tractsInfo` |
| C | Titre du tract | `tractsData[id].title` |
| D | Objet du courriel | `tractsInfo[id].subject` |
| E | Date de diffusion | `tractsInfo[id].date` |
| F | Resume | `tractsInfo[id].summary` |
| G | Chemin PDF | `tractsData[id].pdfPath` |
| H | Chemin apercu JPG | `tractsData[id].previewPath` |

Chaque nouveau tract doit avoir un ID unique.

## Procedure pour un nouveau tract

1. Ajouter le PDF et l'image d'aperçu dans le dossier de l'annee.
2. Ajouter une ligne dans `tracts.xlsx`.
3. Verifier les champs C a H :
   - titre ;
   - objet exact du mail ;
   - date de diffusion ;
   - resume ;
   - chemin PDF ;
   - chemin JPG.
4. Ajouter l'entree correspondante dans le tableau `tractsData` de `index.html`.
5. Ajouter l'entree correspondante dans `tractsInfo` de `index.html`.
6. Regenerer la page autonome :

```powershell
.\.venv\Scripts\Activate.ps1
python build_standalone.py
```

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

Dans `tractsInfo`, utiliser une date lisible en francais, par exemple :

```javascript
36: {
    subject: 'Objet du courriel',
    date: '30 septembre 2026',
    summary: 'Resume du tract.'
}
```

## Controle apres mise a jour

Verifier les points suivants :

- le PDF et le JPG existent ;
- l'ID est unique ;
- le chemin PDF et le chemin JPG correspondent exactement aux noms de fichiers ;
- l'objet, la date et le resume viennent du fichier Excel ;
- `python build_standalone.py` se termine sans erreur ;
- le nouveau tract apparait dans `index.html` et `index_standalone.html` ;
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
