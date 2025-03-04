# Tennis Ranking List Webapplikation

## Einleitung

Die Webapplikation **Tennis Ranking List** dient der Verwaltung von Tennis-Spielern und der Organisation von Herausforderungen (Challenges) zwischen diesen. Neben der Darstellung der aktuellen Rangliste bietet die Anwendung Funktionen zur dynamischen Aktualisierung der Rangpositionen sowie zur Verwaltung von Spielerblockierungen und -verfügbarkeiten.

---

## Ziel des Projekts

- **Spielerverwaltung:**  
  Hinzufügen, Bearbeiten und Löschen von Spielern.

- **Challenge-Management:**  
  Erstellen, Verwalten und Auswerten von Herausforderungen zwischen Spielern.

- **Dynamisches Ranking:**  
  Automatische Aktualisierung der Rangliste basierend auf Spielergebnissen.

- **Echtzeit-Updates:**  
  Übertragung von Änderungen in Echtzeit an alle verbundenen Clients mittels Socket.IO.

---

## Technologie-Stack

- **Backend:**  
  Python mit dem Flask-Framework ([Flask-Dokumentation](https://flask.palletsprojects.com/en/2.2.x/))

- **Datenbank:**  
  SQLite, initialisiert über ein SQL-Schema ([schema.sql](schema.sql))

- **Echtzeit-Kommunikation:**  
  Flask-SocketIO ([Flask-SocketIO Dokumentation](https://flask-socketio.readthedocs.io/))

- **Frontend:**  
  HTML, CSS, JavaScript (jQuery, [Bootstrap](https://getbootstrap.com/))

- **Weitere Komponenten:**  
  JSON-Daten zur Initialisierung der Spieler ([initial_players.json](initial_players.json))

---

## Architektur & Struktur

Die Applikation ist modular aufgebaut und umfasst folgende zentrale Dateien:

- **app.py:**  
  Enthält den Flask-Server, die Routing-Logik, Datenbankoperationen und die Echtzeitkommunikation.

- **HTML-Templates:**  
  - **admin.html:**  
    Administrationsoberfläche zur Verwaltung offener Challenges.
  - **index.html:**  
    Hauptseite mit dynamischer Rangliste (Pyramidenansicht) und Challenge-Formularen.
  - **db_settings.html:**  
    Seite zur Verwaltung der Spieler-Datenbankeinstellungen.

- **Daten:**  
  - **initial_players.json:**  
    Initiale Spieler-Daten, die beim ersten Aufbau der Datenbank geladen werden.
  - **schema.sql:**  
    SQL-Skript zur Erstellung der notwendigen Tabellen (z. B. *players* und *challenges*).

---

## Hauptfunktionen

### Spielerverwaltung

- Spieler können hinzugefügt, bearbeitet oder gelöscht werden.
- Validierungen verhindern beispielsweise doppelte Rangzuweisungen.

### Challenge-Erstellung & -Auswertung

- Dynamische Dropdown-Menüs ermöglichen die Auswahl von „Challenger“ und „Opponent“.
- Herausforderungen werden in der Datenbank gespeichert und erhalten ein festes Zeitlimit.
- Nach Auswertung einer Challenge wird das Ranking dynamisch angepasst; Blockierungen werden zeitlich gesteuert.

### Echtzeit-Updates

- Mit Socket.IO werden Änderungen wie neue Challenges oder Ranking-Aktualisierungen in Echtzeit an alle Clients übertragen.

---

## API Endpoints & Routen

- **/** und **/stecher_start:**  
  Startseiten und Umleitungen.

- **/index:**  
  Anzeige der aktuellen Rangliste inklusive Challenge-Status.

- **/admin:**  
  Administrationsoberfläche zur Auswertung und Verwaltung der Challenges.

- **/get_players:**  
  Gibt alle Spielerinformationen als JSON zurück.

- **/eligible_opponents:**  
  Bestimmt mögliche Gegner für einen gewählten Challenger.

- **/challenge:**  
  Erstellt eine neue Challenge zwischen zwei Spielern.

- **/toggle_availability:**  
  Schaltet die Verfügbarkeit eines Spielers um.

- **/submit_result:**  
  Wertet eine Challenge aus und aktualisiert das Ranking.

- **/newplayer_challenge:**  
  Fügt einen neuen Spieler hinzu und erstellt gleichzeitig eine Challenge.

- **/update_player, /delete_player, /add_player:**  
  CRUD-Operationen zur Spielerverwaltung.

- **/db_settings:**  
  Verwaltung der Datenbankeinstellungen.

---

## Datenbankstruktur

Die Datenbank umfasst mindestens zwei Tabellen:

- **players:**  
  Enthält Informationen wie ID, Name, Rang, Verfügbarkeit, Blockierungszeiträume und Kennzeichnung als neuer Spieler.

- **challenges:**  
  Speichert Challenge-Daten, einschließlich der beteiligten Spieler-IDs, Zeitstempel, Deadlines und Ergebnisse.  
  Das SQL-Schema ([schema.sql](schema.sql)) wird in *app.py* zur Initialisierung verwendet.

---

## Benutzeroberfläche & Templates

- **Admin Panel (admin.html):**  
  Verwaltung offener Challenges und Übermittlung der Ergebnisse.

- **Hauptseite (index.html):**  
  Darstellung der Spieler in einer Pyramidenstruktur, Auswahl von Challengern und Gegnern sowie Anzeige von Statusinformationen (z. B. Blockierung, In-Challenge).

- **DB Settings (db_settings.html):**  
  Oberfläche zur Verwaltung der Spieler-Datenbank (Hinzufügen, Bearbeiten, Löschen).

---

## Besonderheiten & Erweiterungen

- **Echtzeit-Interaktion:**  
  Alle Clients werden automatisch über Änderungen informiert, was für ein dynamisches Nutzererlebnis sorgt.

- **Flexible Challenge-Logik:**  
  Unterschiedliche Regeln für die Gegnerauswahl je nach Spieler-Rang.

- **Automatische Ranking-Aktualisierung:**  
  Nach Challenge-Abschluss wird die Rangliste neu berechnet und Blockierungen werden zeitlich gesteuert.

---

## Sicherheit und Verbesserungsmöglichkeiten

- **Sicherheit:**  
  Derzeit wird ein fest kodierter Secret Key ("your-secret-key") verwendet. In einer Produktionsumgebung sollte dieser durch einen sicheren, umgebungsbasierten Schlüssel ersetzt werden.

- **Erweiterungen:**  
  Zusätzliche Sicherheitsprüfungen, detailliertere Fehlerbehandlungen und weitere Funktionen (z. B. Statistiken, Benutzerrollen) könnten in zukünftigen Versionen implementiert werden.

---

## Fazit

Die Applikation bietet eine umfassende Lösung zur Verwaltung von Tennis-Spielern und deren Herausforderungen. Durch die Integration von Echtzeit-Updates, dynamischen UI-Komponenten und automatisierter Ranking-Berechnung entsteht ein modernes und benutzerfreundliches System, das sowohl im administrativen als auch im spielerischen Bereich überzeugt.

---

## Quellen und weiterführende Informationen

- **Flask-Dokumentation:** [https://flask.palletsprojects.com/en/2.2.x/](https://flask.palletsprojects.com/en/2.2.x/)
- **Flask-SocketIO:** [https://flask-socketio.readthedocs.io/](https://flask-socketio.readthedocs.io/)
- **Bootstrap:** [https://getbootstrap.com/](https://getbootstrap.com/)

---

## NGINX – Socket.IO Settings

Die folgende Konfiguration (aus */etc/nginx/sites-available/stechertennis*) zeigt, wie NGINX so konfiguriert wird, dass WebSocket-Verbindungen an die Flask-App weitergeleitet werden:

```nginx
server {
    listen 443 ssl http2;
    server_name stechertennis.duckdns.org;

    # Dedicated location for WebSocket /socket.io endpoints
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Regular HTTP proxy for other routes
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    ssl_certificate /etc/letsencrypt/live/stechertennis.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stechertennis.duckdns.org/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()";

    # HSTS (optional)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Logging
    access_log /var/log/nginx/stechertennis.access.log;
    error_log /var/log/nginx/stechertennis.error.log warn;
}

