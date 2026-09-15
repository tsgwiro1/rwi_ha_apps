from smbus2 import SMBus
import logging

logger = logging.getLogger("fan_driver")

# Register des EMC2301
REG_FAN_SETTING = 0x30
REG_TACH_HIGH = 0x3E
REG_TACH_LOW = 0x3F

# Drehzahl = TACH_RPM_FACTOR / Zählerstand (Bereichsfaktor 1), mal Korrekturfaktor
TACH_RPM_FACTOR = 3932160
TACH_CORRECTION = 1.86
# Grösster Zählerstand: Der Lüfter steht
TACH_MAX = 8191


class RaspiCM4IOBoardFanSensor:
    def __init__(self, busnum, address):
        self.address = address
        # I2C Bus initialisieren
        self.bus = SMBus(busnum)
        logger.info(f"EMC2301 initialisiert (Adresse: {self.address:#04x})")

    def set_fan_speed_percentage(self, percentage: int):
        """Setzt die Lüftergeschwindigkeit (0 - 100%)"""
        # Limitiere auf 0-100
        percentage = max(0, min(100, percentage))
        converted_value = int(percentage / 100 * 255)

        try:
            self.bus.write_byte_data(self.address, REG_FAN_SETTING, converted_value)
        except Exception as e:
            logger.error(f"Fehler beim Setzen der Lüftergeschwindigkeit: {e}")

    def fan_speed(self) -> int:
        """Liest die aktuelle RPM aus"""
        try:
            hb = self.bus.read_byte_data(self.address, REG_TACH_HIGH)
            lb = self.bus.read_byte_data(self.address, REG_TACH_LOW)

            # 13-Bit-Zählerstand: 8 Bit aus dem High-Byte, die oberen 5 Bit des Low-Byte
            tach_count = (hb << 5) | (lb >> 3)

            if tach_count == 0 or tach_count >= TACH_MAX:
                return 0 # Lüfter steht still

            return int(TACH_RPM_FACTOR / tach_count * TACH_CORRECTION)

        except Exception as e:
            logger.error(f"Fehler beim Auslesen der RPM: {e}")
            return 0
