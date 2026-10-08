# Hollister-Verfügbarkeitsmonitor

Docker-Anwendung für Synology mit Telegram-Benachrichtigungen.

## Geplantes Verhalten
- Artikel über Produktlink, Größe und Farbe konfigurieren; deutscher Shop.
- Standardmäßig alle 15 Minuten prüfen; Intervall konfigurierbar.
- Nur bestätigte Verfügbarkeit der exakten Variante melden, mit Kauflink.
- Auch beim ersten erfolgreichen Check melden, falls bereits verfügbar.
- Keine Wiederholung solange derselbe verfügbare Zustand anhält.
- Zustand dauerhaft im Docker-Volume speichern.
- Netzwerkfehler, fehlende Artikel und nicht auswertbare Antworten als unbekannt behandeln; niemals als Verfügbarkeit.
- Fehlgeschlagene Telegram-Zustellung erneut versuchen; erst nach erfolgreicher Zustellung als gemeldet speichern.
- Zugangsdaten über lokale .env-Datei setzen und aus Logs ausschließen.
- Docker Compose, Neustartregel und Anleitung für Synology bereitstellen.

## Noch erforderlich
Produktlink sowie Größe und Farbe, um Datenquelle und Erkennung anhand realer Shopantworten zu implementieren und zu prüfen. Telegram-Bot-Token und Chat-ID werden erst bei Einrichtung auf Synology benötigt.

## Aktueller Stand
Konfigurationsvorlage und Umsetzungsspezifikation angelegt. Noch keine laufende Überwachung, keine implementierte Shopabfrage und keine versendeten Benachrichtigungen.
