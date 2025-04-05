#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import logging
import subprocess
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Konfigurationsdateien
CONFIG_DIR = '/app/config'
SCHEDULER_CONFIG = os.path.join(CONFIG_DIR, 'scheduler.json')

# Backup-Skript
BACKUP_SCRIPT = '/app/scripts/backup.sh'

# Initialisiere Scheduler
scheduler = BackgroundScheduler()

# Führe Backup aus
def run_backup():
    logger.info("Starte geplantes Backup...")
    try:
        result = subprocess.run([BACKUP_SCRIPT], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Geplantes Backup erfolgreich durchgeführt.")
        else:
            logger.error(f"Geplantes Backup fehlgeschlagen: {result.stderr}")
    except Exception as e:
        logger.exception("Fehler beim Ausführen des geplanten Backups")

# Lade die Scheduler-Konfiguration
def load_scheduler_config():
    if os.path.exists(SCHEDULER_CONFIG):
        try:
            with open(SCHEDULER_CONFIG, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.exception(f"Fehler beim Laden der Scheduler-Konfiguration: {e}")
    
    # Standardkonfiguration
    return {
        "enabled": False,
        "schedule": "daily",
        "time": "00:00",
        "day_of_week": "1",
        "day_of_month": "1"
    }

# Konfiguriere den Scheduler basierend auf der Konfiguration
def configure_scheduler():
    # Entferne alle vorhandenen Jobs
    scheduler.remove_all_jobs()
    
    # Lade Konfiguration
    config = load_scheduler_config()
    
    # Wenn der Scheduler nicht aktiviert ist, beende hier
    if not config.get("enabled", False):
        logger.info("Scheduler ist deaktiviert.")
        return
    
    # Parse Zeit
    try:
        hour, minute = config.get("time", "00:00").split(":")
        hour = int(hour)
        minute = int(minute)
    except Exception:
        logger.error("Ungültiges Zeitformat in der Konfiguration. Verwende 00:00.")
        hour, minute = 0, 0
    
    # Konfiguriere Job basierend auf dem Zeitplan
    schedule_type = config.get("schedule", "daily")
    
    if schedule_type == "hourly":
        # Stündlich
        scheduler.add_job(run_backup, 'cron', minute=minute, id='backup_job')
        logger.info(f"Backup-Job konfiguriert: Stündlich um XX:{minute}")
    
    elif schedule_type == "daily":
        # Täglich
        scheduler.add_job(run_backup, 'cron', hour=hour, minute=minute, id='backup_job')
        logger.info(f"Backup-Job konfiguriert: Täglich um {hour:02d}:{minute:02d}")
    
    elif schedule_type == "weekly":
        # Wöchentlich
        day_of_week = int(config.get("day_of_week", "1"))
        scheduler.add_job(run_backup, 'cron', day_of_week=day_of_week, hour=hour, minute=minute, id='backup_job')
        logger.info(f"Backup-Job konfiguriert: Wöchentlich am Tag {day_of_week} um {hour:02d}:{minute:02d}")
    
    elif schedule_type == "monthly":
        # Monatlich
        day_of_month = int(config.get("day_of_month", "1"))
        scheduler.add_job(run_backup, 'cron', day=day_of_month, hour=hour, minute=minute, id='backup_job')
        logger.info(f"Backup-Job konfiguriert: Monatlich am Tag {day_of_month} um {hour:02d}:{minute:02d}")
    
    else:
        logger.error(f"Unbekannter Zeitplan: {schedule_type}")

# Überwache Änderungen an der Konfigurationsdatei
def watch_config_changes():
    last_modified = 0
    
    while True:
        try:
            # Prüfe, ob die Konfigurationsdatei existiert
            if os.path.exists(SCHEDULER_CONFIG):
                # Prüfe, ob die Datei geändert wurde
                current_modified = os.path.getmtime(SCHEDULER_CONFIG)
                
                if current_modified > last_modified:
                    logger.info("Scheduler-Konfiguration wurde geändert. Konfiguriere Scheduler neu...")
                    configure_scheduler()
                    last_modified = current_modified
        
        except Exception as e:
            logger.exception(f"Fehler beim Überwachen der Konfigurationsdatei: {e}")
        
        # Warte 10 Sekunden
        time.sleep(10)

# Hauptfunktion
def main():
    logger.info("Starte Backup-Scheduler...")
    
    # Initialisiere Scheduler
    configure_scheduler()
    scheduler.start()
    
    try:
        # Überwache Änderungen an der Konfigurationsdatei
        watch_config_changes()
    except KeyboardInterrupt:
        logger.info("Scheduler wird beendet...")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
