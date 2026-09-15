# Offene Punkte «PV Wärmepumpen Steuerung»

Posteingang dieser App. Einträge werden angefügt; erledigt meldet, wer an der
App arbeitet.

---

## 2026-09-15 – aus dem Common-Chat: installierte Kopie auf HA weicht vom Repo ab

Beim Vergleich von `ha:/addons/pv_wp_control/` mit dem Repo (Stand `aaebb86`,
v1.0.11) gefunden. Alle übrigen Dateien sind identisch, nur
`src/modbus_client.py` nicht. Auf HA stehen nach Zeile 150 zwei Zeilen mehr:

```python
            self.client.write_register(10040, 0, slave=self.config.wp_slave_id)
            time.sleep(1.0)
```

Die App auf HA läuft also nicht mit dem Code, der im Repo als v1.0.11 steht.
Nicht geraten, welcher Stand gilt – klären:

1. Welcher Stand ist der gewollte? Die Zeilen setzen Register 10040 vor dem
   folgenden Schreibzugriff auf 0.
2. Gilt der HA-Stand: ins Repo übernehmen, Version heben, CHANGELOG.
3. Gilt der Repo-Stand: nach `/addons/pv_wp_control/` zurückspielen und die App
   neu bauen.

Abgleich zum Nachvollziehen:

```sh
rsync -a --rsync-path="sudo rsync" ha:/addons/pv_wp_control/ <tmp>/
diff -r pv_wp_control <tmp>
```

Zwei weitere Kleinigkeiten, beim Lesen aufgefallen:

- `config.yaml`: `url: "https://github.com/your-repo/pv-wp-control"` ist ein
  Platzhalter. Die CM4-App verweist auf
  `https://github.com/tsgwiro1/rwi_ha_apps/tree/main/<slug>`.
- `config.yaml`: `wp_ip` hat als Vorgabe eine private Adresse aus dem eigenen
  Netz. Sie steht schon im Repo; bei einer Überarbeitung einen neutralen
  Vorgabewert oder `str` ohne Vorgabe erwägen.

**Stand 2026-09-15, App-Chat – V1.0.12:**

- *Erledigt:* Der HA-Stand gilt. Die zwei Zeilen stehen jetzt im Repo, die
  Version ist 1.0.12, das CHANGELOG ist nachgeführt. Die Datei auf HA war am
  2026-05-13 geändert worden, am Morgen nach v1.0.9. Die Zeilen schalten im
  Anlauf das Soft Limit ab, damit der Verdichter nicht an einem alten Limit
  scheitert. Auf HA muss der Code nicht neu eingespielt werden, dort weichen
  nur noch `config.yaml` und CHANGELOG ab.
- *Erledigt:* `url` in der `config.yaml` zeigt auf dieses Repository.
- *Erledigt (V1.1.0):* `wp_ip` hat keine Vorgabe mehr.

---

## 2026-09-15 – aus dem Common-Chat: Rückfallwerte in `src/config.py` doppeln die Optionen

Neue Repo-Regel «Ein Wert, eine Stelle» (steht in `CLAUDE.md`, ein Hook prüft
sie vor jedem Commit): Vorgaben stehen nur unter `options:` in `config.yaml`,
der Code hat keinen eigenen Rückfallwert.

`_load_from_options_file()` in `src/config.py` (Zeilen 65–90) wiederholt jede
Vorgabe als `opts.get('…', <wert>)`. Eine davon ist schon auseinandergelaufen:

| Option | `config.yaml` | `src/config.py` Z. 74 |
| :--- | :--- | :--- |
| `startup_no_limit_s` | 1800 (seit v1.0.10) | 180 |

Zeile 65 trägt ausserdem die private Adresse der Wärmepumpe als Rückfall.
`register_timeout_min` (Z. 49 und 76) und `safety_hysteresis` (Z. 51 und 90)
stehen je zweimal im selben File.

Zu klären: Wird der Pfad über `/data/options.json` überhaupt noch gebraucht?
`run.sh` übergibt die Optionen als Argumente. Wenn ja, die Rückfallwerte
streichen oder aus einer Stelle beziehen; wenn nein, den Pfad entfernen.

**Stand 2026-09-15, App-Chat – V1.1.0:**

- *Erledigt:* Umgekehrt gelöst: Der Argument-Pfad ist weg, das Programm liest
  nur noch `/data/options.json`, ohne Rückfallwerte. Fehlt eine Pflichtoption,
  bricht es mit Meldung ab. `register_timeout_min` war unbenutzt und ist
  entfernt, die Sicherheits-Hysterese steht einmal in `src/safety.py`.
- *Erledigt:* Weitere Doppelungen im Code als Konstanten benannt, Dashboard-
  Vorgaben nur noch in `DEFAULT_PARAMS`, `translations/` ohne Vorgaben.

## 2026-09-15 – aus dem Common-Chat: neue Repo-Konventionen

Stehen jetzt in `CLAUDE.md` im Repo-Wurzelordner, hier nur der Hinweis:

- Commit-Messages `pv_wp_control: V1.0.12 – Kurzbeschreibung`.
- Tags `pv_wp_control/v<version>` sind rückwirkend gesetzt für 1.0.3, 1.0.7
  bis 1.0.11. 1.0.4 bis 1.0.6 standen nie als Commit im Repo.
- Neue CHANGELOG-Abschnitte nach Keep a Changelog: `## [1.0.12] - Datum`,
  deutsche Rubriken, Link-Fussnote. Das jetzige CHANGELOG (`### v1.0.11
  (aktuell)`, ohne Datum) bei Gelegenheit umstellen.
- Diese Datei gehört ins Repo und wird von diesem Chat mit der App committet.

**Nachtrag:** Die private Adresse der Wärmepumpe steht an drei Stellen –
`config.yaml` Z. 38, `src/config.py` Z. 65 **und** `README.md` Z. 254
(Konfigurationstabelle, Spalte Vorgabe). Der neue Commit-Hook meldet sie, sobald
eine dieser Zeilen geändert wird. Im README anonymisieren (`192.0.2.10`) oder
auf `config.yaml` verweisen.

**Stand 2026-09-15, App-Chat – V1.1.0:** Die Adresse steht nicht mehr in
`config.yaml`, `src/config.py` und der README-Tabelle (dort «Pflicht»). Die
übrigen Vorgaben im README folgen mit der Doku-Überarbeitung.

**Stand 2026-09-15, App-Chat – Doku:** *Erledigt.* Das README nennt keine
Vorgaben, Bereiche und Intervalle mehr und verweist auf `config.yaml`,
`DEFAULT_PARAMS`, `src/mqtt_handler.py` und die Konstanten.

---

## 2026-09-15 – aus dem App-Chat: `ha_connection_timeout_min` löst keine Abschaltung aus

Beim Überarbeiten des README gefunden. `main.py` übergibt der Zustandsmaschine
`ha_connected` (aus `HAClient.is_connected()`, also nach
`ha_connection_timeout_min`), `StateMachine.evaluate()` wertet es aber nicht
aus. Bleiben die Daten von HA aus, rechnet die Steuerung mit dem letzten
PV-Wert weiter – auch in BETRIEB.

Das README beschrieb «dann ABSCHALT», `translations/*.yaml` beschreiben die
Option noch als «bevor Abschaltung». Das README ist korrigiert, die
translations nicht, weil sie mit der Entscheidung zusammenhängen:

1. **Abschaltung einbauen:** In BETRIEB/ABREGELUNG bei `ha_connected = False`
   → ABSCHALT, in WARTEN kein Start. Minor-Version.
2. **Nur Anzeige:** Die Option bleibt ohne Wirkung auf die Steuerung, die
   translations werden an den Text im README angepasst. Patch-Version.

## 2026-09-15 – aus dem App-Chat: zurückgestellte Punkte aus der Planung

Beim Plan für V1.0.12 bis Doku notiert, bewusst nicht umgesetzt. Vorlage ist
`cm4_sys_monitor` V2.1.0:

- `Dockerfile`: Base-Image mit festem Alpine-Tag statt `latest`.
- `paho-mqtt` 1.6.1 → 2.x.
- Discovery nach einem Neustart von HA erneut senden (`homeassistant/status`).
- Watchdog der App ist auf HA ausgeschaltet; das README empfiehlt ihn.
- Nach dem Start bleibt die Zustandsmaschine bei aktiver Sicherheitssperre in
  AUS statt WARTEN, obwohl der Modus «PV Überschuss» ist. Funktional ohne
  Folge, in der Anzeige aber irreführend.
- `dashboard.yaml`: Anzeigebereich und Farbschwellen der Temperaturanzeige sind
  feste Zahlen. Darstellung, keine Parameter – bewusst stehen gelassen.
