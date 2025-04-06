#!/bin/bash

# MySQL-Backup-Skript

# Lese Konfiguration
CONFIG_FILE="/app/config/backup.conf"
source "$CONFIG_FILE"

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

# Setze Standardwerte für allgemeine Einstellungen
BACKUP_DIR=${BACKUP_DIR:-"/app/backups"}
BACKUP_RETENTION=${BACKUP_RETENTION:-"7"}
SMB_ENABLED=${SMB_ENABLED:-"false"}
SMB_SHARE=${SMB_SHARE:-""}
SMB_MOUNT=${SMB_MOUNT:-"/mnt/backup"}
SMB_USER=${SMB_USER:-""}
SMB_PASSWORD=${SMB_PASSWORD:-""}
SMB_DOMAIN=${SMB_DOMAIN:-"WORKGROUP"}

# Erstelle lokales Backup-Verzeichnis, falls es nicht existiert
mkdir -p "$BACKUP_DIR"

# Funktion zum Erstellen eines Backups für eine Datenbank
backup_database() {
    local db_id=$1
    local db_name=$(eval echo \$DB_${db_id}_NAME)
    local db_host=$(eval echo \$DB_${db_id}_HOST)
    local db_port=$(eval echo \$DB_${db_id}_PORT)
    local db_user=$(eval echo \$DB_${db_id}_USER)
    local db_password=$(eval echo \$DB_${db_id}_PASSWORD)
    local db_database=$(eval echo \$DB_${db_id}_DATABASE)
    
    # Setze Standardwerte, falls nicht in der Konfiguration definiert
    db_host=${db_host:-"localhost"}
    db_port=${db_port:-"3306"}
    db_user=${db_user:-"root"}
    db_password=${db_password:-""}
    
    # Prüfe, ob die Datenbank angegeben wurde
    if [ -z "$db_database" ]; then
        log "FEHLER: Keine Datenbank für DB_${db_id} angegeben!"
        return 1
    fi
    
    # Erstelle Zeitstempel für Backup-Dateinamen
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="mysql_backup_${db_id}_${db_database}_${TIMESTAMP}.sql.gz"
    
    log "Starte Backup der Datenbank $db_database (ID: $db_id) auf $db_host..."
    
    # Führe MySQL-Backup durch
    log "Verwende lokalen MySQL-Client für das Backup..."
    mysqldump -h "$db_host" -P "$db_port" -u "$db_user" -p"$db_password" \
        --single-transaction --quick --lock-tables=false \
        "$db_database" | gzip > "$BACKUP_DIR/$BACKUP_FILE"
    
    # Prüfe, ob das Backup erfolgreich war
    if [ $? -eq 0 ]; then
        log "Backup erfolgreich erstellt: $BACKUP_FILE ($(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1))"
        
        # Wenn SMB aktiviert ist, kopiere das Backup auf den SMB-Share
        if [ "$SMB_ENABLED" = "true" ] && [ ! -z "$SMB_SHARE" ]; then
            copy_to_smb "$BACKUP_FILE"
        fi
        
        return 0
    else
        log "FEHLER: Backup für Datenbank $db_database (ID: $db_id) fehlgeschlagen!"
        return 1
    fi
}

# Funktion zum Kopieren eines Backups auf den SMB-Share
copy_to_smb() {
    local backup_file=$1
    
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
            log "Kopiere Backup-Datei: $backup_file ($(du -h "$BACKUP_DIR/$backup_file" | cut -f1))"
            cp "$BACKUP_DIR/$backup_file" "$SMB_MOUNT/mysql_backups/"
            
            # Prüfe, ob das Kopieren erfolgreich war
            if [ $? -eq 0 ]; then
                log "Backup erfolgreich auf SMB-Share kopiert: $SMB_MOUNT/mysql_backups/$backup_file"
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
}

# Funktion zum Löschen alter Backups
cleanup_old_backups() {
    if [ "$BACKUP_RETENTION" -gt 0 ]; then
        log "Lösche Backups, die älter als $BACKUP_RETENTION Tage sind..."
        
        # Lokale Backups
        log "Lösche alte lokale Backups..."
        DELETED_COUNT=$(find "$BACKUP_DIR" -name "mysql_backup_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -print | wc -l)
        find "$BACKUP_DIR" -name "mysql_backup_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -delete
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
                    SMB_DELETED_COUNT=$(find "$SMB_MOUNT/mysql_backups" -name "mysql_backup_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -print | wc -l)
                    
                    # Lösche alte Backups
                    find "$SMB_MOUNT/mysql_backups" -name "mysql_backup_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -delete
                    
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
}

# Hauptfunktion
main() {
    # Prüfe, ob eine spezifische Datenbank-ID als Parameter übergeben wurde
    if [ $# -eq 1 ]; then
        db_id=$1
        log "Starte Backup für Datenbank mit ID $db_id..."
        backup_database "$db_id"
        backup_status=$?
    else
        # Für Abwärtskompatibilität: Wenn alte Konfiguration vorhanden ist, verwende diese
        if [ ! -z "$MYSQL_DATABASE" ]; then
            log "Verwende alte Konfiguration für Abwärtskompatibilität..."
            
            # Setze Standardwerte, falls nicht in der Konfiguration definiert
            MYSQL_HOST=${MYSQL_HOST:-"localhost"}
            MYSQL_PORT=${MYSQL_PORT:-"3306"}
            MYSQL_USER=${MYSQL_USER:-"root"}
            MYSQL_PASSWORD=${MYSQL_PASSWORD:-""}
            
            # Erstelle Zeitstempel für Backup-Dateinamen
            TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
            BACKUP_FILE="mysql_backup_${MYSQL_DATABASE}_${TIMESTAMP}.sql.gz"
            
            log "Starte Backup der Datenbank $MYSQL_DATABASE auf $MYSQL_HOST..."
            
            # Führe MySQL-Backup durch
            mysqldump -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" \
                --single-transaction --quick --lock-tables=false \
                "$MYSQL_DATABASE" | gzip > "$BACKUP_DIR/$BACKUP_FILE"
            
            # Prüfe, ob das Backup erfolgreich war
            if [ $? -eq 0 ]; then
                log "Backup erfolgreich erstellt: $BACKUP_FILE ($(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1))"
                
                # Wenn SMB aktiviert ist, kopiere das Backup auf den SMB-Share
                if [ "$SMB_ENABLED" = "true" ] && [ ! -z "$SMB_SHARE" ]; then
                    copy_to_smb "$BACKUP_FILE"
                fi
                
                backup_status=0
            else
                log "FEHLER: Backup fehlgeschlagen!"
                backup_status=1
            fi
        else
            # Suche nach allen konfigurierten Datenbanken
            log "Suche nach konfigurierten Datenbanken..."
            db_ids=()
            
            # Durchsuche die Konfigurationsdatei nach Datenbankeinträgen
            while IFS='=' read -r key value; do
                if [[ $key == DB_*_NAME ]]; then
                    db_id=$(echo $key | cut -d'_' -f2)
                    db_ids+=($db_id)
                fi
            done < <(grep -E "^DB_[0-9]+_NAME=" "$CONFIG_FILE")
            
            # Sortiere die IDs numerisch
            IFS=$'\n' db_ids=($(sort -n <<<"${db_ids[*]}"))
            unset IFS
            
            if [ ${#db_ids[@]} -eq 0 ]; then
                log "FEHLER: Keine Datenbanken in der Konfiguration gefunden!"
                exit 1
            fi
            
            log "Gefundene Datenbanken: ${db_ids[@]}"
            
            # Führe Backup für jede Datenbank durch
            all_success=true
            for db_id in "${db_ids[@]}"; do
                backup_database "$db_id"
                if [ $? -ne 0 ]; then
                    all_success=false
                fi
            done
            
            if [ "$all_success" = true ]; then
                backup_status=0
            else
                backup_status=1
            fi
        fi
    fi
    
    # Lösche alte Backups
    cleanup_old_backups
    
    log "Backup-Vorgang abgeschlossen."
    exit $backup_status
}

# Starte Hauptfunktion
main "$@"
