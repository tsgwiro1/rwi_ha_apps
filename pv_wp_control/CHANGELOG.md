
## 📝 Changelog

### v1.0.3 (aktuell)
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
