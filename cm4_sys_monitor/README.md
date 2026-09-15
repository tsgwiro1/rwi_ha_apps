# CM4 System Monitor

[![Version: 2.1.0](https://img.shields.io/badge/Version-2.1.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-App-41bdf5?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)

> Regelt den Lüfter und meldet Akkuspannung, Ladestand, Akkustrom und
> Lüfterdrehzahl eines Raspberry Pi Compute Module 4 auf dem Waveshare
> CM4-POE-UPS-BASE – als App direkt in Home Assistant, per MQTT-Discovery.

---

## ⚠️ Haftungsausschluss (Disclaimer)

Privates Projekt, Verwendung **auf eigene Gefahr**. Es wird keinerlei Haftung für
Schäden an Hardware, Haustechnik oder Daten übernommen.

Die App **steuert den Lüfter** des Rechners, auf dem Home Assistant selbst läuft,
und schreibt dafür über I²C direkt in die Register von Lüfterregler und
Strommesser. Insbesondere:

* **Kühlung:** Zu hoch gesetzte Temperaturgrenzen lassen den Lüfter zu spät
  anlaufen. Nach einem Neustart des Boards regelt niemand, bis die App läuft.
* **Akkuwerte** sind Näherungen, der Ladestand ist aus der Spannung geschätzt.
  Sie ersetzen keine Abschaltung, die bei leerem Akku zuverlässig greift.
* Keine geprüfte Software, keine Gewähr für Richtigkeit oder Vollständigkeit von
  Code und Dokumentation.

---

## 📖 Inhalt

- [Das Problem](#-das-problem)
- [Die Lösung](#-die-lösung)
- [Was sie leistet – und was nicht](#-was-sie-leistet--und-was-nicht)
- [Aufbau](#-aufbau)
- [Installation](#-installation)
- [Die Sensoren](#-die-sensoren)
- [Dokumentation](#-dokumentation)
- [Herkunft](#-herkunft)
- [Lizenz](#-lizenz)

---

## 🚨 Das Problem

Das Waveshare CM4-POE-UPS-BASE macht aus einem CM4 einen kleinen Server mit PoE
und Akkupufferung. Dafür hat es zwei eigene Chips: einen Lüfterregler (EMC2301)
und einen Strommesser für den Akku (INA219).

Läuft darauf Home Assistant OS, bleiben beide ungenutzt:

1. **Der Lüfter wird nicht geregelt.** Home Assistant OS lädt keinen Treiber für
   den Lüfterregler (auf dieser Installation geprüft).
2. **Der Akku ist unsichtbar.** Ob der Rechner gerade auf Akku läuft und wie
   lange noch, sieht Home Assistant nicht.
3. **Die Integration System Monitor** liefert CPU-Temperatur, Last und Speicher,
   aber nichts aus diesen beiden Chips.

## ✅ Die Lösung

Eine App auf Home Assistant selbst. Sie liest die Chips über I²C, regelt den
Lüfter nach der CPU-Temperatur und meldet die Werte über den MQTT-Broker. Per
**MQTT-Discovery** meldet sie sich als Gerät an – in Home Assistant ist nichts
von Hand einzutragen.

| | |
| :--- | :--- |
| 🌀 **Lüfter** | Regelung nach CPU-Temperatur mit Hysterese und Anlaufhilfe, Drehzahl als Sensor |
| 🔋 **Akku** | Spannung, Ladestand und Strom aus dem INA219 |

## ⚖️ Was sie leistet – und was nicht

**Leistet:** Eine Meldung je Intervall mit allen Werten, ein Gerät mit vier
Entitäten. Wird die App gestoppt, zeigen die Entitäten sofort «nicht
verfügbar», und der Lüfter läuft voll. Ist der Broker weg, regelt sie den Lüfter
trotzdem weiter.

**Leistet nicht:** Herunterfahren bei leerem Akku. Die App meldet die Werte; was
daraus folgt, entscheidet eine Automation in Home Assistant.

**Leistet auch nicht:** CPU-Temperatur, Last oder Speicher als Entitäten – das
liefert die Integration System Monitor. Und keine Restlaufzeit: Der Ladestand
ist aus der Spannung geschätzt.

> ⚠️ **Nur für dieses Board.** Die App setzt den EMC2301 und den INA219 des
> Waveshare CM4-POE-UPS-BASE an ihren festen Adressen voraus.

## 🧱 Aufbau

```
┌──────────── Waveshare CM4-POE-UPS-BASE, Home Assistant OS ────────────┐
│                                                                       │
│  CPU-Temperatur ──────────────┐                                       │
│                               ▼                                       │
│  EMC2301 (Bus 10, 0x2f) ◀──▶ App «CM4 System Monitor»                 │
│  Lüfter: PWM, Drehzahl        ▲                                       │
│                               │                                       │
│  INA219  (Bus 10, 0x43) ──────┘                                       │
│  Akku: Spannung, Strom                                                │
│                                                                       │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ MQTT, einmal je Intervall
                                ▼
                     MQTT-Broker ──▶ Home Assistant
```

## 🚀 Installation

Voraussetzungen: Home Assistant OS auf dem CM4 mit diesem Board, der I²C-Bus als
`/dev/i2c-10`, ein MQTT-Broker und die MQTT-Integration in Home Assistant.

1. Dieses Repository in Home Assistant hinzufügen, wie im
   [Repository-README](../README.md#repository-in-home-assistant-hinzufügen)
   beschrieben. Alternativ den Ordner nach `/addons/cm4_sys_monitor/` kopieren;
   die App erscheint dann unter den lokalen Apps.
2. **CM4 System Monitor** installieren und im Reiter **Konfiguration** Broker,
   Benutzername und Passwort eintragen. Alle Optionen erklärt [DOCS.md](DOCS.md).
3. Starten. Im Log erscheinen `INA219 initialisiert (Kalibrierung: 0x68f4, …)`
   und `MQTT verbunden`.
4. **Beim Booten starten** und **Watchdog** einschalten.

Danach erscheint in Home Assistant unter *MQTT* ein neues Gerät.

## 📡 Die Sensoren

| Sensor | Einheit | Hinweis |
| :--- | :--- | :--- |
| Akkuspannung | V | drei Nachkommastellen |
| Ladestand | % | aus der Spannung geschätzt |
| Akkustrom | mA | positiv beim Entladen, mit Langzeitstatistik |
| Lüfterdrehzahl | rpm | |

Jeder lässt sich einzeln abschalten und verschwindet dann aus Home Assistant.

## 📚 Dokumentation

| Datei | Inhalt |
| :--- | :--- |
| [DOCS.md](DOCS.md) | Optionen, Lüfterregelung, MQTT und Entitäten, Genauigkeit der Akkuwerte, Datenlast, Fehlerbehebung, bekannte Punkte, Herkunft. In Home Assistant im Reiter **Dokumentation**. |
| [CHANGELOG.md](CHANGELOG.md) | Was sich je Version geändert hat, und warum |

## 🧬 Herkunft

Kalibrierung und Umrechnung des INA219 stammen aus der Demo von Waveshare zum
[CM4-POE-UPS-BASE](https://www.waveshare.com/wiki/CM4-POE-UPS-BASE). Lüfterregelung,
MQTT-Anbindung und App sind eigener Code. Einzelheiten in
[DOCS.md](DOCS.md#9-herkunft).

## 📄 Lizenz

MIT – siehe [LICENSE](../LICENSE).
