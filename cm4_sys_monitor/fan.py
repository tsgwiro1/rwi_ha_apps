import smbus

class RaspiCM4IOBoardFanSensor:
    def __init__(self, busnum=10, address=0x2f):
        self.busnum = busnum
        self.address = address
        # I2C Bus initialisieren
        self.bus = smbus.SMBus(self.busnum)

    def set_fan_speed_percentage(self, percentage: int):
        """Setzt die Lüftergeschwindigkeit (0 - 100%)"""
        # Limitiere auf 0-100
        percentage = max(0, min(100, percentage))
        converted_value = int(percentage / 100 * 255)
        
        try:
            # Register 0x30 ist FAN_SETTING
            self.bus.write_byte_data(self.address, 0x30, converted_value)
        except Exception as e:
            print(f"Fehler beim Setzen der Lüftergeschwindigkeit: {e}")

    def fan_speed(self) -> int:
        """Liest die aktuelle RPM aus"""
        try:
            # Register 0x3E (High Byte) und 0x3F (Low Byte) für TACH_READ
            hb = self.bus.read_byte_data(self.address, 0x3E)
            lb = self.bus.read_byte_data(self.address, 0x3F)
            
            # TACH Count berechnen (laut EMC2301 Datenblatt / Original-Code)
            tach_count = (hb << 5) | (lb >> 3)
            
            if tach_count == 0 or tach_count >= 8191:
                return 0 # Lüfter steht still
                
            # Formel aus dem Original-Code (zusammengefasst)
            rpm = int(3932160 / tach_count)
            return int(rpm * 1.86)
            
        except Exception as e:
            print(f"Fehler beim Auslesen der RPM: {e}")
            return 0