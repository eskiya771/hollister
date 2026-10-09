# Synology-Pr?fprotokoll, 08.10.2026

Ziel: `/volume1/docker/hollister`, Projekt `hollister`, Dienst `hollister`.

| Pr?fung | Ergebnis |
| --- | --- |
| SSH | Zugang als mevi best?tigt; Docker-Ausf?hrung einmalig durch Benutzer mit sudo |
| Plattform | Linux x86_64, Docker 24.0.2, Compose 2.20.1 |
| Compose | config --quiet erfolgreich |
| Image | Build erfolgreich, sha256:8de9bcad6554301bb9968b385a2ab591b7db92d7ea558da06746f44cdcf9cfb2 |
| Container-Benutzer | UID 10001 |
| Schreibrechte | /data, /data/browser-profile, /tmp, /data/cache, /data/config best?tigt |
| Chromium | Echter Start im Container erfolgreich |
| Telegram-Test | 23:04:05 Uhr Europe/Berlin, message_id 10 best?tigt |
| Erste Bestandsabfrage | 23:04:12 Uhr: Schutzseite/CAPTCHA, Status unknown |
| Erste Statuszustellung | 23:04:12 Uhr, message_id 11 best?tigt |
| Zweiter planm??iger Lauf | 23:19:06 Uhr: Schutzseite/CAPTCHA, Status unknown, Telegram message_id 12 best?tigt |
| Bestand XS / Helles Pink / SKU 673063170 | Nicht best?tigt; Schutzseite nicht umgangen |
| Neustartregel | unless-stopped konfiguriert; kein NAS-Neustart durchgef?hrt |

Quellen: deploy.log und verification.log auf der NAS. Telegram-Best?tigung bedeutet API-Annahme f?r die konfigurierte Chat-ID; sie best?tigt nicht, dass der Empf?nger die Nachricht gelesen hat.

Keine anderen Container oder Dienste wurden ge?ndert. Der Monitor bleibt entsprechend dem Auftrag alle 900 Sekunden aktiv, auch bei unbekanntem Bestand. Ein laufender Container allein ist kein Nachweis f?r eine funktionierende Bestandsauswertung.

Ergebnis: Container, Chromium, Schreibrechte, Telegram-Zustellung und zwei regul?re Durchl?ufe sind best?tigt. Die Bestandsauswertung ist wegen der auch auf der NAS gelieferten Schutzseite nicht erfolgreich verifiziert. Keine weitere automatische Umgehung oder zus?tzliche Abfrage durchgef?hrt.

## Update auf b745f8f mit erhaltenen lokalen ?nderungen

Am 08.10.2026 wurde der Upstream-Cookie-Fix mit der lokalen Variantenpr?fung zusammengef?hrt. 17 Tests bestanden, einschlie?lich verz?gertem OneTrust-Banner und fehlgeschlagenem Schlie?en. Lokale und NAS-.env blieben unver?ndert. Die lokalen ?nderungen vor dem Update sind zus?tzlich im Git-Stash gesichert; ersetzte NAS-Programmdateien in .update-backups/20261008-233335.

- Neuer Image-Build erfolgreich: sha256:3b06fd58bce2c82fec85b20acede7843e8e582cda798afabce9948552d39d524.
- Chromium-Start als UID 10001 und alle gepr?ften Schreibrechte erneut best?tigt.
- Container hollister-hollister-1 neu erstellt und gestartet, 23:42:41 Uhr Europe/Berlin.
- Telegram-Test best?tigt: message_id 14.
- Echte Shopabfrage 23:42:45 Uhr: Schutzseite/CAPTCHA, status=unknown.
- Zugeh?rige Telegram-Statusmeldung best?tigt: message_id 15.
- In diesem Lauf kein blockierender Cookie-Dialog nachgewiesen: Die Schutzseite verhindert bereits den Zugriff auf die Produktseite. Der Cookie-Fix ist damit synthetisch getestet, aber auf der echten Produktseite noch nicht best?tigt.

Quellen: update.log und verification-update.log auf der NAS. Bestand weiterhin nicht best?tigt. Ein zweiter Durchlauf nach diesem Update wurde bei dieser Kontrolle noch nicht abgewartet.

## Minutenintervall aktiviert

08.10.2026, 23:52:53 Uhr: Container mit Intervall=60s gestartet. Build und Chromium-Test erfolgreich. Telegram-Test 16, erste echte Abfrage 23:52:58 Uhr (Nachricht 17), n?chster automatischer Durchlauf 23:53:54 Uhr (Nachricht 18). Beide Abfragen weiterhin CAPTCHA/unknown. Unterschiedliche Abfragelaufzeiten erkl?ren die leicht unterschiedlichen Zustellabst?nde. Quelle: update.log und verification-update.log.

## Session-Monitor: zwei echte Bestandspruefungen bestaetigt

09.10.2026: Projekt hollister, Dienst session-monitor, Volume hollister_browser-data. Image sha256:bc4bd8eb59030f7051c892d3bb14c7b3eee9a9cb70ec30be2c358305cff12a5a. Start 01:17:23 Uhr Europe/Berlin, Intervall 60 Sekunden, Browser bleibt kontinuierlich offen. Erste Abfrage 01:17:38 Uhr: unavailable, Telegram 71. Zweite Abfrage 01:18:39 Uhr: unavailable, Telegram 72. Beide Male deutsche Produktseite ohne CAPTCHA, Helles Pink und XS explizit ausgewaehlt, sichtbare Ausverkauft-Anzeige. Interne Zuordnung zur angefragten SKU 673063170 nicht separat bestaetigt. Positive Verfuegbarkeit und Verhalten nach erneutem CAPTCHA oder NAS-Neustart sind damit nicht live verifiziert. Quelle: verification-session-20261009-011713.log. Die bisherigen Monitor- und manuellen Dienste wurden vor diesem Start gestoppt.
