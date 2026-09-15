# Changelog

Alle wichtigen Änderungen an dieser App werden in dieser Datei dokumentiert.

Das Format folgt [Keep a Changelog](https://keepachangelog.com/de/1.1.0/), die
Versionen folgen [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

## [1.1.0] - 2026-09-15

### Geändert

- **Optionen aus `/data/options.json`:** Das Programm liest die App-Optionen selbst. `run.sh` übergibt keine Argumente mehr. Fehlt eine Pflichtoption, bricht die App mit einer Meldung ab, die die Option nennt, statt mit einem eigenen Wert zu laufen.
- `wp_ip` hat keine Vorgabe mehr und muss bei einer neuen Installation gesetzt werden. Bestehende Installationen behalten ihren gespeicherten Wert.
- `mqtt_user` und `mqtt_password` sind optional, das Passwort ist ein Passwortfeld und wird in der Konfiguration verdeckt angezeigt.
- Feste Werte stehen je einmal als benannte Konstante: Kompressorschwelle, Grenze im Modus «Sofort», Reset-Prüfung, Cooldown-Faktor, PV-Hysterese, Sicherheits-Hysterese, HTTP-Timeout.
- Die Dashboard-Parameter haben ihren Startwert nur noch in `DEFAULT_PARAMS`; Zustandsmaschine und MQTT-Handler wiederholen weder Werte noch Typen.
- Das Lebenszeichen «HA weiterhin nicht erreichbar» richtet sich nach der Zeit statt nach einer Fehlerzahl, die ein Messintervall von 15 s voraussetzte.
- `translations/` nennen keine Vorgaben mehr.

### Entfernt

- Der Rückfallpfad in `src/config.py` mit eigenen Vorgaben – darunter `startup_no_limit_s` 180 statt 1800 – und das unbenutzte `register_timeout_min`.

### Sicherheit

- Das MQTT-Passwort steht nicht mehr als Argument in der Prozessliste.

## [1.0.12] - 2026-09-15

### Behoben

- **Kompressorstart im Anlauf:** `write_fixwert()` schaltet das Soft Limit ab (HR10040 = 0), bevor der Fixwert gesetzt wird. Ist aus einem früheren Zustand noch ein Limit aktiv, startet der Verdichter nicht, wenn seine Anlaufleistung darüber liegt. Die Änderung lief auf Home Assistant seit dem 2026-05-13, stand aber nicht im Repo – die installierte App wich damit vom Stand v1.0.11 im Repo ab.

### Geändert

- `url` in der `config.yaml` verweist auf dieses Repository statt auf einen Platzhalter.
- CHANGELOG auf Keep a Changelog umgestellt, mit Datum und Link je Version.

## [1.0.11] - 2026-05-26

### Geändert

- **HA API Fehler-Eskalation:** Bei HA-Neustart nur noch 1 WARNING + Recovery-Meldung statt je 2 Zeilen pro 15s-Zyklus.
- **Ping-Pong Log-Erkennung:** Wiederholte Wechsel zwischen gleichen WARTEN-Gründen (z.B. "Stabilisierung"↔"PV zu tief", "Speicher voll"↔"Zu wenig Spielraum") werden auf DEBUG heruntergestuft.

### Behoben

- **SAFETY Hysterese:** Recovery nach Übertemperatur erst bei < 62°C (statt sofort bei < 65°C), verhindert Flapping an der Grenze.

## [1.0.10] - 2026-05-14

### Geändert

- `startup_no_limit_s` Default auf 1800s (30 min) – Kompressor hat nach langer Standzeit genug Zeit für Öl-Vorwärmung.

### Behoben

- Fehlstarts, die durch den zu kurzen Timeout (300s) verursacht wurden.

## [1.0.9] - 2026-05-12

### Hinzugefügt

- **Diagnose-Register:** IR 10201 (Fehlernummer), IR 10203 (Schaltspielsperre), IR 10302 (Min. Leistung) werden gelesen.
- **Erweitertes Fehlstart-Logging:** Zeigt bei ANLAUF FEHLGESCHLAGEN alle Diagnose-Daten (Status Heizen, Schaltspielsperre, Fehlernummer, Min. Leistung).

### Behoben

- **Log-Spam:** "Stabilisierung läuft" nutzt nun das _log_wait Pattern (nur 1x INFO bei Eintritt, dann nur bei Grund-Wechsel).

## [1.0.8] - 2026-05-10

### Hinzugefügt

- **Parameter-Persistenz:** Dashboard-Einstellungen werden in `/data/params.json` gespeichert und bleiben nach Rebuild, Neustart und Update erhalten.
- Neue Datei `param_store.py` (persistenter Key-Value Store).

### Geändert

- `mqtt_handler.py` vereinfacht (keine retained-Message Abhängigkeit mehr).

## [1.0.7] - 2026-05-08

Enthält auch die Versionen 1.0.4 bis 1.0.6, die nie als eigener Commit im Repo standen.

### Hinzugefügt

- Reset-Verifizierung: WARNING wenn Kompressor 120s nach Reset noch läuft.
- Custom App-Icon (`logo.png` + `icon.png`).

### Geändert

- BETRIEB↔ABREGELUNG Wechsel auf DEBUG (nur erster Eintritt auf INFO + Zusammenfassung bei Zyklus-Ende).
- pymodbus Connection-Meldungen unterdrückt (eigener Logger auf WARNING).

### Behoben

- Modbus-Disconnect Prüfung vor Speicher-voll (verhindert irreführende "99°C" Meldung).
- `write_reset()` Erfolg wird geprüft und bei Fehler als ERROR geloggt.
- SAFETY-Logging korrigiert: CRITICAL nur wenn wir aktiv steuern, sonst WARNING.

## [1.0.6]

Datum nicht überliefert, nie als eigener Commit im Repo.

### Hinzugefügt

- **Start-Hysterese:** PV-Überschuss muss konfigurierbare Dauer stabil über Schwelle sein (Dashboard-Slider "Min. Überschuss-Dauer", Default 10 min).
- **Min. Batteriestand:** Neuer Slider – WP startet erst wenn Batterie-SOC >= Schwellwert (0% = deaktiviert).
- Neue Config-Option `ha_entity_battery_soc` (Default: `sensor.battery_state_of_capacity`).
- Neuer Sensor: Batteriestand (%) im Dashboard.

### Geändert

- BETRIEB-Logs (Fixwert/Limit) auf DEBUG heruntergestuft.
- Modbus write verify auf DEBUG heruntergestuft.

## [1.0.5]

Datum nicht überliefert, nie als eigener Commit im Repo.

### Hinzugefügt

- Progressiver Cooldown nach Fehlstarts (25 min → 50 min → 75 min max).

### Geändert

- PV-Hysterese: "PV erholt" erst nach 2 Messzyklen (30s stabil über Schwelle).
- Heartbeat-Intervall auf 60 Min erhöht (war 15 Min).

### Behoben

- **KRITISCH – Modbus Reset bei jedem Verlassen des aktiven Zustands:**
  - Kompressor extern gestoppt → Reset + Cooldown (war: nur Cooldown, Register blieben aktiv!)
  - Mode=Aus aus WARTEN → defensiver Reset
- EVU-Sperre wird vor Start geprüft (Betriebsart=3/4 blockiert ANLAUF).
- Doppeltes "Modbus Reset" Log entfernt.

## [1.0.4]

Datum nicht überliefert, nie als eigener Commit im Repo.

### Geändert

- Logging-Optimierung: "Log-on-change + Heartbeat" Pattern.
- WARTEN-Meldungen nur noch bei Grund-Wechsel oder alle 15 Min.
- Cooldown: Nur Start + Ende statt minütlichem Countdown.
- BETRIEB-Log nur bei ΔTemp ≥ 2K, ΔLimit ≥ 500W oder alle 5 Min.
- ANLAUF-Log nur einmalig statt jeden Schreibzyklus.
- Neuer Catch-all: "PV zu tief" wird als Warte-Grund geloggt.
- Log-Reduktion von ~940 Zeilen/Tag auf ~40-50 im Normalbetrieb.

## [1.0.3] - 2026-05-03

### Hinzugefügt

- Kompressor-Überwachung (externer Start/Stopp).
- Übernahme-Logik (externer Heizbetrieb).
- Externe Übersteuerung erkennen (WW, Abtauen).
- Abschalt-Timer als HA Entity.
- Version zentral aus `config.yaml`.

### Geändert

- Anlauf mit `max_temperature`.
- Kein Start wenn Delta < Offset.
- Sauberes Logging.

### Behoben

- Safety: kein Log-Spam.

## [1.0.2]

Datum nicht überliefert.

### Hinzugefügt

- SOLL-Verify nach Schreibvorgang.
- Anlauf-Timeout 300s.

### Geändert

- Modbus Schreibpausen 1.0s.

## [1.0.1]

Datum nicht überliefert.

### Geändert

- MQTT Auth via bashio/config.

### Behoben

- Dockerfile-Fix (BUILD_ARCH).

## [1.0.0]

Datum nicht überliefert.

- Initiale Version.

[Unreleased]: https://github.com/tsgwiro1/rwi_ha_apps/compare/pv_wp_control/v1.1.0...HEAD
[1.1.0]: https://github.com/tsgwiro1/rwi_ha_apps/tree/pv_wp_control/v1.1.0
[1.0.12]: https://github.com/tsgwiro1/rwi_ha_apps/tree/pv_wp_control/v1.0.12
[1.0.11]: https://github.com/tsgwiro1/rwi_ha_apps/tree/pv_wp_control/v1.0.11
[1.0.10]: https://github.com/tsgwiro1/rwi_ha_apps/tree/pv_wp_control/v1.0.10
[1.0.9]: https://github.com/tsgwiro1/rwi_ha_apps/tree/pv_wp_control/v1.0.9
[1.0.8]: https://github.com/tsgwiro1/rwi_ha_apps/tree/pv_wp_control/v1.0.8
[1.0.7]: https://github.com/tsgwiro1/rwi_ha_apps/tree/pv_wp_control/v1.0.7
[1.0.3]: https://github.com/tsgwiro1/rwi_ha_apps/tree/pv_wp_control/v1.0.3
