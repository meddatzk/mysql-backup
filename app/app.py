#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_wtf import CSRFProtect
from werkzeug.utils import secure_filename
import configparser
import logging

# Konfiguriere Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/webapp.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialisiere Flask-App
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mysecretkey')
csrf = CSRFProtect(app)

# Konfigurationsdateien
CONFIG_DIR = '/app/config'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'backup.conf')
CONFIG_EXAMPLE = os.path.join(CONFIG_DIR, 'backup.conf.example')
SCHEDULER_CONFIG = os.path.join(CONFIG_DIR, 'scheduler.json')

# Backup-Skript
BACKUP_SCRIPT = '/app/scripts/backup.sh'

# Stelle sicher, dass die Konfigurationsdateien existieren
def ensure_config_files():
    # Erstelle Konfigurationsverzeichnis, falls es nicht existiert
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Erstelle backup.conf, falls sie nicht existiert
    if not os.path.exists(CONFIG_FILE) and os.path.exists(CONFIG_EXAMPLE):
        with open(CONFIG_EXAMPLE, 'r') as src, open(CONFIG_FILE, 'w') as dst:
            dst.write(src.read())
        logger.info(f"Konfigurationsdatei {CONFIG_FILE} erstellt.")
    
    # Erstelle scheduler.json, falls sie nicht existiert
    if not os.path.exists(SCHEDULER_CONFIG):
        default_scheduler = {
            "enabled": False,
            "schedule": "daily",
            "time": "00:00",
            "day_of_week": "1",  # Montag
            "day_of_month": "1"
        }
        with open(SCHEDULER_CONFIG, 'w') as f:
            json.dump(default_scheduler, f, indent=4)
        logger.info(f"Scheduler-Konfiguration {SCHEDULER_CONFIG} erstellt.")

# Lade die Backup-Konfiguration
def load_backup_config():
    config = {}
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip('"\'')
    
    return config

# Speichere die Backup-Konfiguration
def save_backup_config(config):
    with open(CONFIG_FILE, 'w') as f:
        f.write("# MySQL-Backup-Konfiguration\n")
        f.write("# Automatisch generiert durch die Weboberfläche\n\n")
        
        f.write("# MySQL-Verbindungsdaten\n")
        f.write(f'MYSQL_HOST="{config.get("MYSQL_HOST", "localhost")}"\n')
        f.write(f'MYSQL_PORT="{config.get("MYSQL_PORT", "3306")}"\n')
        f.write(f'MYSQL_USER="{config.get("MYSQL_USER", "root")}"\n')
        f.write(f'MYSQL_PASSWORD="{config.get("MYSQL_PASSWORD", "")}"\n')
        f.write(f'MYSQL_DATABASE="{config.get("MYSQL_DATABASE", "")}"\n\n')
        
        f.write("# Backup-Einstellungen\n")
        f.write(f'BACKUP_DIR="{config.get("BACKUP_DIR", "/app/backups")}"\n')
        f.write(f'BACKUP_RETENTION="{config.get("BACKUP_RETENTION", "7")}"\n\n')
        
        f.write("# SMB-Share-Einstellungen\n")
        f.write(f'SMB_ENABLED="{config.get("SMB_ENABLED", "false")}"\n')
        f.write(f'SMB_SHARE="{config.get("SMB_SHARE", "")}"\n')
        f.write(f'SMB_MOUNT="{config.get("SMB_MOUNT", "/mnt/backup")}"\n')
        f.write(f'SMB_USER="{config.get("SMB_USER", "")}"\n')
        f.write(f'SMB_PASSWORD="{config.get("SMB_PASSWORD", "")}"\n')
        f.write(f'SMB_DOMAIN="{config.get("SMB_DOMAIN", "WORKGROUP")}"\n')

# Lade die Scheduler-Konfiguration
def load_scheduler_config():
    if os.path.exists(SCHEDULER_CONFIG):
        with open(SCHEDULER_CONFIG, 'r') as f:
            return json.load(f)
    return {
        "enabled": False,
        "schedule": "daily",
        "time": "00:00",
        "day_of_week": "1",
        "day_of_month": "1"
    }

# Speichere die Scheduler-Konfiguration
def save_scheduler_config(config):
    with open(SCHEDULER_CONFIG, 'w') as f:
        json.dump(config, f, indent=4)

# Führe ein manuelles Backup durch
def run_backup():
    try:
        result = subprocess.run([BACKUP_SCRIPT], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("Backup erfolgreich durchgeführt.")
            return True, result.stdout
        else:
            logger.error(f"Backup fehlgeschlagen: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        logger.exception("Fehler beim Ausführen des Backups")
        return False, str(e)

# Liste alle Backups auf
def list_backups():
    backups = []
    config = load_backup_config()
    backup_dir = config.get('BACKUP_DIR', '/app/backups')
    
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.startswith('mysql_backup_') and file.endswith('.sql.gz'):
                file_path = os.path.join(backup_dir, file)
                file_stat = os.stat(file_path)
                file_size = file_stat.st_size
                file_date = datetime.datetime.fromtimestamp(file_stat.st_mtime)
                
                # Extrahiere Datenbankname aus Dateinamen
                parts = file.split('_')
                if len(parts) >= 3:
                    db_name = parts[2]
                else:
                    db_name = "unbekannt"
                
                backups.append({
                    'filename': file,
                    'database': db_name,
                    'size': file_size,
                    'date': file_date,
                    'path': file_path
                })
    
    # Sortiere nach Datum (neueste zuerst)
    backups.sort(key=lambda x: x['date'], reverse=True)
    return backups

# Lösche ein Backup
def delete_backup(filename):
    config = load_backup_config()
    backup_dir = config.get('BACKUP_DIR', '/app/backups')
    file_path = os.path.join(backup_dir, filename)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Backup {filename} gelöscht.")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Backups {filename}: {e}")
            return False
    else:
        logger.error(f"Backup {filename} nicht gefunden.")
        return False

# Routen
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        # Speichere Konfiguration
        config_data = {
            'MYSQL_HOST': request.form.get('mysql_host', 'localhost'),
            'MYSQL_PORT': request.form.get('mysql_port', '3306'),
            'MYSQL_USER': request.form.get('mysql_user', 'root'),
            'MYSQL_PASSWORD': request.form.get('mysql_password', ''),
            'MYSQL_DATABASE': request.form.get('mysql_database', ''),
            'BACKUP_DIR': request.form.get('backup_dir', '/app/backups'),
            'BACKUP_RETENTION': request.form.get('backup_retention', '7'),
            'SMB_ENABLED': 'true' if request.form.get('smb_enabled') else 'false',
            'SMB_SHARE': request.form.get('smb_share', ''),
            'SMB_MOUNT': request.form.get('smb_mount', '/mnt/backup'),
            'SMB_USER': request.form.get('smb_user', ''),
            'SMB_PASSWORD': request.form.get('smb_password', ''),
            'SMB_DOMAIN': request.form.get('smb_domain', 'WORKGROUP')
        }
        
        save_backup_config(config_data)
        flash('Konfiguration gespeichert', 'success')
        return redirect(url_for('config'))
    
    # Lade aktuelle Konfiguration
    config_data = load_backup_config()
    return render_template('config.html', config=config_data)

@app.route('/scheduler', methods=['GET', 'POST'])
def scheduler():
    if request.method == 'POST':
        # Speichere Scheduler-Konfiguration
        scheduler_data = {
            'enabled': True if request.form.get('enabled') else False,
            'schedule': request.form.get('schedule', 'daily'),
            'time': request.form.get('time', '00:00'),
            'day_of_week': request.form.get('day_of_week', '1'),
            'day_of_month': request.form.get('day_of_month', '1')
        }
        
        save_scheduler_config(scheduler_data)
        flash('Scheduler-Konfiguration gespeichert', 'success')
        return redirect(url_for('scheduler'))
    
    # Lade aktuelle Scheduler-Konfiguration
    scheduler_data = load_scheduler_config()
    return render_template('scheduler.html', config=scheduler_data)

@app.route('/backups')
def backups():
    backup_list = list_backups()
    return render_template('backups.html', backups=backup_list)

@app.route('/run_backup', methods=['POST'])
def trigger_backup():
    success, message = run_backup()
    if success:
        flash('Backup erfolgreich durchgeführt', 'success')
    else:
        flash(f'Backup fehlgeschlagen: {message}', 'danger')
    return redirect(url_for('backups'))

@app.route('/download_backup/<filename>')
def download_backup(filename):
    config = load_backup_config()
    backup_dir = config.get('BACKUP_DIR', '/app/backups')
    file_path = os.path.join(backup_dir, filename)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        from flask import send_file
        return send_file(file_path, as_attachment=True)
    else:
        flash(f'Backup {filename} nicht gefunden.', 'danger')
        return redirect(url_for('backups'))

@app.route('/delete_backup/<filename>', methods=['POST'])
def delete_backup_route(filename):
    if delete_backup(filename):
        flash(f'Backup {filename} erfolgreich gelöscht.', 'success')
    else:
        flash(f'Fehler beim Löschen des Backups {filename}.', 'danger')
    return redirect(url_for('backups'))

# Stelle sicher, dass die Konfigurationsdateien existieren
ensure_config_files()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
