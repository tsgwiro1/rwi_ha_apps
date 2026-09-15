#!/bin/bash
# Haelt Personenbezogenes, Zugangsdaten, Geodaten und Metadaten aus dem Repo.
#
# Aufruf 1 (durch den PreToolUse-Hook): liest das Hook-JSON von stdin und
#   blockiert den Commit, solange die gestagten Zeilen Funde enthalten.
# Aufruf 2 (durch Claude, nach der Klaerung): mit --ok.
#
# Die Marke haengt am Inhalt des Index und verfaellt bei jeder Aenderung.
# Grundlage ist die Regel in ~/.claude/CLAUDE.md, «Git: keine persoenlichen
# Daten in ein Repository».

set -u

if [ "${1:-}" != "--ok" ]; then
  CMD=$(cat | sed 's/[[:cntrl:]]/ /g')
  echo "$CMD" | grep -qE 'git[^;&|]*\bcommit\b' || exit 0
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
git diff --cached --quiet && exit 0

KEY=$(git diff --cached | shasum | cut -d' ' -f1)
MARK="$(git rev-parse --git-dir)/claude-sensitive-guard"

if [ "${1:-}" = "--ok" ]; then
  echo "$KEY" > "$MARK"
  echo "Funde geklaert und quittiert. Der Commit laeuft jetzt durch."
  exit 0
fi

[ -f "$MARK" ] && [ "$(cat "$MARK")" = "$KEY" ] && exit 0

FUNDE=$(git diff --cached | "$(git rev-parse --show-toplevel)/.claude/hooks/scan-sensitive.py")
[ -z "$FUNDE" ] && exit 0

{
  echo "PERSONENBEZOGENES / GEHEIMNISSE - $(echo "$FUNDE" | wc -l | tr -d ' ') Fund(e) in den gestagten Zeilen"
  echo
  echo "$FUNDE" | awk -F'\t' '{printf "  %-46s %-38s %s\n", $1, $2, substr($3,1,80)}'
  echo
  echo "Git-Historie ist dauerhaft. Ein spaeterer Commit entfernt nichts - der"
  echo "Wert bleibt in Forks, Klonen und Plattform-Caches. Die Entscheidung faellt"
  echo "hier, vor dem Commit."
  echo
  echo "Je Fund einer der Wege:"
  echo "  * Echtes Geheimnis (Passwort, Token, Key): gehoert in die App-Optionen"
  echo "    in HA. In config.yaml nur der Schematyp (password, str), unter"
  echo "    options: kein Wert."
  echo "  * Eigene Netzadresse als Vorgabe unter options: oder als Rueckfallwert"
  echo "    im Code: Vorgabe weglassen, die Adresse gehoert in die App-Optionen."
  echo "  * Doku, die einen echten Wert zeigt: anonymisieren. Fuer Adressen die"
  echo "    Dokumentationsbereiche 192.0.2.0/24 oder 198.51.100.0/24, fuer MACs"
  echo "    AA:BB:CC:DD:EE:FF, fuer Koordinaten einen erfundenen Ort."
  echo "  * Datei gehoert gar nicht ins Repo: aus dem Index nehmen und in"
  echo "    .gitignore aufnehmen, mit 'git check-ignore -v <datei>' gegenpruefen."
  echo "  * Nicht durchsuchbare Datei (PDF, STEP, Bild, minifiziert): selbst"
  echo "    ansehen. Bilder tragen oft EXIF mit Ort und Geraet, PDFs den Autor."
  echo "  * Wirklich unbedenklich: benennen, warum - nicht stillschweigend"
  echo "    durchwinken."
  echo
  echo "Danach quittieren und den Commit wiederholen:"
  echo "  .claude/hooks/sensitive-guard.sh --ok"
} >&2
exit 2
