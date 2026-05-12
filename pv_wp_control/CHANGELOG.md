
## 📝 Change-log

### v1.0.9 (aktuell)
- **Log-Spam behoben:** "Stabilisierung läuft" nutzt nun _log_wait Pattern (nur 1x INFO bei Eintritt, dann nur bei Grund-Wechsel)
- **Diagnose-Register:** IR 10201 (Fehlernummer), IR 10203 (Schaltspielsperre), IR 10302 (Min. Leistung) werden gelesen
- **Erweitertes Fehlstart-Logging:** Zeigt bei ANLAUF FEHLGESCHLAGEN alle Diagnose-Daten (Status Heizen, Schaltspielsperre, Fehlernummer, Min. Leistung)

### v1.0.8
- Parameter-Persistenz: Dashboard-Einstellungen werden in /data/params.json gespeichert
- Einstellungen bleiben nach Rebuild, Neustart und Update erhalten
- Neue Datei: param_store.py (persistenter Key-Value Store)
- mqtt_handler.py vereinfacht (keine retained-Message Abhängigkeit mehr)

### v1.0.7
- BETRIEB↔ABREGELUNG Wechsel auf DEBUG (nur erster Eintritt auf INFO + Zusammenfassung bei Zyklus-Ende)
- Reset-Verifizierung: WARNING wenn Kompressor 120s nach Reset noch läuft
- Modbus-Disconnect Prüfung vor Speicher-voll (verhindert irreführende "99°C" Meldung)
- pymodbus Connection-Meldungen unterdrückt (eigener Logger auf WARNING)
- write_reset() Erfolg wird geprüft und bei Fehler als ERROR geloggt
- Custom App-Icon (logo.png + icon.png)
- SAFETY-Logging korrigiert: CRITICAL nur wenn wir aktiv steuern, sonst WARNING

### v1.0.6
- **Start-Hysterese:** PV-Überschuss muss konfigurierbare Dauer stabil über Schwelle sein (Dashboard-Slider "Min. Überschuss-Dauer", Default 10 min)
- **Min. Batteriestand:** Neuer Slider – WP startet erst wenn Batterie-SOC >= Schwellwert (0% = deaktiviert)
- Neue Config-Option: `ha_entity_battery_soc` (Default: sensor.battery_state_of_capacity)
- BETRIEB-Logs (Fixwert/Limit) auf DEBUG heruntergestuft
- Modbus write verify auf DEBUG heruntergestuft
- Neuer Sensor: Batteriestand (%) im Dashboard

### v1.0.5
- **KRITISCHER FIX:** Modbus Reset bei jedem Verlassen des aktiven Zustands
  - Kompressor extern gestoppt → Reset + Cooldown (war: nur Cooldown, Register blieben aktiv!)
  - Mode=Aus aus WARTEN → defensiver Reset
- EVU-Sperre wird vor Start geprüft (Betriebsart=3/4 blockiert ANLAUF)
- Progressiver Cooldown nach Fehlstarts (25 min → 50 min → 75 min max)
- PV-Hysterese: "PV erholt" erst nach 2 Messzyklen (30s stabil über Schwelle)
- Heartbeat-Intervall auf 60 Min erhöht (war 15 Min)
- Doppeltes "Modbus Reset" Log entfernt

### v1.0.4
- Logging-Optimierung: "Log-on-change + Heartbeat" Pattern
- WARTEN-Meldungen nur noch bei Grund-Wechsel oder alle 15 Min
- Cooldown: Nur Start + Ende statt minütlichem Countdown
- BETRIEB-Log nur bei ΔTemp ≥ 2K, ΔLimit ≥ 500W oder alle 5 Min
- ANLAUF-Log nur einmalig statt jeden Schreibzyklus
- Neuer Catch-all: "PV zu tief" wird als Warte-Grund geloggt
- Log-Reduktion von ~940 Zeilen/Tag auf ~40-50 im Normalbetrieb

### v1.0.3
- Kompressor-Überwachung (externer Start/Stopp)
- Übernahme-Logik (externer Heizbetrieb)
- Externe Übersteuerung erkennen (WW, Abtauen)
- Abschalt-Timer als HA Entity
- Anlauf mit max_temperature
- Kein Start wenn Delta < Offset
- Safety: kein Log-Spam
- Sauberes Logging
- Version zentral aus config.yaml

### v1.0.2
- Modbus Schreibpausen 1.0s
- SOLL-Verify nach Schreibvorgang
- Anlauf-Timeout 300s

### v1.0.1
- MQTT Auth via bashio/config
- Dockerfile-Fix (BUILD_ARCH)

### v1.0.0
- Initiale Version
