"""Sicherheitslogik."""


class SafetyMonitor:
    def __init__(self, config, log):
        self.config = config
        self.log = log

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

        # Absolute Maximaltemperatur überschritten?
        if rl_extern >= self.config.max_absolute_temperature:
            msg = (f"RL extern {rl_extern:.1f}°C >= "
                   f"{self.config.max_absolute_temperature:.1f}°C")
            return False, msg

        return True, ""
