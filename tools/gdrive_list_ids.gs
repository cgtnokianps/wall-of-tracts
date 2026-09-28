/**
 * Liste recursivement le dossier Drive et affiche "chemin relatif;FILE_ID".
 *
 * Utilisation :
 *   1. https://script.google.com -> Nouveau projet
 *   2. Coller ce fichier, executer listIds()
 *   3. Autoriser l'acces, puis copier la sortie du journal (Ctrl+Entree)
 *   4. Coller dans gdrive_ids.csv a cote de build_gdrive.py
 */

const ROOT_FOLDER_ID = '1m6U-27DeG-3x0Jjx4fomwnz4Vp7BjuVb';

function listIds() {
  const lines = [];
  walk(DriveApp.getFolderById(ROOT_FOLDER_ID), '', lines);
  lines.sort();
  const out = lines.join('\n');
  Logger.log(out);
  DriveApp.createFile('gdrive_ids.csv', out, MimeType.PLAIN_TEXT);
}

function walk(folder, prefix, lines) {
  const files = folder.getFiles();
  while (files.hasNext()) {
    const f = files.next();
    lines.push(prefix + f.getName() + ';' + f.getId());
  }
  const subs = folder.getFolders();
  while (subs.hasNext()) {
    const s = subs.next();
    walk(s, prefix + s.getName() + '/', lines);
  }
}
