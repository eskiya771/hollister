> Aktueller Betrieb (09.10.2026, 01:19 Uhr): Im Projekt `hollister` laeuft jetzt `session-monitor` mit dauerhaft offenem Browser und 60-Sekunden-Takt. Zwei echte Ausverkauft-Meldungen fuer Helles Pink / XS und Telegram-Zustellungen (71, 72) sind bestaetigt. Siehe docs/VERIFICATION.md. Die folgenden Anleitungen zum reinen manuellen Modus beschreiben den vorherigen Betriebszustand. Den laufenden Session-Monitor nicht durch einen separaten Monitor oder resume-Befehl ersetzen.

# Aktueller manueller Betrieb

Projektname: `hollister`. Bestehendes Volume: `hollister_browser-data`. Der manuelle Browser bleibt bis zur ausdr?cklichen Anweisung ge?ffnet; Monitor und Telegram-Pr?fschleife bleiben gestoppt. Lokale ?ltere Live-Browser-Varianten sind erhalten, werden f?r diesen Modus aber nicht gestartet.

## Manual CAPTCHA session on Synology

The optional `manual-browser` service displays Chromium through noVNC using the
same Docker volume and profile as the monitor. It does not solve challenges.
An exclusive file lock prevents both services from opening the profile at once.
This mode is implemented but still requires a Docker build and live test on your NAS.

Keep the existing project directory and Compose project name: a new project name
would create a different `browser-data` volume. Do not run `down -v`.

In the NAS project folder, stop the monitor before starting the manual service:

```sh
docker compose stop hollister
docker compose --profile manual up -d --build manual-browser
docker compose --profile manual logs --tail=50 manual-browser
```

On your PC, open a separate terminal and keep this SSH tunnel running. Replace
`NAS_USER` and `NAS_IP` with your DSM SSH user and NAS address:

```sh
ssh -N -L 127.0.0.1:6080:127.0.0.1:6080 NAS_USER@NAS_IP
```

Open `http://127.0.0.1:6080/vnc.html` on the PC and click Connect.
The browser shown there runs **on the NAS**, not on your PC. Solve any challenge
manually, dismiss cookies and confirm the German shop, Helles Pink and XS.
noVNC has no VNC password in this configuration; its published port binds only
to NAS loopback and SSH provides authentication and encryption. Do not change
the binding to `0.0.0.0`, expose it through a reverse proxy or forward it on your router.
Other local NAS processes can reach the loopback port while the service runs.

Save the browser profile with a graceful stop, then test one automatic check:

```sh
docker compose --profile manual stop manual-browser
docker compose build hollister
docker compose run --rm --no-deps hollister python app.py --once
```

Review the actual Telegram result. If it is correct, start the 15-minute monitor:

```sh
docker compose up -d hollister
docker compose logs --tail=50 hollister
```

Close the SSH tunnel with Ctrl+C. A successful manual challenge does not guarantee
future automatic requests work: session-only cookies, browser restarts or the
change from a visible to a headless browser may trigger a new challenge.
An unknown result must remain unknown; do not treat it as sold out.


---

# Erhaltene lokale Dokumentation (bisheriger Monitorbetrieb)

> Aktuelle Einstellung: Seit der Umstellung am 08.10.2026 betr?gt das Pr?f- und Meldeintervall **60 Sekunden**. Die unten dokumentierten 15-Minuten-Tests sind historische Nachweise vor dieser ?nderung. Auf der NAS seit 23:52:53 Uhr aktiv; zwei automatische Abfragen und Telegram-Nachrichten 17 und 18 sind best?tigt.

# Hollister auf Synology

Überwacht ausschließlich den deutschen Artikel 63757420, gewünschte SKU **673107873**, **XS**, **Helles Pink**. Eine Telegram-Meldung nach der ersten Abfrage direkt beim Start, danach bei jedem Durchlauf (auch unverändert) im Abstand von 900 Sekunden. Bei Ladeproblemen oder Schutzseiten wird „Status nicht prüfbar“ gemeldet.

## Erkennung und Grenzen

Der Browser schließt bekannte Cookie-Dialoge, stellt bei US-Weiterleitung Deutschland ein und wählt Farbe und Größe ausdrücklich aus. Bestandsmeldungen erfordern dieselbe SKU, Größe, Farbe und Verfügbarkeit in einem JSON-LD-Product-Datensatz sowie dazu passende Auswahl und sichtbaren Bestandsstatus. Widersprüche, deaktivierte/nicht auswählbare Größen und fehlende Variantendaten ergeben unbekannt. Ein aktiver Warenkorbbutton allein belegt keinen Bestand. Zwei Sekunden stabile Darstellung sind nur eine zusätzliche Prüfung, kein Ersatz für Variantenidentität.

**Die Datenstruktur auf der echten Produktseite ist noch nicht bestätigt:** Der lokale Shoptest vom 08.10.2026 erhielt eine Client-Challenge/CAPTCHA. Falls der Shop auf der Synology zugänglich ist, aber keine entsprechend genauen JSON-LD-Daten liefert, bleibt die Meldung unbekannt. Dann muss der Adapter anhand der dort tatsächlich gelieferten Variantendaten angepasst werden. Die App löst und umgeht keine Sicherheitsprüfungen. Ein unbekannter Status ist kein ausverkaufter Artikel und keine erfolgreich geprüfte Verfügbarkeit.

## Bisher tatsächlich geprüft

- Windows, Python 3.12.13, Playwright 1.63.0: Chromium erfolgreich installiert und gestartet, persistenter Kontext funktionsfähig.
- 13 Unit-Tests zu exakter Variantenidentität, widersprüchlichen Daten, Telegram-Antworten, Geheimnis-Redaktion, sofortigem Start und 900-Sekunden-Takt bestanden.
- Echter Chromium mit synthetischer Produktseite: verzögerte Aktualisierung von falscher Größe zu ausverkauftem XS wird korrekt behandelt (1 Test bestanden).
- Echter Hollister-Aufruf: Schutzseite erkannt, Ergebnis unbekannt; keine CAPTCHA-Umgehung.
- Docker lokal nicht installiert: Image-Build, Linux-Browser, NAS-Rechte und Neustartverhalten noch nicht praktisch geprüft.
- Telegram mit echten Zugangsdaten und zwei echte NAS-Durchläufe im Abstand von 15 Minuten noch offen.

## Dateien und Geheimnisse

Die ausgefüllte `.env` gehört nur lokal und nach `/volume1/docker/hollister/.env`. Vorlage: `.env.example`. Die App ergänzt PRODUCT_SKU=673107873, wenn eine ältere .env diesen Schlüssel noch nicht enthält. Vorhandene Prozessvariablen haben Vorrang. UTF-8 mit oder ohne BOM wird unterstützt. Keine Tokens in Befehlszeilen oder Ausgaben einfügen. `docker compose config` ohne `--quiet` kann Geheimnisse ausgeben.

`.env`, `*.env`, Browserprofile, virtuelle Python-Umgebung und Testartefakte sind aus Git und dem Docker-Buildkontext ausgeschlossen. Der Dockerfile kopiert nur Programmdateien. Es gibt keine eingehenden Ports.

## Installation ohne SSH

1. In File Station unter der Freigabe `docker` einen Ordner `hollister` erstellen; physischer Pfad `/volume1/docker/hollister`. Von Windows erreichbar als `\\192.168.178.86\docker\hollister`.
2. `app.py`, `browser_check.py`, `smoke_browser.py`, `Dockerfile`, `compose.yaml`, `requirements.txt`, `.dockerignore` und die ausgefüllte `.env` dorthin kopieren. Nicht nur GitHub herunterladen: Die aktuellen Änderungen liegen zunächst lokal.
3. Container Manager öffnen → **Projekt** → **Erstellen**. Name `hollister`, Pfad `/volume1/docker/hollister`, vorhandene `compose.yaml` verwenden. Je nach DSM-Version heißt die Option „vorhandene Compose-Datei verwenden“ oder ähnlich. Keine Webportal-/Portfreigabe einrichten. Projekt erstellen/bauen/starten.
4. Beim Container `hollister` die **Protokolle** öffnen. Erwartet: `Monitor gestartet`, anschließend `stock_check status=...` und `status=... telegram_message_id=...`.
5. Im Container-Terminal `python smoke_browser.py` ausführen. Erwartet: beschreibbare Verzeichnisse und `chromium_start=ok`. Der Smoke-Test nutzt ein separates temporäres Profil.
6. Im Container-Terminal `python app.py --test-telegram` ausführen. Erwartet: `telegram_test message_id=...` sowie die Testnachricht im konfigurierten Chat. Keinen zweiten regulären Monitor und keine zusätzliche Bestandsabfrage parallel mit demselben Profil starten.
7. Erste echte Statusmeldung im Chat und Logs vergleichen. Nach dem nächsten regulären Durchlauf (15 Minuten nach Beginn der ersten Abfrage) eine zweite Nachricht und neue message_id kontrollieren. Die Laufzeit der Abfrage kann Zustellzeitpunkte geringfügig verschieben.
8. Bei `unknown` den protokollierten Grund prüfen. Schutzseite: keine Umgehung; der Bestand ist nicht bestätigt. Fehlende exakte Variantendaten: Adapter anhand der zugänglichen echten Seite nacharbeiten. Den Betrieb erst nach tatsächlich bestätigter Bestandsauswertung und Telegram-Zustellung als erfolgreich betrachten.

## Installation mit autorisiertem SSH

Auf der NAS als berechtigter Benutzer ausführen; bei älteren DSM-Versionen ggf. `docker-compose` statt `docker compose`. Zuerst prüfen, dass das Modell eine von Playwright unterstützte Linux-Architektur besitzt (amd64 oder arm64, kein ARMv7) und Container Manager installiert ist.

```sh
uname -m
docker compose version
cd /volume1/docker/hollister
chmod 600 .env
docker compose -p hollister config --quiet
docker compose -p hollister build hollister
docker compose -p hollister run --rm --no-deps hollister python smoke_browser.py
docker compose -p hollister up -d --no-deps hollister
docker compose -p hollister logs --tail=80 hollister
docker compose -p hollister exec -T hollister python app.py --test-telegram
docker compose -p hollister logs --follow --since=2m hollister
```

Wenn Docker-Berechtigungen fehlen, diese Befehle mit `sudo` ausführen; keine globalen Docker-Rechte oder anderen Dienste ändern. Logs mit Strg+C verlassen: Der Container läuft weiter. Nach mindestens 15 Minuten die beiden echten Statusmeldungen kontrollieren. `up` und `build` betreffen hier ausschließlich das Projekt und den Dienst `hollister`.

## Container und Neustart

Nicht-root-Benutzer UID 10001. Persistentes Docker-Volume `hollister_browser-data` auf `/data`; Profil, HOME, Cache und Konfiguration liegen dort. `/tmp` ist ein beschreibbares tmpfs (512 MiB, Modus 1777), `/dev/shm` erhält 512 MiB. Root-Dateisystem schreibgeschützt; alle zusätzlichen Capabilities entfernt, keine Privilegieneskalation. Chromium und seine Linux-Abhängigkeiten werden passend zur gepinnten Playwright-Version installiert. Der Smoke-Test prüft die tatsächlichen Rechte und den Browserstart auf der NAS.

Chromium verwendet die Playwright-Standardeinstellung ohne Chromium-Sandbox; die genannten Containerbeschränkungen bleiben aktiv. Es wird weder `privileged` noch `SYS_ADMIN` gesetzt. Eine Chromium-Sandbox wäre gesondert mit der NAS-Kernel-/seccomp-Unterstützung zu testen.

`restart: unless-stopped` startet den laufenden Monitor nach Docker-/NAS-Neustart automatisch wieder. Ein zuvor manuell gestoppter Container bleibt gestoppt. Keine NAS-Neustarts durchführen, die andere Dienste unterbrechen. Quellen: [Docker-Neustartregeln](https://docs.docker.com/engine/containers/start-containers-automatically/), [Playwright-Dockerhinweise](https://playwright.dev/python/docs/docker).

## Lokale Tests

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe -m unittest -v
.venv/Scripts/python.exe smoke_browser.py
.venv/Scripts/python.exe app.py --check-only
.venv/Scripts/python.exe app.py --test-telegram
```

`--check-only` prüft ohne Nachricht, `--once` prüft und sendet einmal. Exitcodes: 0 = bestätigter Bestand / erfolgreicher Telegram-Test, 1 = Zustellfehler, 2 = unbekannter Bestand oder Konfigurationsfehler. Einmalige Browserabfragen nur bei gestopptem Monitor mit demselben Profil durchführen. Ohne CLI-Option startet der dauerhafte 15-Minuten-Betrieb. Telegram-Fehler werden ohne Token protokolliert; der nächste planmäßige Durchlauf versucht erneut zu senden.
