import smbus
import logging

logger = logging.getLogger("fan_driver")

class RaspiCM4IOBoardFanSensor:
    def __init__(self, busnum=10, addr=0x2f):
        self.bus = smbus.SMBus(busnum)
        self.addr = addr

    def set_fan_speed_percentage(self, percentage):
        try:
            pwm = int(percentage * 2.55)
            self.bus.write_byte_data(self.addr, 0x30, pwm)
        except Exception as e:
            logger.error(f"Fan PWM Fehler: {e}")

    def fan_speed(self):
        try:
            high = self.bus.read_byte_data(self.addr, 0x06)
            low = self.bus.read_byte_data(self.addr, 0x07)
            if high == 0xFF and low == 0xFF: return 0
            # Formel basierend auf EMC2301 Datenblatt
            return int(3932160 / ((high << 5) | (low >> 3)))
        except Exception as e:
            logger.error(f"Fan RPM Fehler: {e}")
            return 0