ARG BUILD_ARCH
FROM ghcr.io/home-assistant/${BUILD_ARCH}-base:latest

# Alles nativ über Alpine Linux installieren
RUN apk add --no-cache \
    python3 \
    py3-paho-mqtt \
    py3-yaml \
    py3-smbus

# Skripte kopieren
COPY usv_status.py /
COPY fan.py /
COPY system_sensors.py /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]