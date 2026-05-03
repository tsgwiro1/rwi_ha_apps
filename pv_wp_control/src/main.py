"""PV-WP-Control: Hauptprogramm und Orchestrierung."""

import time
import signal
import sys
from datetime import datetime, date

from config import Config
from logger import get_logger
from modbus_client import ModbusClient
from mqtt_handler import MqttHandler
from ha_client import HAClient
from state_machine import StateMachine, State
from safety import SafetyMonitor
from config import Config, VERSION

running = True


def signal_handler(sig, frame):
    global running
    running = False


def main():
    global running

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # === Init ===
    config = Config()
    log = get_logger(config.log_level)

    log.info("=" * 60)
    log.info(f"PV-WP-Control Add-on v{VERSION}")
    log.info("=" * 60)
    log.info(f"WP: {config.wp_ip}:{config.wp_port} (Slave {config.wp_slave_id})")
    log.info(f"PV Entity: {config.ha_entity_pv_surplus}")
    log.info(f"MQTT Prefix: {config.mqtt_topic_prefix}")
    log.info("=" * 60)

    # === Components ===
    modbus = ModbusClient(config, log)
    mqtt = MqttHandler(config, log)
    ha = HAClient(config, log)
    safety = SafetyMonitor(config, log)
    sm = StateMachine(config, log)

    # Start MQTT
    mqtt.connect()
    mqtt.publish_discovery()

    # Tracking
    last_modbus_write = 0
    last_measurement = 0
    energy_today_wh = 0.0
    energy_date = date.today()
    modbus_data = None
    pv_surplus = 0

    log.info("Entering main loop...")

    # === Main Loop ===
    while running:
        try:
            now = time.time()

            # Reset energy counter at midnight
            if date.today() != energy_date:
                energy_today_wh = 0.0
                energy_date = date.today()
                log.info("Mitternacht: Energiezähler zurückgesetzt")

            # --- Measurement cycle (every 15s) ---
            if now - last_measurement >= config.measurement_interval_s:
                last_measurement = now

                # 1. Read Modbus
                modbus_data = modbus.read_all()

                # 2. Read PV surplus from HA
                pv_surplus = ha.get_pv_surplus()

                # 3. Get dynamic parameters from MQTT
                params = mqtt.get_parameters()

                # 4. Safety check
                safety_ok, safety_msg = safety.check(modbus_data, params)

                # 5. Evaluate state machine
                sm_input = {
                    'modbus': modbus_data,
                    'pv_surplus': pv_surplus,
                    'params': params,
                    'safety_ok': safety_ok,
                    'safety_msg': safety_msg,
                    'modbus_connected': modbus.is_connected(),
                    'ha_connected': ha.is_connected(),
                }
                sm.evaluate(sm_input)

                # 6. Energy tracking
                if modbus_data and modbus_data.get('leistung_kw', 0) > 0.1:
                    energy_today_wh += (modbus_data['leistung_kw'] * 1000 *
                                        config.measurement_interval_s / 3600)

                # 7. Publish status via MQTT
                mqtt.publish_status({
                    'state': sm.state.value,
                    'power': int(modbus_data.get('leistung_kw', 0) * 1000) if modbus_data else 0,
                    'heat_output': int(modbus_data.get('heizleistung_kw', 0) * 1000) if modbus_data else 0,
                    'cop': round(modbus_data.get('cop', 0), 1) if modbus_data else 0,
                    'rl_extern': round(modbus_data.get('rl_extern', 0), 1) if modbus_data else 0,
                    'rl_soll': round(modbus_data.get('rl_soll', 0), 1) if modbus_data else 0,
                    'pv_surplus': int(pv_surplus) if pv_surplus is not None else 0,
                    'active_limit': sm.active_limit_w,
                    'runtime': sm.runtime_min,
                    'cooldown': sm.cooldown_remaining_min,
                    'abregelung_timer': sm.abregelung_remaining_min,
                    'wp_running': modbus_data.get('wp_running', False) if modbus_data else False,
                    'modbus_connected': modbus.is_connected(),
                    'energy_today': round(energy_today_wh / 1000, 2),
                })

                # 8. Debug Log
                if modbus_data:
                    if sm.state == State.ANLAUF:
                        limit_display = "KEIN"
                    elif sm.active_limit_w == 0:
                        limit_display = "-"
                    else:
                        limit_display = f"{sm.active_limit_w}W"

                    log.debug(
                        f"[{sm.state.value}] "
                        f"RL_ext={modbus_data.get('rl_extern', 0):.1f}°C "
                        f"SOLL={modbus_data.get('rl_soll', 0):.1f}°C "
                        f"PV={pv_surplus}W "
                        f"Leistung={modbus_data.get('leistung_kw', 0):.2f}kW "
                        f"Limit={limit_display}"
                    )

            # --- Modbus write cycle (every 60s) ---
            if now - last_modbus_write >= config.modbus_refresh_s:
                last_modbus_write = now

                if sm.state in (State.ANLAUF, State.BETRIEB, State.ABREGELUNG):
                    params = mqtt.get_parameters()
                    rl_extern = modbus_data.get('rl_extern', 30.0) if modbus_data else 30.0
                    pv_surplus_val = ha.get_pv_surplus() or 0

                    if sm.state == State.ANLAUF:
                        # ANLAUF: Fixwert = max_temperature für sicheren Start
                        fixwert = params['max_temperature']
                        modbus.write_fixwert(fixwert)
                        sm.active_limit_w = 0
                        log.info(f"ANLAUF: Fixwert={fixwert:.1f}°C "
                                f"(Delta={fixwert-rl_extern:.1f}K, KEIN Limit)")
                    else:
                        # BETRIEB / ABREGELUNG: Normaler Offset + Limit
                        fixwert = min(rl_extern + params['offset'],
                                      params['max_temperature'])

                        if params['mode'] == 'Sofort':
                            limit_w = 10000
                        else:
                            limit_w = max(int(pv_surplus_val),
                                          params['min_power'])

                        sm.active_limit_w = limit_w
                        modbus.write_fixwert_with_limit(fixwert, limit_w)
                        log.info(f"BETRIEB: Fixwert={fixwert:.1f}°C "
                                f"(RL_ext={rl_extern:.1f}°C + "
                                f"Offset={params['offset']:.1f}K) "
                                f"Limit={limit_w}W")

                elif sm.state == State.ABSCHALT:
                    modbus.write_reset()
                    sm.transition_to_aus()
                    log.info("ABSCHALT: Reset gesendet → AUS")

            # Sleep
            time.sleep(1)

        except Exception as e:
            log.error(f"Fehler im Main Loop: {e}")
            time.sleep(5)

    # === Shutdown ===
    log.info("Shutdown eingeleitet...")
    if sm.state in (State.ANLAUF, State.BETRIEB, State.ABREGELUNG):
        log.info("Sende Reset an WP...")
        modbus.write_reset()

    mqtt.publish_offline()
    mqtt.disconnect()
    modbus.disconnect()
    log.info("PV-WP-Control beendet.")


if __name__ == '__main__':
    main()
