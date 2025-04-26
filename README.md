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

#### Wichtig: MySQL 8.0 Kompatibilität

Wenn Sie MySQL 8.0 oder höher verwenden, müssen Sie den Benutzer so konfigurieren, dass er das ältere Authentifizierungsplugin `mysql_native_password` verwendet. MySQL 8.0 verwendet standardmäßig das Plugin `caching_sha2_password`, das mit dem im Container verwendeten MariaDB-Client nicht kompatibel ist.

Führen Sie den folgenden SQL-Befehl auf Ihrem MySQL-Server aus, um den Benutzer zu konfigurieren (ersetzen Sie 'username' und 'password' durch Ihre Werte):

```sql
ALTER USER 'username'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
```

Beispiel für den Root-Benutzer:

```sql
ALTER USER 'root'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
```

Danach müssen Sie die Berechtigungen neu laden:

```sql
FLUSH PRIVILEGES;
```

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

## Fehlerbehebung

### Leere Backups (0 Bytes)

Wenn Ihre Backups leer sind (0 Bytes oder 0.0 MB in der Weboberfläche), liegt das wahrscheinlich an einem Authentifizierungsproblem mit MySQL 8.0. MySQL 8.0 verwendet standardmäßig das Authentifizierungsplugin `caching_sha2_password`, das mit dem im Container verwendeten MariaDB-Client nicht kompatibel ist.

**Lösung:**

1. Ändern Sie den MySQL-Benutzer, um das ältere Authentifizierungsplugin `mysql_native_password` zu verwenden:

   ```sql
   ALTER USER 'username'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
   FLUSH PRIVILEGES;
   ```

2. Starten Sie ein neues Backup über die Weboberfläche.

3. Überprüfen Sie, ob das Backup jetzt Daten enthält. Die Weboberfläche zeigt möglicherweise immer noch 0.0 MB an, aber die tatsächliche Dateigröße sollte größer sein.

### Verbindungsprobleme zum MySQL-Server

Wenn Sie Probleme haben, eine Verbindung zum MySQL-Server herzustellen:

1. Stellen Sie sicher, dass der MySQL-Server läuft und von außen erreichbar ist.
2. Überprüfen Sie, ob der Benutzer die richtigen Berechtigungen hat.
3. Stellen Sie sicher, dass der Benutzer von der IP-Adresse des Containers aus zugreifen darf.
4. Überprüfen Sie die Firewall-Einstellungen.

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz.

## Copyright

&copy; 2025 Maik Bohrmann | [GitHub Repository](https://github.com/meddatzk/mysql-backup)
