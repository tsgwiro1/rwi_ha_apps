FROM ghcr.io/home-assistant/base:3.24

RUN apk add --no-cache python3

# Python-Abhängigkeiten in eigener Umgebung, Versionen in requirements.txt
COPY requirements.txt /app/
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/
COPY config.yaml /app/
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
