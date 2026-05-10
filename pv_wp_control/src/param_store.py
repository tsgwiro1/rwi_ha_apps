# Neue Datei: param_store.py

"""Persistente Parameter-Speicherung in /data/params.json."""

import json
import os


PARAMS_FILE = '/data/params.json'


class ParamStore:
    def __init__(self, defaults, log):
        self.log = log
        self.defaults = defaults
        self._params = dict(defaults)
        self._load()

    def _load(self):
        """Parameter aus /data/params.json laden (falls vorhanden)."""
        if not os.path.exists(PARAMS_FILE):
            self.log.info("Keine gespeicherten Parameter – verwende Defaults")
            return

        try:
            with open(PARAMS_FILE, 'r') as f:
                saved = json.load(f)

            loaded = []
            for key, value in saved.items():
                if key in self.defaults:
                    # Typ-Cast basierend auf Default-Typ
                    default_type = type(self.defaults[key])
                    self._params[key] = default_type(value)
                    loaded.append(f"{key}={self._params[key]}")

            if loaded:
                self.log.info(
                    f"Parameter geladen: {', '.join(loaded)}")

        except (json.JSONDecodeError, IOError) as e:
            self.log.warning(f"Parameter-Datei fehlerhaft, verwende Defaults: {e}")

    def _save(self):
        """Parameter in /data/params.json speichern."""
        try:
            with open(PARAMS_FILE, 'w') as f:
                json.dump(self._params, f, indent=2)
        except IOError as e:
            self.log.error(f"Parameter speichern fehlgeschlagen: {e}")

    def get(self, key, default=None):
        """Einzelnen Parameter lesen."""
        return self._params.get(key, default)

    def get_all(self):
        """Alle Parameter als Dict."""
        return dict(self._params)

    def set(self, key, value):
        """Parameter setzen und persistieren."""
        if key in self.defaults:
            default_type = type(self.defaults[key])
            self._params[key] = default_type(value)
            self._save()
            return True
        return False
