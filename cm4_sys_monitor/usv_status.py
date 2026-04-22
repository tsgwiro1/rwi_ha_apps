import smbus
import logging

logger = logging.getLogger("usv_driver")

class INA219:
    def __init__(self, bus=10, addr=0x43, low_bat_warning=3.0):
        self.busnum = bus
        self.addr = addr
        self.low_bat_warning = low_bat_warning
        try:
            self.bus = smbus.SMBus(self.busnum)
            logger.info(f"INA219 initialisiert (Warnschwelle: {self.low_bat_warning}V)")
        except Exception as e:
            logger.error(f"INA219 Init Fehler: {e}")
            self.bus = None

    def get_bus_voltage(self):
        if not self.bus: return 0.0
        try:
            read = self.bus.read_word_data(self.addr, 0x02)
            swapped = ((read << 8) & 0xFF00) | ((read >> 8) & 0x00FF)
            voltage = (swapped >> 3) * 0.004
            if voltage < self.low_bat_warning:
                logger.warning(f"KRITISCH: Batterie bei {voltage:.2f}V!")
            return voltage
        except Exception as e:
            logger.error(f"I2C Spannungsfehler: {e}")
            return 0.0

    def get_current(self):
        if not self.bus: return 0.0
        try:
            read = self.bus.read_word_data(self.addr, 0x04)
            swapped = ((read << 8) & 0xFF00) | ((read >> 8) & 0x00FF)
            if swapped > 32767: swapped -= 65536
            return swapped * 0.1
        except Exception as e:
            logger.error(f"I2C Stromfehler: {e}")
            return 0.0