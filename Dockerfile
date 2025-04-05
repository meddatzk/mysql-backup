FROM alpine:3.18

# Installiere benötigte Pakete
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    mysql-client \
    cifs-utils \
    tzdata \
    bash \
    curl \
    supervisor

# Arbeitsverzeichnis setzen
WORKDIR /app

# Kopiere Anwendungsdateien
COPY app/ /app/
COPY config/ /app/config/
COPY scripts/ /app/scripts/

# Erstelle Verzeichnisse
RUN mkdir -p /app/backups /app/logs

# Installiere Python-Abhängigkeiten
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Mache Skripte ausführbar
RUN chmod +x /app/scripts/*.sh

# Konfiguriere Supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Port für die Weboberfläche
EXPOSE 80

# Starte Supervisor als Hauptprozess
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
