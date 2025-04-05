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

# Führe MySQL-Backup durch
log "Verwende lokalen MySQL-Client für das Backup..."
mysqldump -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" \
    --single-transaction --quick --lock-tables=false \
    "$MYSQL_DATABASE" | gzip > "$BACKUP_DIR/$BACKUP_FILE"

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
    log "Mount-Verzeichnis: $SMB_MOUNT"
    
    # Prüfe, ob das SMB-Share erreichbar ist
    ping -c 1 $(echo "$SMB_SHARE" | cut -d'/' -f3) > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log "WARNUNG: SMB-Server scheint nicht erreichbar zu sein. Ping fehlgeschlagen."
    fi
    
    # Mounte SMB-Share mit detailliertem Logging
    log "Versuche SMB-Share zu mounten..."
    MOUNT_CMD=""
    MOUNT_LOG=""
    
    if [ -z "$SMB_PASSWORD" ]; then
        # Ohne Passwort
        log "Mount ohne Passwort mit Benutzer: $SMB_USER, Domain: $SMB_DOMAIN"
        MOUNT_CMD="mount -t cifs \"$SMB_SHARE\" \"$SMB_MOUNT\" -o username=\"$SMB_USER\",domain=\"$SMB_DOMAIN\",vers=3.0"
        MOUNT_LOG=$(eval $MOUNT_CMD 2>&1)
        MOUNT_STATUS=$?
    else
        # Mit Passwort
        log "Mount mit Passwort mit Benutzer: $SMB_USER, Domain: $SMB_DOMAIN"
        MOUNT_CMD="mount -t cifs \"$SMB_SHARE\" \"$SMB_MOUNT\" -o username=\"$SMB_USER\",password=\"********\",domain=\"$SMB_DOMAIN\",vers=3.0"
        MOUNT_LOG=$(mount -t cifs "$SMB_SHARE" "$SMB_MOUNT" -o username="$SMB_USER",password="$SMB_PASSWORD",domain="$SMB_DOMAIN",vers=3.0 2>&1)
        MOUNT_STATUS=$?
    fi
    
    # Prüfe, ob das Mounten erfolgreich war
    if [ $MOUNT_STATUS -eq 0 ]; then
        log "SMB-Share erfolgreich gemountet."
        
        # Erstelle Backup-Verzeichnis auf dem Share, falls es nicht existiert
        log "Erstelle Backup-Verzeichnis auf dem Share: $SMB_MOUNT/mysql_backups"
        mkdir -p "$SMB_MOUNT/mysql_backups"
        
        if [ $? -ne 0 ]; then
            log "FEHLER: Konnte Backup-Verzeichnis auf dem Share nicht erstellen. Prüfe die Berechtigungen."
        else
            # Kopiere Backup-Datei
            log "Kopiere Backup-Datei: $BACKUP_FILE ($(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1))"
            cp "$BACKUP_DIR/$BACKUP_FILE" "$SMB_MOUNT/mysql_backups/"
            
            # Prüfe, ob das Kopieren erfolgreich war
            if [ $? -eq 0 ]; then
                log "Backup erfolgreich auf SMB-Share kopiert: $SMB_MOUNT/mysql_backups/$BACKUP_FILE"
            else
                log "FEHLER: Kopieren auf SMB-Share fehlgeschlagen! Prüfe die Berechtigungen und den verfügbaren Speicherplatz."
            fi
        fi
        
        # Unmounte SMB-Share
        log "Unmounte SMB-Share..."
        umount "$SMB_MOUNT"
        
        if [ $? -ne 0 ]; then
            log "WARNUNG: Konnte SMB-Share nicht unmounten. Möglicherweise wird es noch verwendet."
        else
            log "SMB-Share erfolgreich unmountet."
        fi
    else
        log "FEHLER: Mounten des SMB-Shares fehlgeschlagen!"
        log "Mount-Befehl: $MOUNT_CMD"
        log "Mount-Fehler: $MOUNT_LOG"
        log "Prüfe folgende mögliche Ursachen:"
        log "  - Ist der SMB-Server erreichbar?"
        log "  - Sind Benutzername und Passwort korrekt?"
        log "  - Existiert der Share auf dem Server?"
        log "  - Sind die Berechtigungen korrekt konfiguriert?"
        log "  - Ist die SMB-Version kompatibel? (Versuche ggf. vers=2.0 oder vers=1.0)"
    fi
fi

# Lösche alte Backups basierend auf der Aufbewahrungsdauer
if [ "$BACKUP_RETENTION" -gt 0 ]; then
    log "Lösche Backups, die älter als $BACKUP_RETENTION Tage sind..."
    
    # Lokale Backups
    log "Lösche alte lokale Backups..."
    DELETED_COUNT=$(find "$BACKUP_DIR" -name "mysql_backup_${MYSQL_DATABASE}_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -print | wc -l)
    find "$BACKUP_DIR" -name "mysql_backup_${MYSQL_DATABASE}_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -delete
    log "Gelöschte lokale Backups: $DELETED_COUNT"
    
    # SMB-Backups, falls aktiviert
    if [ "$SMB_ENABLED" = "true" ] && [ ! -z "$SMB_SHARE" ]; then
        log "Lösche alte Backups auf dem SMB-Share..."
        
        # Mounte SMB-Share erneut
        log "Mounte SMB-Share erneut für die Bereinigung..."
        MOUNT_CMD=""
        MOUNT_LOG=""
        
        if [ -z "$SMB_PASSWORD" ]; then
            # Ohne Passwort
            MOUNT_CMD="mount -t cifs \"$SMB_SHARE\" \"$SMB_MOUNT\" -o username=\"$SMB_USER\",domain=\"$SMB_DOMAIN\",vers=3.0"
            MOUNT_LOG=$(eval $MOUNT_CMD 2>&1)
            MOUNT_STATUS=$?
        else
            # Mit Passwort
            MOUNT_CMD="mount -t cifs \"$SMB_SHARE\" \"$SMB_MOUNT\" -o username=\"$SMB_USER\",password=\"********\",domain=\"$SMB_DOMAIN\",vers=3.0"
            MOUNT_LOG=$(mount -t cifs "$SMB_SHARE" "$SMB_MOUNT" -o username="$SMB_USER",password="$SMB_PASSWORD",domain="$SMB_DOMAIN",vers=3.0 2>&1)
            MOUNT_STATUS=$?
        fi
        
        if [ $MOUNT_STATUS -eq 0 ]; then
            log "SMB-Share erfolgreich für die Bereinigung gemountet."
            
            # Prüfe, ob das Backup-Verzeichnis existiert
            if [ -d "$SMB_MOUNT/mysql_backups" ]; then
                # Zähle zu löschende Dateien
                SMB_DELETED_COUNT=$(find "$SMB_MOUNT/mysql_backups" -name "mysql_backup_${MYSQL_DATABASE}_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -print | wc -l)
                
                # Lösche alte Backups
                find "$SMB_MOUNT/mysql_backups" -name "mysql_backup_${MYSQL_DATABASE}_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -delete
                
                log "Gelöschte Backups auf dem SMB-Share: $SMB_DELETED_COUNT"
            else
                log "Backup-Verzeichnis auf dem SMB-Share nicht gefunden."
            fi
            
            # Unmounte SMB-Share
            log "Unmounte SMB-Share nach der Bereinigung..."
            umount "$SMB_MOUNT"
            
            if [ $? -ne 0 ]; then
                log "WARNUNG: Konnte SMB-Share nach der Bereinigung nicht unmounten."
            else
                log "SMB-Share nach der Bereinigung erfolgreich unmountet."
            fi
        else
            log "FEHLER: Konnte SMB-Share für die Bereinigung nicht mounten."
            log "Mount-Fehler: $MOUNT_LOG"
        fi
    fi
fi

log "Backup-Vorgang abgeschlossen."
exit 0
