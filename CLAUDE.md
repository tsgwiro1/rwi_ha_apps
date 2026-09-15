# Arbeitsanweisungen für dieses Repository

Monorepo mit Home-Assistant-Apps (bis HA 2026.2 «Add-ons» genannt). Jeder
Unterordner ist eine eigenständige App mit eigener Version, eigenem
`CHANGELOG.md`, eigener `README.md` und eigenem Posteingang `OFFENE-PUNKTE.md`.
Der Ordnername ist der `slug` aus der `config.yaml`.

Vorlage für Aufbau und Regeln ist `~/repos/rwi_esphome_apps`. Dort nachlesen ist
erlaubt, geändert wird dort aus diesem Repo nichts.

## Die zwei Orte einer App

| Ort | Pfad | Rolle |
| :--- | :--- | :--- |
| Repo | `~/repos/rwi_ha_apps/<slug>/` | versionierte Quelle |
| HA | `ha:/addons/<slug>/` | installierte Kopie, HA baut daraus die App |

Auf HA sind die Apps **lokal** installiert (Repository `local`, Slug
`local_<slug>`), nicht über die GitHub-Adresse aus `repository.yaml`. Die
GitHub-Adresse ist für andere, die das Repo einbinden. Geänderter Code wirkt auf
HA erst, wenn er unter `/addons/<slug>/` liegt **und** die App neu gebaut ist.

**Immer erst diffen, dann einspielen.** Bei Abweichung nicht raten, welcher
Stand gilt, sondern nachfragen. Belegt am 2026-09-15: In
`/addons/pv_wp_control/src/modbus_client.py` standen zwei Zeilen, die das Repo
nicht kennt – HA lief also nicht mit dem Code, der im Repo als v1.0.11 steht.

```sh
rsync -a --rsync-path="sudo rsync" ha:/addons/<slug>/ <scratchpad>/<slug>/
diff -r -x .DS_Store -x OFFENE-PUNKTE.md <slug> <scratchpad>/<slug>
```

`scp` scheitert, HA-OS hat kein SFTP-Subsystem. Der `ha`-Befehl über SSH hat
kein API-Token; Zustand und Version der Apps liefert das HA-MCP
(`ha_get_app`).

**Einspielen und Neubau nur nach Rückfrage.** `pv_wp_control` steuert die
Wärmepumpe, `cm4_sys_monitor` den Lüfter und die Akkuüberwachung des HA-Boards
selbst.

## Ein Wert, eine Stelle

**Jeder Parameter und jede Konfiguration steht genau einmal. Keine Doppelung.**
Die Regel gilt für alle Chats; der ausformulierte Wortlaut samt Begründung steht
in `~/repos/rwi_esphome_apps/CLAUDE.md`, gleichnamiger Abschnitt. In einer App
heisst das:

* **Einstellbare Vorgaben** stehen nur unter `options:` in `config.yaml`. Der
  Code liest sie aus den Optionen und hat **keinen eigenen Rückfallwert**
  (`opts.get('x', 180)` ist ein zweiter Wert).
* **Feste Werte im Code** stehen einmal als benannte Konstante, alle anderen
  Stellen verweisen darauf.
* **README, DOCS und `translations/`** nennen keine Vorgaben und Grenzen,
  sondern verweisen auf die Optionen. Auch Fliesstext zählt.
* **Die Version** steht nur in `config.yaml`; der Code liest sie von dort
  (`bashio::addon.version`, oder wie in `pv_wp_control/src/config.py`).

Belegt am 2026-09-15, zweimal: Das README von `cm4_sys_monitor` nennt
`fanmaxtemp` 55, die `config.yaml` 60. In `pv_wp_control/src/config.py` steht
als Rückfall `startup_no_limit_s` 180, in `config.yaml` seit v1.0.10 1800.

**Wie umsetzen:** `.claude/hooks/single-source.sh` blockiert `git commit`,
solange `config.yaml`, `translations/`, `dashboard.yaml`, Python-Code oder ein
App-README/DOCS gestagt und die Prüfung nicht quittiert ist, und legt die neuen
und geänderten Zeilen vor. Quittiert wird mit
`.claude/hooks/single-source.sh --ok` – **erst nach der Prüfung**. Die Marke
hängt am Inhalt des Index und verfällt, sobald danach noch etwas gestagt wird.

Grenzfälle benennen statt stillschweigend durchwinken. Registernummern,
Portnummern und Bitmasken sind oft zufällig gleich und keine Doppelung.

## Geheimnisse und Personenbezug

Zugangsdaten gehören in die **App-Optionen in HA**, nie ins Repo. In
`config.yaml` steht dafür nur der Schematyp (`password`, `str`) und unter
`options:` kein Wert. Dasselbe gilt für alles übrige Personenbezogene – private
Netzadressen, MAC-Adressen, Koordinaten, Seriennummern, Namen,
E-Mail-Adressen –, und zwar **auch in README, CHANGELOG, `OFFENE-PUNKTE.md` und
Kommentaren**. Begründung im globalen `CLAUDE.md`: Git-Historie ist dauerhaft.

Bewusst im Repo: Name und E-Mail als Maintainer in `repository.yaml`, der Name
in `LICENSE`.

**Wie umsetzen:** `.claude/hooks/sensitive-guard.sh` durchsucht vor jedem Commit
die gestagten Zeilen und blockiert bei Funden; die Muster stehen in
`scan-sensitive.py`. Quittiert wird nach der Klärung mit `--ok`. Bilder, PDFs
und `.docx` kann er nicht durchsuchen und meldet sie zum Selberansehen – Bilder
tragen EXIF, Office-Dateien und PDFs den Autornamen. Beispielwerte in der Doku
anonymisieren: `192.0.2.0/24` für Adressen, `AA:BB:CC:DD:EE:FF` für MACs.

## Versionierung

Jede inhaltliche Änderung an einer App hebt deren Version nach SemVer
(Bugfix → Patch, Feature → Minor, Breaking → Major). Breaking ist auch alles,
was in HA Entity-IDs ändert (siehe unten). Fünf Stellen gehören nachgezogen:

1. `version:` in `<slug>/config.yaml`
2. neuer datierter Abschnitt in `<slug>/CHANGELOG.md`, mit Link-Fussnote
3. Versions-Badge in `<slug>/README.md`
4. Versionsspalte in der Tabelle im Root-`README.md`
5. annotierter Git-Tag `<slug>/v<version>`

Neue CHANGELOG-Abschnitte folgen [Keep a Changelog](https://keepachangelog.com/de/1.1.0/):
`## [2.1.0] - 2026-09-15`, deutsche Rubriken (Hinzugefügt, Geändert, Entfernt,
Behoben, Sicherheit), am Ende die Fussnote
`[2.1.0]: https://github.com/tsgwiro1/rwi_ha_apps/tree/<slug>/v2.1.0`.

Reine Doku-Commits heben die Version **nicht** an und sagen das im
Commit-Body ausdrücklich.

## Git

Commits erst nach Rogers Freigabe, gepusht wird nie aus dem Terminal – beides
steht im globalen `CLAUDE.md`. Tags gehen beim Push in Fork nur mit, wenn die
Option aktiv ist.

**Ein Projekt pro Commit.** Keine Vermischung zwischen Apps oder zwischen einer
App und repo-weiten Dateien. Die zugehörige Zeile im Root-`README.md` darf mit,
sofern sie dieselbe App betrifft. Repo-weit sind `CLAUDE.md`, `.claude/`,
`.gitignore`, `repository.yaml`, `LICENSE` und das Root-`README.md` ausserhalb
der App-Zeilen.

Commit-Messages auf Deutsch, **ohne** `Co-Authored-By`-Zeile:

```
<slug>: V2.0.4 – Kurzbeschreibung
<slug>: Doku – Kurzbeschreibung
Repo: Kurzbeschreibung
```

Die Historie vor dem 2026-09-15 (`feat(v1.0.11): …`) bleibt, wie sie ist.

**Vorsicht bei `git add <slug>/`** — das zieht untracked Dateien mit rein. Vor
dem Commit `git diff --cached --name-only` prüfen.

Der Tag zeigt auf den letzten Commit, der die App in dieser Version berührt hat:

```sh
GIT_COMMITTER_DATE="$(git log -1 --format=%aI <commit>)" \
  git tag -a "<slug>/v<version>" <commit> -m "<slug> V<version> - <beschreibung>"
```

Rückwirkend getaggt am 2026-09-15. Versionen, die nie als Commit im Repo
standen (`pv_wp_control` 1.0.4 bis 1.0.6), haben keinen Tag.

## Chat-Aufteilung und Posteingang

Ein Chat je App, dazu der **Common-Chat** für alles Repo-weite. Chat-Grenze =
Commit-Grenze. Mehrere Chats dürfen offen sein, aber nur einer schreibt und
committet gerade — Git-Index und Arbeitsverzeichnis sind geteilt.

**Chats im Repo-Wurzelordner öffnen**, auch App-Chats. Das Gedächtnis von
Claude Code hängt am Arbeitsverzeichnis; ein Chat im Unterordner bekommt ein
eigenes, leeres. `CLAUDE.md` findet er zwar, das Gedächtnis nicht.

Ein App-Ordner gehört seinem Chat (globale Regel «Arbeitsbereiche»). Aus einem
anderen Chat ist dort genau eines erlaubt: einen Auftrag an
`<slug>/OFFENE-PUNKTE.md` **anfügen** — mit Datum, Herkunft und genug
Zusammenhang. Nicht umsetzen, nicht abhaken, nichts streichen.

`OFFENE-PUNKTE.md` gehört ins Repo und wird mit der App committet, vom Chat der
App. Für Personenbezug gilt dort dasselbe wie überall.

## Home Assistant

* **Entity-IDs nicht brechen.** `unique_id`s, Gerätenamen und die Schlüssel der
  MQTT-Nutzlast bleiben stehen; daran hängen in HA Views, Vorlagen und
  Automationen. Eine Änderung ist Breaking und wird vorher angekündigt.
* HA-seitige Arbeit (Views, Automationen, Template-Sensoren) läuft in
  `~/homeassistant`, nicht hier. Von hier aus dort nur lesen oder einen Auftrag
  in die `OFFENE-PUNKTE.md` des Themenordners anfügen.
* Eine MQTT-Meldung ist keine Datenbankzeile: HA schreibt nur bei geändertem
  Zustand. Schreiblast messen, nicht aus der Melderate schliessen.
