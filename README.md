# MySQL Backup Manager

Ein Docker-Container zur einfachen Sicherung von MySQL-Datenbanken mit Weboberfläche.

## Features

- **Webbasierte Konfiguration** der MySQL-Verbindung und Backup-Einstellungen
- **Backup auf SMB-Shares** möglich für externe Speicherung
- **Flexible Zeitplanung** für automatische Backups (stündlich, täglich, wöchentlich, monatlich)
- **Konfigurierbare Aufbewahrungsdauer** für Backups
- **Manuelle Backups** über die Weboberfläche
- **Übersicht aller Backups** mit Informationen zu Größe und Datum

## Installation

### Voraussetzungen

- Docker und Docker Compose
- Zugriff auf einen MySQL-Server

### Installation mit Docker Compose

1. Repository klonen oder Dateien herunterladen
2. Optional: Passen Sie die Einstellungen in der `.env`-Datei an (z.B. den Port der Weboberfläche)
3. Docker-Container bauen und starten:

```bash
docker-compose up -d
```

4. Öffnen Sie die Weboberfläche unter http://localhost:8080 (oder dem in der `.env`-Datei konfigurierten Port)

## Konfiguration

### MySQL-Verbindung

Konfigurieren Sie die Verbindung zu Ihrer MySQL-Datenbank über die Weboberfläche:

- **Host**: Hostname oder IP-Adresse des MySQL-Servers
- **Port**: Port des MySQL-Servers (Standard: 3306)
- **Benutzer**: Benutzername für die MySQL-Verbindung
- **Passwort**: Passwort für die MySQL-Verbindung
- **Datenbank**: Name der zu sichernden Datenbank

### Backup-Einstellungen

- **Backup-Verzeichnis**: Verzeichnis, in dem die Backups gespeichert werden
- **Aufbewahrungsdauer**: Anzahl der Tage, die Backups aufbewahrt werden (0 = unbegrenzt)

### SMB-Share-Einstellungen

Für die Sicherung auf einen Netzwerk-Share:

- **SMB-Share aktivieren**: Aktiviert die Sicherung auf einen SMB-Share
- **SMB-Share**: Pfad zum SMB-Share (z.B. //server/share)
- **Mount-Punkt**: Lokaler Mount-Punkt für den SMB-Share
- **SMB-Benutzer**: Benutzername für den SMB-Share
- **SMB-Passwort**: Passwort für den SMB-Share
- **SMB-Domain**: Domain für den SMB-Share (Standard: WORKGROUP)

### Backup-Zeitplan

Konfigurieren Sie, wann automatische Backups ausgeführt werden sollen:

- **Automatische Backups aktivieren**: Aktiviert den Backup-Zeitplan
- **Backup-Häufigkeit**: Stündlich, täglich, wöchentlich oder monatlich
- **Uhrzeit**: Zu welcher Uhrzeit sollen die Backups erstellt werden
- **Wochentag**: An welchem Wochentag sollen die Backups erstellt werden (bei wöchentlichen Backups)
- **Tag des Monats**: An welchem Tag des Monats sollen die Backups erstellt werden (bei monatlichen Backups)

## Manuelles Backup

Sie können jederzeit ein manuelles Backup über die Weboberfläche starten:

1. Gehen Sie zur "Backups"-Seite
2. Klicken Sie auf "Backup jetzt starten"

## Backup-Format

Die Backups werden im SQL-Format erstellt und mit gzip komprimiert. Der Dateiname enthält den Namen der Datenbank und einen Zeitstempel:

```
mysql_backup_[Datenbankname]_[Zeitstempel].sql.gz
```

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz.
