ARG BUILD_ARCH
FROM ghcr.io/home-assistant/${BUILD_ARCH}-base:latest

RUN apk add --no-cache \
    python3 \
    py3-pip

RUN pip3 install --no-cache-dir --break-system-packages \
    pymodbus==3.6.9 \
    paho-mqtt==1.6.1 \
    requests==2.31.0

COPY src/ /app/
COPY config.yaml /app/
COPY run.sh /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

