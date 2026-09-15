#!/usr/bin/env python3
"""Durchsucht einen Unified-Diff nach Personenbezug, Geheimnissen und Geodaten.

Liest den Diff auf stdin, schreibt die Funde nach stdout, eine Zeile je Fund:
    <datei>:<zeile>\t<kategorie>\t<textausschnitt>
Rueckgabe 1, wenn es Funde gab, sonst 0.

Geprueft werden nur hinzugefuegte Zeilen - was schon im Repo steht, ist nicht
Gegenstand dieses Commits.
"""
import re, sys

# Ein Wert, der per !secret hereinkommt, ist genau die richtige Form. Ebenso
# eine Schemazeile in der config.yaml einer App: "password: password" oder
# "username: str?" nennt nur den Typ, keinen Wert.
SECRET_REF = re.compile(
    r'!secret\b'
    r'|:\s*["\']?(?:str|password|email|url|int|bool|port)\??["\']?\s*$')
# Ein Wert, den run.sh zur Laufzeit aus den App-Optionen liest
# (PWD=$(bashio::config 'password')), steht nicht im Repo.
OPTION_REF = re.compile(r'bashio::config\b')

MUSTER = [
    ("MAC-Adresse",
     re.compile(r'\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b')),
    ("private IP-Adresse",
     re.compile(r'\b(?:192\.168\.\d{1,3}\.\d{1,3}'
                r'|10\.\d{1,3}\.\d{1,3}\.\d{1,3}'
                r'|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b')),
    # Nur die Zuweisungsform, nicht die Erwaehnung im Fliesstext: ein
    # YAML-Schluessel am Zeilenanfang oder eine Zuweisung mit kompaktem Wert.
    ("Zugangsdaten im Klartext",
     re.compile(r'^\s*[-#/ ]*\b(pass(?:word|wd|phrase)?|pwd|api[_-]?key|apikey'
                r'|token|secret|psk|ota[_-]?key|encryption[_-]?key|ssid'
                r'|credential|user(?:name)?)\s*[:=]\s*["\']?[^\s*]{3}', re.I)),
    ("Zuweisung mit Geheimwert",
     re.compile(r'\b(pass(?:word|wd)?|pwd|api[_-]?key|token|secret|psk)'
                r'\s*=\s*["\']?[^\s"\'*]{6,}', re.I)),
    ("Geodaten",
     re.compile(r'^\s*[-#/ ]*\b(latitude|longitude|lat|lon|lng|gps'
                r'|koordinat\w*)\s*[:=]\s*["\']?-?\d', re.I)),
    # Ausgeschriebene Position: 47.5505°N, 9.3866°E. Verlangt die
    # Himmelsrichtung - reine Zahlenpaare sind in CAD-Dateien Massangaben.
    ("ausgeschriebene Koordinate",
     re.compile(r'\b\d{1,3}\.\d{3,}\s*(?:°\s*[NSEWOnsewo]|[NSEWO])\b')),
    ("E-Mail-Adresse",
     re.compile(r'\b[\w.+-]+@[\w-]+\.[A-Za-z]{2,}\b')),
    ("langer Schluesselstring",
     re.compile(r'["\'][A-Za-z0-9+/]{32,}={0,2}["\']')),
    ("Personenname",
     re.compile(r'\b(Widmer|rogerwidmer)\b')),
    ("Seriennummer",
     re.compile(r'\b(serial|seriennummer|imei|iccid)\s*[:=]\s*["\']?\w', re.I)),
]

RISKANTE_NAMEN = re.compile(
    r'(^|/)(secrets?\.ya?ml|\.env|.*\.local\.\w+|.*\.(key|pem|p12|pfx|crt))$', re.I)
BILD = re.compile(r'\.(jpe?g|png|heic|tiff?|bmp|gif|mp4|mov)$', re.I)
# Erzeugte oder binaere Formate: der Inhalt ist nicht sinnvoll zu mustern.
# Sie werden gemeldet, aber nicht durchsucht - ansehen muss man sie selbst.
# Platzhalter aus der Dokumentation sind keine Funde. Bewusst eng gefasst:
# nur die kanonischen Beispielwerte, nichts, was einer echten Adresse aehnelt.
PLATZHALTER = re.compile(
    r'\b(?:AA:BB:CC:DD:EE:FF|DE:AD:BE:EF(?::[0-9A-F]{2})*|(?:00:){5}00'
    r'|(?:FF:){5}FF|XX:XX:XX:XX:XX:XX)\b', re.I)

# Die Pruefwerkzeuge selbst enthalten die Muster, nach denen sie suchen, und
# die Beispielwerte aus ihrem eigenen Hilfetext. Sie auszunehmen ist der Preis
# dafuer, dass sie sich nicht selbst blockieren - dort gehoert ohnehin keine
# Konfiguration hin, und wer sie aendert, liest sie.
SELBST = re.compile(r'(^|/)\.claude/hooks/')

UNLESBAR = re.compile(
    r'\.(pdf|docx?|xlsx?|pptx?|step|stp|stl|3mf|f3d|zip|bin|ttf|otf|woff2?)$', re.I)

def main():
    datei, zeile, funde, lange = None, 0, [], set()
    for roh in sys.stdin.read().splitlines():
        if roh.startswith('+++ b/'):
            datei, zeile = roh[6:], 0
            if SELBST.search(datei):
                datei = None
                continue
            if RISKANTE_NAMEN.search(datei):
                funde.append((datei, 0, "verdaechtiger Dateiname", datei))
            elif BILD.search(datei):
                funde.append((datei, 0, "Bild- oder Videodatei", datei))
            elif UNLESBAR.search(datei):
                funde.append((datei, 0, "erzeugte Datei, nicht durchsuchbar", datei))
            continue
        if roh.startswith('@@'):
            m = re.search(r'\+(\d+)', roh)
            zeile = int(m.group(1)) - 1 if m else 0
            continue
        # Kontextzeilen zaehlen mit, sonst stimmt die Zeilennummer nur bei -U0.
        if roh.startswith(' '):
            zeile += 1
            continue
        if not roh.startswith('+') or roh.startswith('+++'):
            continue
        if datei is None:
            continue
        zeile += 1
        if datei and UNLESBAR.search(datei):
            continue
        if len(text := roh[1:]) > 500:
            if datei not in lange:
                lange.add(datei)
                funde.append((datei, zeile, "minifizierte Zeile, nicht durchsuchbar", text[:60]))
            continue
        text = PLATZHALTER.sub('', roh[1:])
        for kategorie, muster in MUSTER:
            if kategorie == "Zugangsdaten im Klartext" and SECRET_REF.search(text):
                continue
            if kategorie in ("Zugangsdaten im Klartext", "Zuweisung mit Geheimwert") \
                    and OPTION_REF.search(text):
                continue
            if muster.search(text):
                funde.append((datei, zeile, kategorie, roh[1:].strip()[:110]))
    for d, z, k, t in funde:
        print(f"{d}:{z}\t{k}\t{t}")
    return 1 if funde else 0

sys.exit(main())
