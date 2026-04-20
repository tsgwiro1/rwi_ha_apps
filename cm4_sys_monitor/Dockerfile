ARG BUILD_FROM
FROM $BUILD_FROM

# Alles nativ über Alpine Linux installieren
RUN apk add --no-cache \
    python3 \
    py3-paho-mqtt \
    py3-yaml \
    py3-smbus

# Skripte kopieren (i2c_pkg und sensors.py fallen komplett weg!)
COPY usv_status.py /
COPY fan.py /
COPY system_sensors.py /
COPY settings.yaml /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]