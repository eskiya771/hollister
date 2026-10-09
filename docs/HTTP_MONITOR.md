# Automatischer HTTP-Monitor

`http_monitor.py` prüft sofort nach dem Start und anschließend alle 60 Sekunden:

| Oberteil | Farbe | Größen |
|---|---|---|
| Henley 63757420 | Helles Pink | XS, S |
| Camisole 63270319 | Weiß | XS, S, XXL |

Pro Zyklus erfolgen zwei GraphQL-POST-Anfragen ohne Browser, Cookies oder Anmeldung. Eine Telegram-Nachricht enthält alle fünf Ergebnisse. Bestätigte Farbprodukt-, Collection- und SKU-IDs stehen in `http_stock.py`. Die alten Browser-SKU-Einstellungen in `.env` werden von diesem Einstiegspunkt nicht verwendet. Andere Produkte müssen ausdrücklich in der Zuordnung ergänzt und geprüft werden.

Nur eine eindeutige, passende SKU mit ganzzahligem Bestand > 0 und `Available` gilt als verfügbar. Bestand 0 und `Unavailable` bedeutet ausverkauft. Fehler, fehlende/mehrdeutige Varianten, widersprüchliche Daten, Schutzseiten und GraphQL-Fehler bedeuten nicht prüfbar. Ein gemeldetes HTTP-Cache-Alter über 900 Sekunden wird abgelehnt; fehlendes `Age` ist kein Beleg für ungecachte Daten. Die API ist intern und kann sich ändern. Bei Fehlern erfolgt die nächste Prüfung zum regulären Intervall; es gibt keine schnellen Wiederholungsschleifen.

## Lokal oder auf einem neuen System

Vorprüfung ohne Telegram: `python http_monitor.py --check-only`.

Ein Zyklus mit Telegram: `python http_monitor.py --once`.

Dauerbetrieb: `docker compose -f compose.http.yaml up -d --build`. `.env` enthält Telegram-Zugangsdaten, optional `CHECK_INTERVAL_SECONDS`, `HTTP_MAX_CACHE_AGE_SECONDS` (0 bis 900), `TZ`. Nicht zusätzlich den Browser-Monitor starten: sonst entstehen doppelte Nachrichten.

## Synology-Umstellung

`deploy-http-nas.sh` baut das schlanke HTTP-Image und prüft zuerst beide Produkte ohne Telegram. Bei der ersten Umstellung stoppt es danach `hollister-session-monitor-1` und startet `hollister-http-monitor`. Bei weiteren Updates wird der bisherige HTTP-Container gestoppt und mit Zeitstempel als Rückfall umbenannt. Die bestehende `.env` wird nur als Container-Umgebung verwendet; sie wird nicht in das Image kopiert. Scheitert die erste Telegram-Bestätigung, wird automatisch der bisherige Monitor wieder gestartet. Das Browser-Image, sein Container und Profil bleiben erhalten. Logs: `/volume1/docker/hollister/http-release/deployment.log` und `first-cycle.log`.

Betriebsnachweis: Am 09.10.2026 um 13:51 Uhr wurde der neue Container mit `Intervall=60s` gestartet. Telegram bestätigte die erste Zusammenfassung mit fünf Varianten als Nachricht 212. Jede Größe steht in einer eigenen Zeile mit bestätigtem Bestand und SKU; unbekannter Bestand wird ausdrücklich als unbekannt angezeigt.

Rückwechsel als root: zuerst `/usr/local/bin/docker stop hollister-http-monitor`, danach `/usr/local/bin/docker start hollister-session-monitor-1`. Ein Rückwechsel verändert weder Profil noch alte Konfiguration.
