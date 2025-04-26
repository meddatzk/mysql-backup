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

# Lade Versionsinformation
def load_version():
    try:
        with open('/app/version.json', 'r') as f:
            version_data = json.load(f)
            return version_data.get('version', 'unbekannt')
    except Exception as e:
        logger.error(f"Fehler beim Laden der Versionsinformation: {e}")
        return 'unbekannt'

# Globale Variable für die Version
APP_VERSION = load_version()

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

# Lade Datenbank-Konfigurationen
def load_database_configs():
    config = load_backup_config()
    databases = []
    db_ids = set()
    
    # Finde alle konfigurierten Datenbanken
    for key in config.keys():
        if key.startswith('DB_') and '_NAME' in key:
            db_id = key.split('_')[1]
            db_ids.add(db_id)
    
    # Sortiere die IDs numerisch
    db_ids = sorted(db_ids, key=int)
    
    # Erstelle für jede Datenbank eine Konfiguration
    for db_id in db_ids:
        prefix = f'DB_{db_id}_'
        db_config = {
            'id': db_id,
            'name': config.get(f'{prefix}NAME', f'Datenbank {db_id}'),
            'host': config.get(f'{prefix}HOST', 'localhost'),
            'port': config.get(f'{prefix}PORT', '3306'),
            'user': config.get(f'{prefix}USER', 'root'),
            'password': config.get(f'{prefix}PASSWORD', ''),
            'database': config.get(f'{prefix}DATABASE', '')
        }
        databases.append(db_config)
    
    # Wenn keine Datenbanken konfiguriert sind, erstelle eine Standard-Datenbank
    if not databases:
        # Für Abwärtskompatibilität: Wenn alte Konfiguration vorhanden ist, verwende diese
        if 'MYSQL_HOST' in config:
            databases.append({
                'id': '1',
                'name': 'Datenbank 1',
                'host': config.get('MYSQL_HOST', 'localhost'),
                'port': config.get('MYSQL_PORT', '3306'),
                'user': config.get('MYSQL_USER', 'root'),
                'password': config.get('MYSQL_PASSWORD', ''),
                'database': config.get('MYSQL_DATABASE', '')
            })
        else:
            # Sonst erstelle eine leere Standard-Datenbank
            databases.append({
                'id': '1',
                'name': 'Datenbank 1',
                'host': 'localhost',
                'port': '3306',
                'user': 'root',
                'password': '',
                'database': ''
            })
    
    return databases

# Speichere die Backup-Konfiguration
def save_backup_config(config, databases):
    with open(CONFIG_FILE, 'w') as f:
        f.write("# MySQL-Backup-Konfiguration\n")
        f.write("# Automatisch generiert durch die Weboberfläche\n\n")
        
        f.write("# Allgemeine Backup-Einstellungen\n")
        f.write(f'BACKUP_DIR="{config.get("BACKUP_DIR", "/app/backups")}"\n')
        f.write(f'BACKUP_RETENTION="{config.get("BACKUP_RETENTION", "7")}"\n\n')
        
        f.write("# SMB-Share-Einstellungen\n")
        f.write(f'SMB_ENABLED="{config.get("SMB_ENABLED", "false")}"\n')
        f.write(f'SMB_SHARE="{config.get("SMB_SHARE", "")}"\n')
        f.write(f'SMB_MOUNT="{config.get("SMB_MOUNT", "/mnt/backup")}"\n')
        f.write(f'SMB_USER="{config.get("SMB_USER", "")}"\n')
        f.write(f'SMB_PASSWORD="{config.get("SMB_PASSWORD", "")}"\n')
        f.write(f'SMB_DOMAIN="{config.get("SMB_DOMAIN", "WORKGROUP")}"\n\n')
        
        f.write("# Datenbank-Konfigurationen\n")
        for db in databases:
            db_id = db.get('id', '1')
            f.write(f'# Datenbank {db_id}\n')
            f.write(f'DB_{db_id}_NAME="{db.get("name", f"Datenbank {db_id}")}"\n')
            f.write(f'DB_{db_id}_HOST="{db.get("host", "localhost")}"\n')
            f.write(f'DB_{db_id}_PORT="{db.get("port", "3306")}"\n')
            f.write(f'DB_{db_id}_USER="{db.get("user", "root")}"\n')
            f.write(f'DB_{db_id}_PASSWORD="{db.get("password", "")}"\n')
            f.write(f'DB_{db_id}_DATABASE="{db.get("database", "")}"\n\n')

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
def run_backup(db_id=None):
    try:
        if db_id:
            # Backup einer einzelnen Datenbank
            result = subprocess.run([BACKUP_SCRIPT, db_id], capture_output=True, text=True)
        else:
            # Backup mit Standard-Konfiguration (für Abwärtskompatibilität)
            result = subprocess.run([BACKUP_SCRIPT], capture_output=True, text=True)
            
        if result.returncode == 0:
            logger.info(f"Backup für Datenbank {db_id if db_id else 'Standard'} erfolgreich durchgeführt.")
            return True, result.stdout
        else:
            logger.error(f"Backup für Datenbank {db_id if db_id else 'Standard'} fehlgeschlagen: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        logger.exception(f"Fehler beim Ausführen des Backups für Datenbank {db_id if db_id else 'Standard'}")
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
                
                # Extrahiere Datenbankname und ID aus Dateinamen
                # Neues Format: mysql_backup_[DB_ID]_[DB_NAME]_[TIMESTAMP].sql.gz
                parts = file.split('_')
                if len(parts) >= 5:  # Neues Format mit DB_ID
                    db_id = parts[2]
                    db_name = parts[3]
                elif len(parts) >= 3:  # Altes Format
                    db_id = "1"  # Standard-ID für alte Backups
                    db_name = parts[2]
                else:
                    db_id = "1"
                    db_name = "unbekannt"
                
                backups.append({
                    'filename': file,
                    'db_id': db_id,
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
    return render_template('index.html', version=APP_VERSION)

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        # Debug-Ausgabe aller Formularfelder
        print("DEBUG - Formularfelder:", flush=True)
        for key, value in request.form.items():
            print(f"  {key}: {value}", flush=True)
        
        # Allgemeine Konfiguration
        config_data = {
            'BACKUP_DIR': request.form.get('backup_dir', '/app/backups'),
            'BACKUP_RETENTION': request.form.get('backup_retention', '7'),
            'SMB_ENABLED': 'true' if request.form.get('smb_enabled') else 'false',
            'SMB_SHARE': request.form.get('smb_share', ''),
            'SMB_MOUNT': request.form.get('smb_mount', '/mnt/backup'),
            'SMB_USER': request.form.get('smb_user', ''),
            'SMB_PASSWORD': request.form.get('smb_password', ''),
            'SMB_DOMAIN': request.form.get('smb_domain', 'WORKGROUP')
        }
        
        # Datenbank-Konfigurationen
        databases = []
        
        # Hole Datenbank-IDs aus den versteckten Feldern
        db_ids = request.form.getlist('db_ids')
        print(f"DEBUG - Datenbank-IDs aus versteckten Feldern: {db_ids}", flush=True)
        
        for db_id in db_ids:
            db_config = {
                'id': db_id,
                'name': request.form.get(f'db_{db_id}_name', f'Datenbank {db_id}'),
                'host': request.form.get(f'db_{db_id}_host', 'localhost'),
                'port': request.form.get(f'db_{db_id}_port', '3306'),
                'user': request.form.get(f'db_{db_id}_user', 'root'),
                'password': request.form.get(f'db_{db_id}_password', ''),
                'database': request.form.get(f'db_{db_id}_database', '')
            }
            print(f"DEBUG - DB-Konfiguration für ID {db_id}: {db_config}", flush=True)
            databases.append(db_config)
        
        print(f"DEBUG - Anzahl der Datenbanken: {len(databases)}", flush=True)
        
        # Wenn keine Datenbanken übermittelt wurden, füge eine Standard-Datenbank hinzu
        if not databases:
            print("DEBUG - Keine Datenbanken gefunden, füge Standard-Datenbank hinzu", flush=True)
            databases.append({
                'id': '1',
                'name': 'Datenbank 1',
                'host': 'localhost',
                'port': '3306',
                'user': 'root',
                'password': '',
                'database': ''
            })
        
        print("DEBUG - Speichere Konfiguration", flush=True)
        save_backup_config(config_data, databases)
        print("DEBUG - Konfiguration gespeichert", flush=True)
        flash('Konfiguration gespeichert', 'success')
        return redirect(url_for('config'))
    
    # Lade aktuelle Konfiguration
    config_data = load_backup_config()
    databases = load_database_configs()
    return render_template('config.html', config=config_data, databases=databases, version=APP_VERSION)

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
    return render_template('scheduler.html', config=scheduler_data, version=APP_VERSION)

@app.route('/backups')
def backups():
    backup_list = list_backups()
    databases = load_database_configs()
    # Erstelle ein Dictionary für schnellen Zugriff auf Datenbanknamen
    db_names = {db['id']: db['name'] for db in databases}
    return render_template('backups.html', backups=backup_list, databases=databases, db_names=db_names, version=APP_VERSION)

@app.route('/run_backup', methods=['POST'])
def trigger_backup():
    db_id = request.form.get('db_id', 'all')
    
    if db_id == 'all':
        # Backup aller Datenbanken
        databases = load_database_configs()
        all_success = True
        messages = []
        
        for db in databases:
            success, message = run_backup(db['id'])
            if not success:
                all_success = False
                messages.append(f"Fehler bei Datenbank {db['name']}: {message}")
        
        if all_success:
            flash('Alle Backups erfolgreich durchgeführt', 'success')
        else:
            for msg in messages:
                flash(msg, 'danger')
    else:
        # Backup einer einzelnen Datenbank
        success, message = run_backup(db_id)
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

@app.route('/test_db_connection', methods=['POST'])
def test_db_connection():
    if request.is_json:
        data = request.get_json()
        host = data.get('mysql_host', 'localhost')
        port = data.get('mysql_port', '3306')
        user = data.get('mysql_user', 'root')
        password = data.get('mysql_password', '')
        database = data.get('mysql_database', '')
    else:
        # Für die neue Struktur mit mehreren Datenbanken
        db_id = request.form.get('db_id', '1')
        databases = load_database_configs()
        db_config = next((db for db in databases if db['id'] == db_id), None)
        
        if db_config:
            host = db_config.get('host', 'localhost')
            port = db_config.get('port', '3306')
            user = db_config.get('user', 'root')
            password = db_config.get('password', '')
            database = db_config.get('database', '')
        else:
            # Fallback auf alte Konfiguration
            config = load_backup_config()
            host = config.get('MYSQL_HOST', 'localhost')
            port = config.get('MYSQL_PORT', '3306')
            user = config.get('MYSQL_USER', 'root')
            password = config.get('MYSQL_PASSWORD', '')
            database = config.get('MYSQL_DATABASE', '')
    
    try:
        import pymysql
        connection = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        connection.close()
        message = f'Datenbankverbindung zu {host}:{port}/{database} erfolgreich hergestellt.'
        
        if request.is_json:
            return jsonify({'success': True, 'message': message})
        else:
            flash(message, 'success')
            return redirect(url_for('config'))
    except Exception as e:
        error_message = f'Fehler bei der Datenbankverbindung: {str(e)}'
        
        if request.is_json:
            return jsonify({'success': False, 'message': error_message})
        else:
            flash(error_message, 'danger')
            return redirect(url_for('config'))

@app.route('/test_smb_connection', methods=['POST'])
def test_smb_connection():
    if request.is_json:
        data = request.get_json()
        smb_share = data.get('smb_share', '')
        smb_mount = data.get('smb_mount', '/mnt/backup')
        smb_user = data.get('smb_user', '')
        smb_password = data.get('smb_password', '')
        smb_domain = data.get('smb_domain', 'WORKGROUP')
    else:
        config = load_backup_config()
        smb_enabled = config.get('SMB_ENABLED', 'false') == 'true'
        smb_share = config.get('SMB_SHARE', '')
        smb_mount = config.get('SMB_MOUNT', '/mnt/backup')
        smb_user = config.get('SMB_USER', '')
        smb_password = config.get('SMB_PASSWORD', '')
        smb_domain = config.get('SMB_DOMAIN', 'WORKGROUP')
        
        if not smb_enabled:
            flash('SMB-Share ist nicht aktiviert.', 'warning')
            return redirect(url_for('config'))
    
    if not smb_share:
        message = 'SMB-Share-Pfad ist nicht angegeben.'
        if request.is_json:
            return jsonify({'success': False, 'message': message})
        else:
            flash(message, 'danger')
            return redirect(url_for('config'))
    
    # Erstelle Mount-Verzeichnis, falls es nicht existiert
    os.makedirs(smb_mount, exist_ok=True)
    
    # Prüfe, ob der SMB-Server erreichbar ist
    server = smb_share.split('/')[2]
    warnings = []
    
    try:
        import subprocess
        ping_result = subprocess.run(['ping', '-c', '1', server], capture_output=True, text=True)
        if ping_result.returncode != 0:
            warning_msg = f'WARNUNG: SMB-Server {server} scheint nicht erreichbar zu sein. Ping fehlgeschlagen.'
            warnings.append(warning_msg)
            if not request.is_json:
                flash(warning_msg, 'warning')
    except Exception as e:
        logger.error(f"Fehler beim Ping des SMB-Servers: {e}")
    
    # Versuche, den SMB-Share zu mounten
    try:
        mount_cmd = []
        if smb_password:
            mount_cmd = ['mount', '-t', 'cifs', smb_share, smb_mount, 
                        '-o', f'username={smb_user},password={smb_password},domain={smb_domain},vers=3.0']
        else:
            mount_cmd = ['mount', '-t', 'cifs', smb_share, smb_mount, 
                        '-o', f'username={smb_user},domain={smb_domain},vers=3.0']
        
        mount_result = subprocess.run(mount_cmd, capture_output=True, text=True)
        
        if mount_result.returncode == 0:
            # Versuche, ein Testverzeichnis zu erstellen
            test_dir = os.path.join(smb_mount, 'test_connection')
            os.makedirs(test_dir, exist_ok=True)
            os.rmdir(test_dir)
            
            # Unmounte den Share
            subprocess.run(['umount', smb_mount], check=True)
            
            success_msg = f'SMB-Verbindung zu {smb_share} erfolgreich hergestellt.'
            
            if request.is_json:
                return jsonify({
                    'success': True, 
                    'message': success_msg,
                    'warnings': warnings
                })
            else:
                flash(success_msg, 'success')
                return redirect(url_for('config'))
        else:
            error_msg = mount_result.stderr.strip()
            warning_msg = 'Prüfen Sie Benutzername, Passwort, Domain und Share-Pfad.'
            
            if request.is_json:
                return jsonify({
                    'success': False, 
                    'message': f'Fehler beim Mounten des SMB-Shares: {error_msg}',
                    'warnings': warnings + [warning_msg]
                })
            else:
                flash(f'Fehler beim Mounten des SMB-Shares: {error_msg}', 'danger')
                flash(warning_msg, 'warning')
                return redirect(url_for('config'))
    except Exception as e:
        error_msg = f'Fehler bei der SMB-Verbindung: {str(e)}'
        
        # Versuche, den Share zu unmounten, falls er gemountet wurde
        try:
            subprocess.run(['umount', smb_mount], capture_output=True)
        except:
            pass
        
        if request.is_json:
            return jsonify({
                'success': False, 
                'message': error_msg,
                'warnings': warnings
            })
        else:
            flash(error_msg, 'danger')
            return redirect(url_for('config'))

# API-Route zum Hinzufügen einer neuen Datenbank
@app.route('/add_database', methods=['POST'])
def add_database():
    # Lade aktuelle Datenbanken
    databases = load_database_configs()
    
    # Finde die nächste freie ID
    used_ids = [int(db['id']) for db in databases]
    next_id = 1
    while next_id in used_ids:
        next_id += 1
    
    # Lade aktuelle Konfiguration
    config = load_backup_config()
    
    # Füge neue Datenbank hinzu
    new_db = {
        'id': str(next_id),
        'name': f'Datenbank {next_id}',
        'host': 'localhost',
        'port': '3306',
        'user': 'root',
        'password': '',
        'database': ''
    }
    databases.append(new_db)
    
    # Speichere Konfiguration
    save_backup_config(config, databases)
    
    flash(f'Neue Datenbank hinzugefügt: Datenbank {next_id}', 'success')
    return redirect(url_for('config'))

# API-Route zum Löschen einer Datenbank
@app.route('/delete_database/<db_id>', methods=['POST'])
def delete_database(db_id):
    # Lade aktuelle Datenbanken
    databases = load_database_configs()
    
    # Finde die zu löschende Datenbank
    db_to_delete = next((db for db in databases if db['id'] == db_id), None)
    
    if db_to_delete:
        # Entferne die Datenbank aus der Liste
        databases = [db for db in databases if db['id'] != db_id]
        
        # Wenn keine Datenbanken mehr übrig sind, füge eine Standard-Datenbank hinzu
        if not databases:
            databases.append({
                'id': '1',
                'name': 'Datenbank 1',
                'host': 'localhost',
                'port': '3306',
                'user': 'root',
                'password': '',
                'database': ''
            })
        
        # Lade aktuelle Konfiguration
        config = load_backup_config()
        
        # Speichere Konfiguration
        save_backup_config(config, databases)
        
        flash(f'Datenbank {db_to_delete["name"]} wurde gelöscht', 'success')
    else:
        flash(f'Datenbank mit ID {db_id} nicht gefunden', 'danger')
    
    return redirect(url_for('config'))

# Stelle sicher, dass die Konfigurationsdateien existieren
ensure_config_files()

# Kontext-Prozessor, um die Version in allen Templates verfügbar zu machen
@app.context_processor
def inject_version():
    return dict(version=APP_VERSION)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False)
