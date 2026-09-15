#!/bin/bash
# Erzwingt vor jedem Commit, der Optionen, Code oder App-Doku beruehrt, die
# Einzelquellen-Pruefung: Jeder Parameter, jede Konfiguration steht nur an
# EINER Stelle.
#
# Aufruf 1 (durch den PreToolUse-Hook): liest das Hook-JSON von stdin, blockiert
#   den Commit und schreibt die zu pruefenden Zeilen nach stderr.
# Aufruf 2 (durch Claude, nach der Pruefung): mit --ok, setzt die Marke fuer
#   genau diesen Stand des Index; der naechste Commit laeuft dann durch.
#
# Die Marke haengt am Inhalt des Index. Wird nach der Pruefung noch etwas
# gestaged oder geaendert, verfaellt sie und die Pruefung wird erneut verlangt.

set -u

if [ "${1:-}" != "--ok" ]; then
  # stdin ist das Hook-JSON. Alles ausser einem git commit geht sofort durch -
  # auch verkettete Formen wie "cd x && git commit" oder "git -C . commit".
  CMD=$(cat | sed 's/[[:cntrl:]]/ /g')
  echo "$CMD" | grep -qE 'git[^;&|]*\bcommit\b' || exit 0
fi

cd "$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

# Ohne Schraegstrich im Muster faellt das Root-README heraus.
PFADE=('*/config.yaml' '*/translations/*.yaml' '*/dashboard.yaml' '*.py'
       '*/README.md' '*/DOCS.md')

STAGED=$(git diff --cached --name-only --diff-filter=ACMR -- "${PFADE[@]}")
[ -z "$STAGED" ] && exit 0

KEY=$(git diff --cached -- "${PFADE[@]}" | shasum | cut -d' ' -f1)
MARK="$(git rev-parse --git-dir)/claude-single-source"

if [ "${1:-}" = "--ok" ]; then
  echo "$KEY" > "$MARK"
  echo "Einzelquellen-Pruefung quittiert. Der Commit laeuft jetzt durch."
  exit 0
fi

[ -f "$MARK" ] && [ "$(cat "$MARK")" = "$KEY" ] && exit 0

{
  echo "EINZELQUELLEN-PRUEFUNG (Repo-Regel, gilt fuer jeden Chat)"
  echo
  echo "Alle Parameter und Konfigurationen stehen nur an EINER Stelle."
  echo "Keine Doppelung. Gestagt sind:"
  echo "$STAGED" | sed 's/^/  /'
  echo
  echo "Diese Zeilen kommen neu dazu oder aendern sich - jede einzeln pruefen:"
  git diff --cached -U0 -- "${PFADE[@]}" | awk '
    /^\+\+\+ b\// { f = substr($0, 7); next }
    /^@@/ { match($0, /\+[0-9]+/); n = substr($0, RSTART + 1, RLENGTH - 1) - 1; next }
    /^\+/ {
      n++; t = substr($0, 2)
      if (t ~ /^[[:space:]]*#/) next
      if (t ~ /[0-9]+\.[0-9]+|(^|[^A-Za-z_0-9])[0-9][0-9]+|^[[:space:]]*[a-z_0-9]+:[[:space:]]*[^[:space:]]|\.get\(/)
        printf "  %s:%d  %s\n", f, n, substr(t, 1, 100)
    }' | head -60
  echo
  echo "Fuer jeden Wert beantworten:"
  echo "  1. Steht derselbe Wert schon woanders - unter options: in config.yaml,"
  echo "     als Rueckfallwert im Code (opts.get('x', 180)), als zweite Konstante,"
  echo "     in README, DOCS oder translations/?"
  echo "  2. Wenn ja: EINE Stelle ist die Quelle. Vorgaben nur in config.yaml,"
  echo "     feste Werte als benannte Konstante, die Doku verweist."
  echo "  3. Grenzfaelle nennen statt stillschweigend durchwinken."
  echo
  echo "Danach quittieren und den Commit wiederholen:"
  echo "  .claude/hooks/single-source.sh --ok"
} >&2
exit 2
