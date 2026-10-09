# Hollister-Verfügbarkeitsdiagnose – 09.10.2026

> Historischer Zwischenstand. Die inzwischen abgeschlossene Live-Analyse steht in [AVAILABILITY_REPORT.md](AVAILABILITY_REPORT.md). Die früheren Blockade- und Nicht-prüfbar-Angaben unten sind durch den finalen Bericht ersetzt.

## Ergebnis und Grenzen

Der Benutzer hat die ursprüngliche Ziel-ID 63617320 auf **63270319** korrigiert und die zugehörige Suchseite gezeigt. Die produktiven Dateien auf der Synology wurden lesend untersucht. **Die tatsächliche Varianten-Datenquelle für Produkt 63270319 ist noch nicht ermittelt.** Ein cookie-freier direkter HTTP-Test auf der NAS liefert eine Schutzseite. Es liegen keine aufgezeichneten Produktantworten oder bestätigten Produkt-API-Endpunkte vor. Eine Umstellung auf HTTP wäre derzeit nicht begründet.

| Zielvariante | Ergebnis | Begründung |
|---|---|---|
| Weiß / XS | nicht prüfbar | Kein Zugriff auf bestehende Playwright-Sitzung |
| Weiß / S | nicht prüfbar | Kein Zugriff auf bestehende Playwright-Sitzung |
| Weiß / XXL | nicht prüfbar | Kein Zugriff auf bestehende Playwright-Sitzung |

Diese Ergebnisse bedeuten **keine Ausverkauft-Meldung**. Ein fehlendes Feld, eine fehlende Größe, ein deaktivierter Größenbutton, HTTP 403/429, CAPTCHA oder ein Parserfehler dürfen nicht als Bestand null interpretiert werden.

## Befunde am NAS-Code

SSH als `mevi` funktioniert. `/volume1/docker/hollister/manual_browser.py`, `product_checks.py`, `browser_check.py` und `compose.yaml` wurden direkt gelesen. Docker befindet sich unter `/usr/local/bin/docker`; Zugriff auf den Docker-Socket wird verweigert. `sudo -n` meldet, dass ein Passwort benötigt wird. Der Host zeigt einen Docker-Portproxy auf NAS-Loopback-Port 6080; das beweist weder einen zugänglichen Produkt-Tab noch funktionierende Bestandsprüfungen.

1. `product_checks.py` konfiguriert die Camisole mit der URL-Endnummer **63270319**. Nach der ausdrücklichen Korrektur durch den Benutzer passt diese ID zum Auftrag; der frühere Hinweis auf eine abweichende ID ist damit erledigt. Die produktive Konfiguration wurde nicht geändert. Der Screenshot zeigt mehrere Farbvarianten in der Suche, aber keine Größenbestände.
2. `manual_browser.py` startet Chromium über `launch_persistent_context` und hält den Kontext offen. Der gelesene Code konfiguriert keinen CDP-Port oder anderen externen Playwright-Anschluss. Ein weiteres Öffnen desselben Profils wäre keine Wiederverwendung der laufenden Sitzung und würde den exklusiven Profil-Lock verletzen.
   Nachtrag aus dem vom Benutzer bedienten Container-Terminal: In `/data/browser-profile/` ist kein `DevToolsActivePort` aufgelistet. Die selektive Suche in `/proc/*/cmdline` liefert mehrfach `--remote-debugging-pipe`. Damit ist die interne Pipe-Steuerung auch am laufenden Browser bestätigt. Diese Pipe ist kein HTTP-/WebSocket-CDP-Anschluss, an den sich das separate Skript anschließen kann. `ps` ist im Container nicht installiert. Weitere gleichartige Terminalprüfungen sind nicht erforderlich.
3. `variant_checks.py` lädt für zusätzliche Größen erneut; Farbe/Größe werden über Radiobuttons gewählt. Das Verfahren kann clientseitige Zwischenzustände reduzieren, liefert aber keinen Nachweis der zugrunde liegenden API.
4. `browser_check.py` verlangt die deutsche Produkt-URL und gewählte Radiobuttons. Ein sichtbarer Ausverkauft-Text bei inaktivem Warenkorb ergibt `unavailable`. Bestätigte Farb-/Größenüberschriften mit aktivem Warenkorb und ohne Ausverkauft-Text können nach fünf stabilen Sekunden `available` ergeben – **auch ohne unabhängig bestätigte SKU**. Der Kommentar zur zwingenden exakten Variante beschreibt diesen aktuellen UI-Zweig nicht vollständig.
5. Das vorhandene `stock_diagnostics.py` hört nur auf Responses, nur vom Host `www.hollisterco.com`, nur Fetch/XHR mit JSON-Content-Type und nur mit bekannter SKU im Antwortbody. Eine leere Camisole-SKU deaktiviert diese Suche. Begrenzte Feldlisten und höchstens acht Treffer können relevante Daten ausschließen. JSON-LD wird nachträglich aus dem DOM gelesen; initiales Response-HTML und Requests werden nicht erfasst.
6. Der Code kommentiert einen historischen JSON-LD-Datensatz mit Style-SKU `357-293-00059-630`. Dieser Befund ist kein aktueller Messwert für Camisole 63270319. Allgemeines Product-`InStock` belegt keine konkrete Farbe/Größe.

## Separates Diagnoseskript

`diagnose_availability.py` verändert weder Monitorcode noch Konfiguration. Es startet keinen Browser und öffnet kein Profil. Es verlangt einen **bereits vorhandenen CDP-Anschluss** und eine verifizierte deutsche Produkt-URL mit 63270319. Es legt einen eigenen Tab im vorhandenen Browserkontext an, registriert Request- und Response-Listener **vor** `goto`, und schließt anschließend ausschließlich diesen Diagnose-Tab. Die Monitortabs bleiben unberührt.

Erfasst werden HTTP-Methode, bereinigte URL/Queryparameter, Phase, Statuscode und selektierte Produktfelder aus JSON-Responses, initialem HTML und späteren DOM-Snapshots. Reines JSON und JSON-Zuweisungen in Scripts werden ohne JavaScript-Ausführung ausgewertet. Ausführbares JavaScript und `JSON.parse`-Stringliterale sind ausdrücklich nicht vollständig abgedeckt. Initiale HTML-Produktattribute werden zusätzlich selektiv erfasst. Externe Hosts, Roh-HTML, Rohbodys, Headers, Cookies, Speicherinhalte und Authentifizierungsdaten werden nicht exportiert. Unbekannte Querywerte werden ausgelassen, sensible Objektzweige verworfen. Es gibt Größen-/Tiefen-/Mengenlimits.

Phasen: initiales Laden → Weiß wählen → XS/S/XXL einzeln wählen → alternative Farbe wählen, sofern als Radiobutton mit passendem `aria-label` gefunden → zurück zu Weiß. Größenwerte werden sechs Sekunden lang überprüft und als UI-Evidenz gekennzeichnet. Das Skript nutzt dabei die vorhandene UI-Prüflogik; es implementiert noch keinen API-Bestandsadapter. Ein Wechsel ohne Netzwerkverkehr wäre ein Hinweis auf bereits geladene Daten, aber ohne gefundene Variantenstruktur kein Beweis für deren Vollständigkeit. Eine alternative Farbe ohne `aria-label` wird derzeit nicht automatisch gewählt.

Aufruf im Container, **erst wenn ein vorhandener CDP-Anschluss und die Ziel-URL bestätigt sind**:

```sh
python /tmp/diagnose_availability.py \
  --cdp http://127.0.0.1:9222 \
  --url 'VERIFIZIERTE_DEUTSCHE_PRODUKT_URL_MIT_63270319_OHNE_QUERY' \
  --http --output /tmp/availability-diagnostic.json
```

`127.0.0.1:9222` ist ein Beispiel, **kein entdeckter Anschluss**. Ein Container-Terminal allein löst den fehlenden CDP-Anschluss nicht. Für den gelesenen Startcode lässt sich kein gültiger Attach-Befehl angeben. Ein Neustart mit geändertem Browserstart oder eine Instrumentierung des laufenden Monitorprozesses wäre ein eigener Eingriff und wurde nicht vorgenommen. Der produktive Browser wird insbesondere nicht für diese Diagnose neu gestartet.

## API-Endpunkte und HTTP-Test

| Punkt | Tatsächlich bestätigt |
|---|---|
| Produkt-API-Endpunkt | Keiner |
| Methode/erforderliche Parameter | Noch unbekannt |
| Antwortstruktur mit Farb-/Größen-/SKU-Zuordnung | Noch unbekannt |
| Übertragung aller Größen beim Laden | Noch unbekannt |
| Netzwerkreaktion auf Farb-/Größenwechsel | Noch unbekannt |
| Cookie-/Authentifizierungsbedarf | Noch unbekannt |
| Direkter HTTP-Zugriff vom NAS | Ausgeführt: HTTP 200, Schutzseite, keine auswertbaren Produktdaten |

### Gemessener HTTP-Test auf der NAS

Die aktuelle Diagnosedatei wurde per SSH auf der NAS mit `--http-only` ausgeführt. Dieser Modus importiert kein Playwright und nutzt einen frischen `urllib`-Request ohne Cookies oder Authorization. Getestet wurde `GET https://www.hollisterco.com/shop/eu-de/p/camisole-mit-spitzenbesatz-fr-lagenlooks-63270319`. Ergebnis: HTTP 200, 3038 Antwortbytes, Weiterleitung in `/shop/eu/p/`, Schutzseite erkannt, ein Script, keine extrahierbaren JSON-Produktfelder und keine Produktkontrollen. Die exakte Ziel-URL der Weiterleitung wurde durch den konservativen Pfadfilter gekürzt. Rohdaten wurden nicht gespeichert.

Bereinigtes echtes Messergebnis:

```json
{"product_id":"63270319","http_test":{"status":200,"bytes":3038,
 "challenge_detected":true,"embedded":{"script_count":1,"json":[],
 "product_controls":[]}}}
```

Das belegt, dass diese konkrete cookie-freie Produktseitenanfrage derzeit keine nutzbare Bestandsquelle liefert. Es beweist nicht, dass ein noch unbekannter separater API-Endpunkt ebenfalls gesperrt wäre. Alle drei Größen bleiben nicht prüfbar. Ergebnisdatei auf der NAS: `/volume1/docker/hollister/diagnostics-63617320/http-probe-63270319.json`. Der Diagnoseordner behält seinen ursprünglichen Namen; sein Name bezeichnet nicht mehr das aktuelle Zielprodukt.

Mit `--http` testet das Skript die bestätigte Produkt-URL und höchstens zehn tatsächlich beobachtete, sicherheitsgefilterte GET-Endpunkte mit Bestandsfeldern über Python `urllib`, ohne Playwright, Cookies oder Authorization. Warenkorb-, Bestell-, Konto- und Loginpfade werden nicht wiederholt. POST-Endpunkte werden dokumentiert, aber nicht automatisch wiederholt, da eine lesende Funktion erst bestätigt werden müsste. HTTP 200 allein bedeutet keinen Erfolg: gleiche Produktidentität, deutscher Markt, vollständige Varianten und widerspruchsfreie Bestandsfelder müssen anschließend mit der Browseraufnahme verglichen werden. Die HTTP-Antworten werden ebenfalls nur selektiv exportiert. Erforderlichkeit einzelner Parameter ist durch Beobachtung noch nicht bewiesen und braucht kontrollierte Vergleichsanfragen.

Illustration des Ausgabeformats, **synthetisch, keine Hollister-Messdaten**:

```json
{"phase":"select_size_XS","method":"GET","status":200,
 "records":[{"path":"$.variants[0]","fields":{
   "productId":"63270319","color":"Weiß","size":"XS",
   "sku":"BEISPIEL","availability":"InStock"}}]}
```

## Zuverlässigkeit und Empfehlung

UI-Prüfungen belegen die Shopdarstellung zum Messzeitpunkt; sie belegen keinen reservierten Lagerbestand. Die Stabilitätsfrist verhindert nicht jede verspätete Aktualisierung. Für eine HTTP-Umstellung braucht es eine bestätigte Zuordnung Produkt → Farbe → Größe → SKU sowie die dokumentierte Bedeutung des konkreten Verfügbarkeitsfelds. Widersprüche oder unvollständige Antworten müssen `nicht prüfbar` ergeben. Ein allgemeines `InStock` oder ein vorhandener Größenname reicht nicht.

Empfehlung: **vorerst keine Umstellung**. Die Ziel-ID ist nun geklärt. Als nächstes braucht es eine autorisierte Lösung für die Instrumentierung der bestehenden Browserverbindung, um echte Variantenantworten zu beobachten. Zusätzliche cookie-freie API-Vergleichsanfragen sind erst mit entdeckten Endpunkten sinnvoll. Eine spätere HTTP-Implementierung sollte zunächst nur im Vergleichsbetrieb geprüft werden, mit Timeout-/403-/429-/Schemafehlern als unbekannt und maßvollem Abfrageintervall. Produktive Umstellung erst nach ausdrücklicher Freigabe.

## Validierung und unveränderter Betrieb

Die neue Datei lässt sich kompilieren. Vier neue Tests prüfen Datenschutzfilter und Extraktion; 13 vorhandene Tests für Diagnose, Produkt-/Größenkonfiguration und LiveSession wurden erfolgreich ausgeführt. Das ist keine Live-Verifikation mit Hollister. Vorhandene lokale Änderungen bleiben erhalten. Kein Image-Build, Container-Neustart, Telegram-Versand, Profilzugriff oder produktiver Dateiaustausch wurde durchgeführt.
