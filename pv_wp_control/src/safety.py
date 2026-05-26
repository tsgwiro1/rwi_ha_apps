class SafetyMonitor:
    def __init__(self, config, log):
        self.config = config
        self.log = log
        self._triggered = False

    def check(self, modbus_data, params):
        """
        Sicherheitsprüfung mit Hysterese.
        Returns: (ok: bool, message: str)
        """
        if modbus_data is None:
            return True, ""

        rl_extern = modbus_data.get('rl_extern')
        if rl_extern is None:
            return True, ""

        if self._triggered:
            # Recovery erst unterhalb Hysterese-Schwelle
            recovery_temp = (self.config.max_absolute_temperature
                             - self.config.safety_hysteresis)
            if rl_extern < recovery_temp:
                self._triggered = False
                return True, ""
            # Noch im Alarm-Bereich
            msg = (f"RL extern {rl_extern:.1f}°C "
                   f"(Recovery bei < {recovery_temp:.1f}°C)")
            return False, msg
        else:
            # Absolute Maximaltemperatur überschritten?
            if rl_extern >= self.config.max_absolute_temperature:
                self._triggered = True
                msg = (f"RL extern {rl_extern:.1f}°C >= "
                       f"{self.config.max_absolute_temperature:.1f}°C")
                return False, msg

        return True, ""
