## [1.1.1](https://github.com/meddatzk/mysql-backup/compare/v1.1.0...v1.1.1) (2025-04-26)


### Bug Fixes

* behebe das Kopieren der version.json-Datei in das Docker-Image ([e5a2c5c](https://github.com/meddatzk/mysql-backup/commit/e5a2c5cb6cdad956c3f2f01bd83715046c4b4f9f))
* verbessere die Versionserkennung durch Unterstützung relativer Pfade im Docker-Setup ([59e69e2](https://github.com/meddatzk/mysql-backup/commit/59e69e2ec72abf6f13c07888dfdd82812494a16a))

# [1.1.0](https://github.com/meddatzk/mysql-backup/compare/v1.0.0...v1.1.0) (2025-04-26)


### Bug Fixes

* Aktualisiere die Verarbeitung von Datenbank-IDs in Formularen und füge versteckte Felder hinzu ([a0f00e3](https://github.com/meddatzk/mysql-backup/commit/a0f00e366f635bb9442927def24c9f2d73926ee5))
* Ermögliche die Verarbeitung mehrerer Datenbank-IDs über ein verstecktes Feld ([65d2f01](https://github.com/meddatzk/mysql-backup/commit/65d2f01f66b69fd621576b0f4a23f9b6ccfb5b90))
* Extrahiere Datenbank-IDs aus Formularfeldern und entferne das versteckte Feld ([adb127a](https://github.com/meddatzk/mysql-backup/commit/adb127a30943c52d17f2695cdcbf595557fcc1d9))
* Korrigiere die Verarbeitung von Datenbank-IDs in Formularen ([09e6fc7](https://github.com/meddatzk/mysql-backup/commit/09e6fc7a7c17fea5d4faa0ceda188f00e31db67c))
* Korrigiere die Verarbeitung von Datenbank-IDs in versteckten Feldern ([39e2270](https://github.com/meddatzk/mysql-backup/commit/39e227032b6bc5a99b16c2770ece7ab8699e194c))
* Verhindere Validierungsfehler durch temporäres Entfernen von "required" in nicht-aktiven Tabs vor dem Formularabsenden ([0cd2b7e](https://github.com/meddatzk/mysql-backup/commit/0cd2b7e319412a3e1aeed62792701ed7eabedee1))


### Features

* Aktualisiere die Verarbeitung von Datenbank-IDs und verbessere das Formular-Handling ([435e47f](https://github.com/meddatzk/mysql-backup/commit/435e47f7d4447129ea36c21bc6a9ac1177172b5c))
* Enhance MySQL Backup Functionality and Configuration ([d2e9927](https://github.com/meddatzk/mysql-backup/commit/d2e99275d305a654d01760df3641768224f0fc92))
* Ersetze das Löschen von Datenbanken durch einen Button und füge ein verstecktes Formular hinzu ([a6a028d](https://github.com/meddatzk/mysql-backup/commit/a6a028dd3630475a2ebebfc9597b3d9b7357b4b9))
* Füge Debugging-Ausgaben für Formularfelder hinzu und stelle sicher, dass alle Felder übermittelt werden ([6263db5](https://github.com/meddatzk/mysql-backup/commit/6263db50b2758d93a3db2376ce2f8d4e6f5edd6b))
* Füge Debugging-Ausgaben hinzu, um alle Formularfelder zu protokollieren ([47f4ca8](https://github.com/meddatzk/mysql-backup/commit/47f4ca83b25a183bbb68cc9abf4366c9446c6ccd))
* Füge Debugging-Logs hinzu, um die Übermittlung von DB-IDs und Formularfeldern zu überprüfen ([0bb5dc5](https://github.com/meddatzk/mysql-backup/commit/0bb5dc56164f6ede74faf01f80ad7445743854c2))
* Verbessere die Verarbeitung von Datenbank-IDs und füge umfassende Logging-Informationen hinzu ([c54f433](https://github.com/meddatzk/mysql-backup/commit/c54f433ec0c0a45ba552dff86af53bd9a5c0c388))

# 1.0.0 (2025-04-05)


### Bug Fixes

* Aktualisiere supervisord-Konfiguration für Webanwendung und Scheduler, um Log-Ausgaben an stdout zu senden ([aa92761](https://github.com/meddatzk/mysql-backup/commit/aa9276174a625a42b99338f8fc29438975370ca3))
* Setze Flask- und Flask-WTF-Versionen auf vorherige stabile Versionen zurück ([c3351d0](https://github.com/meddatzk/mysql-backup/commit/c3351d0b3888cc622f5c321e72e3fc55ed1840ff))
* Verlagere die Erstellung von Verzeichnissen im Dockerfile und passe Berechtigungen an ([4799aef](https://github.com/meddatzk/mysql-backup/commit/4799aef686d13f54aa58ee89da727052df7cba04))


### Features

* Füge Funktionen zum Löschen und Herunterladen von Backups hinzu ([ccceb83](https://github.com/meddatzk/mysql-backup/commit/ccceb83510f66f46c90156c25866787350c5d41d))
* Füge Funktionen zum Testen der Datenbank- und SMB-Verbindungen hinzu ([3e4d41b](https://github.com/meddatzk/mysql-backup/commit/3e4d41bcb863ac1819c118a55cc5fa1e7ce3ca8a))
* Füge Sicherheitsoptionen und Berechtigungen für SMB-Mounts in der Docker-Compose-Datei hinzu ([ee7bda0](https://github.com/meddatzk/mysql-backup/commit/ee7bda012eb419fed06a61131ecb1322c46199f5))
* Füge Versionsinformation zur Anwendung hinzu und aktualisiere das Template ([afaa441](https://github.com/meddatzk/mysql-backup/commit/afaa441b31451f3fc04064a6d5255cdc2c65b653))
* Implementiere AJAX-Tests für Datenbank- und SMB-Verbindungen in der Konfiguration ([919568e](https://github.com/meddatzk/mysql-backup/commit/919568efe28789569c69ccf9dff185d1fcdfe5f8))
* Implementiere Semantic Versioning mit GitHub Actions und aktualisiere die Konfigurationsdateien ([adcda71](https://github.com/meddatzk/mysql-backup/commit/adcda71e93f730e4ed1fd2d9d74c626c036e8c30))
