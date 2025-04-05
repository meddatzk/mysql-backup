#!/bin/bash

# MySQL-Backup-Skript

# Lese Konfiguration
CONFIG_FILE="/app/config/backup.conf"
source "$CONFIG_FILE"

# Setze Standardwerte, falls nicht in der Konfiguration definiert
BACKUP_DIR=${BACKUP_DIR:-"/app/backups"}
MYSQL_HOST=${MYSQL_HOST:-"localhost"}
MYSQL_PORT=${MYSQL_PORT:-"3306"}
MYSQL_USER=${MYSQL_USER:-"root"}
MYSQL_PASSWORD=${MYSQL_PASSWORD:-""}
MYSQL_DATABASE=${MYSQL_DATABASE:-""}
BACKUP_RETENTION=${BACKUP_RETENTION:-"7"}
SMB_ENABLED=${SMB_ENABLED:-"false"}
SMB_SHARE=${SMB_SHARE:-""}
SMB_MOUNT=${SMB_MOUNT:-"/mnt/backup"}
SMB_USER=${SMB_USER:-""}
SMB_PASSWORD=${SMB_PASSWORD:-""}
SMB_DOMAIN=${SMB_DOMAIN:-"WORKGROUP"}

# Erstelle Zeitstempel für Backup-Dateinamen
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="mysql_backup_${MYSQL_DATABASE}_${TIMESTAMP}.sql.gz"

# Logfunktion
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> /app/logs/backup.log
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Prüfe, ob die Konfigurationsdatei existiert
if [ ! -f "$CONFIG_FILE" ]; then
    log "FEHLER: Konfigurationsdatei $CONFIG_FILE nicht gefunden!"
    exit 1
fi

# Prüfe, ob die Datenbank angegeben wurde
if [ -z "$MYSQL_DATABASE" ]; then
    log "FEHLER: Keine Datenbank angegeben!"
    exit 1
fi

# Erstelle lokales Backup-Verzeichnis, falls es nicht existiert
mkdir -p "$BACKUP_DIR"

# Führe MySQL-Backup durch
log "Starte Backup der Datenbank $MYSQL_DATABASE auf $MYSQL_HOST..."

if [ -z "$MYSQL_PASSWORD" ]; then
    # Ohne Passwort
    mysqldump --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" \
        --single-transaction --quick --lock-tables=false "$MYSQL_DATABASE" | gzip > "$BACKUP_DIR/$BACKUP_FILE"
else
    # Mit Passwort
    mysqldump --host="$MYSQL_HOST" --port="$MYSQL_PORT" --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" \
        --single-transaction --quick --lock-tables=false "$MYSQL_DATABASE" | gzip > "$BACKUP_DIR/$BACKUP_FILE"
fi

# Prüfe, ob das Backup erfolgreich war
if [ $? -eq 0 ]; then
    log "Backup erfolgreich erstellt: $BACKUP_FILE ($(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1))"
else
    log "FEHLER: Backup fehlgeschlagen!"
    exit 1
fi

# Wenn SMB aktiviert ist, kopiere das Backup auf den SMB-Share
if [ "$SMB_ENABLED" = "true" ] && [ ! -z "$SMB_SHARE" ]; then
    log "Kopiere Backup auf SMB-Share $SMB_SHARE..."
    
    # Erstelle Mount-Verzeichnis, falls es nicht existiert
    mkdir -p "$SMB_MOUNT"
    
    # Mounte SMB-Share
    if [ -z "$SMB_PASSWORD" ]; then
        # Ohne Passwort
        mount -t cifs "$SMB_SHARE" "$SMB_MOUNT" -o username="$SMB_USER",domain="$SMB_DOMAIN"
    else
        # Mit Passwort
        mount -t cifs "$SMB_SHARE" "$SMB_MOUNT" -o username="$SMB_USER",password="$SMB_PASSWORD",domain="$SMB_DOMAIN"
    fi
    
    # Prüfe, ob das Mounten erfolgreich war
    if [ $? -eq 0 ]; then
        log "SMB-Share erfolgreich gemountet."
        
        # Erstelle Backup-Verzeichnis auf dem Share, falls es nicht existiert
        mkdir -p "$SMB_MOUNT/mysql_backups"
        
        # Kopiere Backup-Datei
        cp "$BACKUP_DIR/$BACKUP_FILE" "$SMB_MOUNT/mysql_backups/"
        
        # Prüfe, ob das Kopieren erfolgreich war
        if [ $? -eq 0 ]; then
            log "Backup erfolgreich auf SMB-Share kopiert."
        else
            log "FEHLER: Kopieren auf SMB-Share fehlgeschlagen!"
        fi
        
        # Unmounte SMB-Share
        umount "$SMB_MOUNT"
    else
        log "FEHLER: Mounten des SMB-Shares fehlgeschlagen!"
    fi
fi

# Lösche alte Backups basierend auf der Aufbewahrungsdauer
if [ "$BACKUP_RETENTION" -gt 0 ]; then
    log "Lösche Backups, die älter als $BACKUP_RETENTION Tage sind..."
    
    # Lokale Backups
    find "$BACKUP_DIR" -name "mysql_backup_${MYSQL_DATABASE}_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -delete
    
    # SMB-Backups, falls aktiviert
    if [ "$SMB_ENABLED" = "true" ] && [ ! -z "$SMB_SHARE" ]; then
        # Mounte SMB-Share erneut
        if [ -z "$SMB_PASSWORD" ]; then
            mount -t cifs "$SMB_SHARE" "$SMB_MOUNT" -o username="$SMB_USER",domain="$SMB_DOMAIN"
        else
            mount -t cifs "$SMB_SHARE" "$SMB_MOUNT" -o username="$SMB_USER",password="$SMB_PASSWORD",domain="$SMB_DOMAIN"
        fi
        
        if [ $? -eq 0 ]; then
            find "$SMB_MOUNT/mysql_backups" -name "mysql_backup_${MYSQL_DATABASE}_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -delete
            umount "$SMB_MOUNT"
        fi
    fi
fi

log "Backup-Vorgang abgeschlossen."
exit 0
