"""Sicherheitslogik."""


class SafetyMonitor:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self._last_notaus_logged = False

    def check(self, modbus_data, params):
        """
        Sicherheitsprüfung.
        Returns: (ok: bool, message: str)
        """
        if modbus_data is None:
            return True, ""

        rl_extern = modbus_data.get('rl_extern')
        if rl_extern is None:
            return True, ""

        # NOTAUS: Absolute Maximaltemperatur (nicht konfigurierbar!)
        if rl_extern >= self.config.max_absolute_temperature:
            msg = (f"NOTAUS: RL extern {rl_extern:.1f}°C >= "
                   f"{self.config.max_absolute_temperature}°C!")
            if not self._last_notaus_logged:
                self.log.critical(msg)
                self._last_notaus_logged = True
            return False, msg
        else:
            self._last_notaus_logged = False

        return True, ""
