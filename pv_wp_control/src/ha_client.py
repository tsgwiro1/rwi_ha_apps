"""Home Assistant REST API Client."""

import time
import requests


class HAClient:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self._last_value = None
        self._last_success = time.time()
        self._consecutive_errors = 0

    def is_connected(self):
        """Prüfe ob HA-Daten aktuell sind."""
        elapsed = time.time() - self._last_success
        timeout = self.config.ha_connection_timeout_min * 60
        return elapsed < timeout

    def get_pv_surplus(self):
        """PV Überschuss aus HA Entity lesen."""
        entity_id = self.config.ha_entity_pv_surplus
        url = f"{self.config.ha_url}/states/{entity_id}"

        headers = {
            'Authorization': f'Bearer {self.config.ha_token}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                state = data.get('state', 'unavailable')

                if state in ('unavailable', 'unknown', 'None'):
                    self.log.debug(f"HA Entity {entity_id} = {state}")
                    return self._last_value

                value = float(state)
                self._last_value = value
                self._last_success = time.time()
                self._consecutive_errors = 0
                return value

            else:
                self._consecutive_errors += 1
                self.log.warning(
                    f"HA API Fehler: {response.status_code} "
                    f"(Errors: {self._consecutive_errors})"
                )
                return self._last_value

        except requests.exceptions.ConnectionError:
            self._consecutive_errors += 1
            if self._consecutive_errors <= 3:
                self.log.debug("HA API nicht erreichbar")
            else:
                self.log.warning(
                    f"HA API nicht erreichbar "
                    f"(seit {self._consecutive_errors} Versuchen)"
                )
            return self._last_value

        except (ValueError, TypeError) as e:
            self.log.warning(f"HA Entity Wert ungültig: {e}")
            return self._last_value

        except Exception as e:
            self._consecutive_errors += 1
            self.log.error(f"HA API Fehler: {e}")
            return self._last_value

