
# Tennis Ranking List Webapplikation

## Einleitung

Die Webapplikation „Tennis Ranking List“ dient der Verwaltung von Tennis-Spielern und der Organisation von Herausforderungen (Challenges) zwischen diesen Spielern. Neben der Darstellung der aktuellen Rangliste bietet die Anwendung Funktionen zur dynamischen Aktualisierung der Rangpositionen sowie zur Verwaltung von Spielerblockierungen und -verfügbarkeiten.

## Ziel des Projekts

### Spielerverwaltung:
Ermöglichen des Hinzufügens, Bearbeitens und Löschens von Spielern.
### Challenge-Management: Erstellen, Verwalten und Auswerten von Herausforderungen zwischen Spielern.
### Dynamisches Ranking: Automatisches Aktualisieren der Rangliste basierend auf den Spielergebnissen.
### Echtzeit-Updates: Übertragung von Änderungen in Echtzeit an alle verbundenen Clients mittels Socket.IO.

## Technologie-Stack
### Backend: Python mit dem Flask-Framework (siehe Flask-Dokumentation)
### Datenbank: SQLite, initialisiert über ein SQL-Schema (schema.sql)
### Echtzeit-Kommunikation: Flask-SocketIO (Flask-SocketIO Dokumentation)
### Frontend: HTML, CSS, JavaScript (jQuery, Bootstrap – Bootstrap Website)
### Weitere Komponenten: JSON-Daten für die Initialisierung der Spieler (initial_players.json)

## Architektur & Struktur
Die Applikation ist modular aufgebaut und umfasst folgende zentrale Dateien:

### app.py: Enthält den Flask-Server, die Routing-Logik, Datenbankoperationen und die Echtzeitkommunikation.
## HTML-Templates:
### admin.html: Admin-Oberfläche zur Verwaltung der aktiven Herausforderungen.
### index.html: Hauptseite mit der dynamischen Rangliste (Pyramidenansicht) und Formularen zur Challenge-Erstellung.
### db_settings.html: Seite zur Verwaltung der Spieler-Datenbankeinstellungen.
## Daten:
### initial_players.json: Initiale Spieler-Daten, die beim erstmaligen Aufbau der Datenbank geladen werden.
### schema.sql: SQL-Skript zur Erstellung der notwendigen Tabellen (z. B. players und challenges).

## Hauptfunktionen

## Spielerverwaltung:
Spieler können hinzugefügt, bearbeitet oder gelöscht werden.
Validierungen verhindern z. B. doppelte Rangzuweisungen.
Challenge-Erstellung:
Auswahl von „Challenger“ und „Opponent“ über dynamische Dropdown-Menüs.
Herausforderungen werden in der Datenbank gespeichert und erhalten ein
festes Zeitlimit.
Ranking-Update:
Bei der Auswertung einer Challenge wird das Ranking der Spieler dynamisch angepasst.
Blockierungen werden zeitlich gesteuert, um erneute Herausfordungen zu limitieren.
Echtzeit-Updates:
Mithilfe von Socket.IO werden Änderungen (z. B. neue Challenges, Aktualisierungen im Ranking) in Echtzeit an alle Clients übertragen.

## API Endpoints & Routen

Wichtige Endpunkte der Applikation sind:

### / und /stecher_start: Startseiten und Umleitung.
### /index: Anzeige der aktuellen Rangliste inklusive Challenge-Status.
### /admin: Administrationsoberfläche zur Auswertung und Verwaltung der Challenges.
### /get_players: Rückgabe aller Spielerinformationen als JSON.
### /eligible_opponents: Bestimmung der möglichen Gegner für einen gewählten Challenger.
### /challenge: Erstellung einer neuen Challenge zwischen zwei Spielern.
### /toggle_availability: Umschalten der Verfügbarkeit eines Spielers.
### /submit_result: Auswertung einer Challenge und Aktualisierung der Rangliste.
### /newplayer_challenge: Hinzufügen eines neuen Spielers und gleichzeitige Erstellung einer Challenge.
### /update_player, /delete_player, /add_player: CRUD-Operationen zur Spielerverwaltung.
### /db_settings: Verwaltung der Datenbankeinstellungen.

## Datenbankstruktur

Die Datenbank besteht aus mindestens zwei Tabellen:

### players:
Enthält Informationen wie ID, Name, Rang, Verfügbarkeit, Blockierungszeiträume und ob es sich um einen neuen Spieler handelt.
### challenges:
Speichert die Daten zu den Challenges, inklusive der IDs der beteiligten Spieler,
Zeitstempel, Deadlines und dem Ergebnis der Challenge.
Das SQL-Schema zur Initialisierung der Datenbank ist in der Datei schema.sql hinterlegt
und wird in app.py verwendet.

## Benutzeroberfläche & Templates

## Admin Panel (admin.html):
Ermöglicht das Verwalten offener Challenges und das Übermitteln der Ergebnisse.
## Hauptseite (index.html):
Zeigt die Spieler in einer Pyramidenstruktur an, ermöglicht die Auswahl von Challengern und Gegnern sowie die Anzeige von Statusinformationen (z. B. Blockierung, In-Challenge).
## DB Settings (db_settings.html):
Bietet eine Oberfläche zur Verwaltung der Spieler-Datenbank mit Funktionen zum Hinzufügen, Bearbeiten und Löschen von Spielern.

## Besonderheiten & Erweiterungen

### Echtzeit-Interaktion:
Durch den Einsatz von Socket.IO werden alle Clients automatisch über Änderungen informiert, was für ein dynamisches Nutzererlebnis sorgt.
### Flexible Challenge-Logik:
Je nach Rang des Spielers werden unterschiedliche Regeln für die Auswahl möglicher Gegner angewandt.
### Automatische Ranking-Aktualisierung:
Nach Abschluss einer Challenge wird die Rangliste neu berechnet und eventuelle Blockierungen zeitlich gesteuert.
## Sicherheit und Verbesserungsmöglichkeiten

### Sicherheit:
Aktuell wird ein fest kodierter Secret Key ("your-secret-key") verwendet.
In einer Produktionsumgebung muss dieser durch einen sicheren, umgebungsbasierten Schlüssel ersetzt werden.
### Erweiterungen:
Weitere Sicherheitsprüfungen, detailliertere Fehlerbehandlungen sowie zusätzliche Funktionen (z. B. detailliertere Statistiken, Benutzerrollen) könnten in zukünftigen
Versionen implementiert werden.

## Fazit

Die Applikation bietet eine umfassende Lösung zur Verwaltung von Tennis-Spielern und Herausforderungen. Durch die Integration von Echtzeit-Updates, dynamischen UI-Komponenten
und einer automatisierten Ranking-Berechnung entsteht ein modernes und benutzerfreundliches System, das sowohl im administrativen als auch im spielerischen Bereich überzeugt.

## Quellen und weiterführende Informationen:
Flask-Dokumentation: https://flask.palletsprojects.com/en/2.2.x/
Flask-SocketIO: https://flask-socketio.readthedocs.io/
Bootstrap: https://getbootstrap.com/
