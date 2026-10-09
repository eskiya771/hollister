# Hollister: technische Verfügbarkeitsdiagnose

> Ergänzung: Der später erfolgreich bestätigte direkte GraphQL-/HTTP-Weg für beide Produkte ist in [HTTP_API_REPORT.md](HTTP_API_REPORT.md) dokumentiert. Die damalige Aussage, es sei noch keine API bestätigt, beschreibt den früheren Untersuchungsstand.

Stand: 09.10.2026. Produkt: Camisole mit Spitzenbesatz für Lagenlooks, Produktseite **63270319**, Weiß, XS/S/XXL. Der Benutzer hat die ursprüngliche Ziel-ID 63617320 auf 63270319 korrigiert.

## Ergebnis

**Die Bestandsdaten werden bereits im initialen HTML übertragen**, in einem eingebetteten JSON-Zustand unter `CACHE.ROOT_QUERY.<dynamischer Schlüssel>.collection.skus`. Eine separate Online-Bestands-API wurde beim untersuchten Ablauf nicht aufgerufen.

Die Produktseiten-ID ist von den internen Farb-Produkt-IDs zu unterscheiden: Der ausdrücklich als Weiß ausgewählte Radiobutton hat den Wert **63617331**. 63617320 kommt ebenfalls in der Collection vor, ist aber nicht der in dieser Aufnahme ausgewählte Weiß-Radiobutton.

| Weiß / Größe | interne `productId` | `shortSku` | `sizePrimary` | `inventory` | `inventoryStatus` | Ergebnis |
|---|---|---|---|---:|---|---|
| XS | 63617331 | 671819156 | XS_p | 0 | Unavailable | ausverkauft |
| S | 63617331 | 671635648 | S_p | 0 | Unavailable | ausverkauft |
| XXL | 63617331 | 670148021 | XXL_p | 42 | Available | verfügbar |

Alle drei Datenzustände stimmen mit sechs aufeinanderfolgenden UI-Prüfungen pro Größe überein. Bestand ist eine Momentaufnahme, keine Reservierung. Ob `inventory` exakt die kaufbare Stückzahl ausdrückt, wurde nicht durch eine Bestellung geprüft.

## Aufnahme und Betrieb

Zuerst wurde der NAS-Code lesend untersucht. Chromium nutzte `--remote-debugging-pipe`, keinen externen CDP-Anschluss. Der SSH-Benutzer `mevi` hat keine Docker-Rechte. Nach ausdrücklicher Freigabe wurde ein einmaliger DSM-root-Job eingesetzt: ursprünglichen Monitor kontrolliert stoppen, separaten Diagnosecontainer mit vorhandenem Image und persistentem Profil starten, anschließend den ursprünglichen Container wieder starten.

Gespeicherte Browserdaten wurden weiterverwendet; **der zuvor laufende Browserprozess wurde nicht ohne Unterbrechung weiterverwendet**. Die Diagnose erforderte den später freigegebenen Neustart. Der temporäre CDP-Port war nur innerhalb des Containers erreichbar und wurde nicht auf dem NAS veröffentlicht. Der vorhandene noVNC-Port blieb an NAS-Loopback gebunden. Telegram-Zugangsdaten wurden nicht an den Diagnosecontainer übergeben.

Request-/Response-Listener wurden vor der Produktnavigation im eigenen Diagnose-Tab registriert. Erfasst wurden initiales HTML, eingebettetes JSON, spätere DOM-Snapshots und Document-/Fetch-/XHR-Verkehr des Hosts `www.hollisterco.com`. Die finale Aufnahme enthält **35 Requests und 35 Responses**, keine gemeldeten Diagnosefehler. Ein früherer Dateitransferfehler wurde korrigiert; die finale Aufnahme wurde erfolgreich übernommen.

Der letzte Job protokolliert `Original monitor restarted unchanged`, Exitcode 0. Produktiver Code, Image, Compose-Konfiguration und .env wurden nicht geändert. Nur separate Diagnoseartefakte wurden angelegt. Der temporäre Diagnosecontainer wurde entfernt. Reguläre Monitorzustellungen nach Neustart bleiben Teil des bisherigen Betriebs.

## Befunde am bestehenden Code

- `product_checks.py`: URL 63270319, eigenständige Camisole-Konfiguration, Größen XS/S/XXL. Die URL passt nach der Benutzerkorrektur.
- `manual_browser.py`: persistenter sichtbarer Chromium, Profil-Lock und dauerhaft offener Kontext; Monitor läuft im selben Prozess.
- `variant_checks.py`: für zusätzliche Größen erneute Navigation.
- `browser_check.py`: deutsche URL und ausgewählte Radiobuttons; Ausverkauft-Text/inaktiver Warenkorb ergibt `unavailable`. Bestätigte Überschriften, aktiver Warenkorb und stabiler Zustand können auch ohne genaue SKU `available` ergeben.
- `stock_diagnostics.py`: nur wenige JSON-Fetch-/XHR-Antworten mit bereits bekannter SKU; leere SKU deaktiviert die Suche. Initiales HTML, Requests, `shortSku` und `sizePrimary` werden von dieser Suche nicht erfasst.

Die gefundenen Felder erklären, warum JSON-LD- oder reine `sku`-Suche Daten verfehlen kann. Allgemeines Product-`InStock` ist kein Beleg für Farbe und Größe.

## Bestätigte Datenstruktur

Die erste erfolgreiche Browsernavigation lieferte HTTP 200 mit einem Dokument von ungefähr 627 KB. Dessen **Response-Body vor DOM-Nachbearbeitung** enthält bereits die Collection-SKU-Records.

```text
CACHE.ROOT_QUERY.<dynamischer Cache-Schlüssel>.collection
  products[]
  skus[]
```

Der dynamische Schlüssel wurde aus Datenschutzgründen als `*` exportiert. Der Zustand entspricht strukturell einem normalisierten GraphQL-Cache; eine bestimmte Clientbibliothek oder ein serverinterner Upstream ist nicht separat nachgewiesen.

Echte bereinigte Beispieldaten:

```json
[
  {"productId":"63617331","shortSku":"671819156",
   "sizePrimary":"XS_p","sizeSecondary":null,
   "inventory":0,"inventoryStatus":"Unavailable"},
  {"productId":"63617331","shortSku":"671635648",
   "sizePrimary":"S_p","sizeSecondary":null,
   "inventory":0,"inventoryStatus":"Unavailable"},
  {"productId":"63617331","shortSku":"670148021",
   "sizePrimary":"XXL_p","sizeSecondary":null,
   "inventory":42,"inventoryStatus":"Available"}
]
```

Die Größenkennungen passen in dieser Aufnahme zur ausdrücklich ausgewählten UI-Größe. Ein Adapter muss die beobachtete `_p`-Zuordnung ausdrücklich behandeln und weitere Größen-/Längendimensionen berücksichtigen.

## Wechselreaktionen

| Phase | erfasste Shop-Requests | Befund |
|---|---:|---|
| Laden | 30 | HTML und Hilfs-/BFF-Aufrufe |
| Weiß wählen | 3 | Unter anderem Outfits/Matching-Sets; keine Stock-Antwort |
| XS wählen | 0 | Bereits geladene Daten |
| S wählen | 0 | Bereits geladene Daten |
| XXL wählen | 0 | Bereits geladene Daten |
| andere Farbe | 1 | Farbradiobutton-Wert 63234052 |
| zurück zu Weiß | 1 | Farbradiobutton-Wert erneut 63617331 |

„0“ bedeutet keine erfassten Document-/Fetch-/XHR-Requests an den Hollister-Host, keine Aussage über externe Hosts oder Bild-/Scriptverkehr. Zusammen mit initialen SKU-Daten und übereinstimmender UI ist dies ein starker Beleg für clientseitige Größen-/Bestandsauswertung.

## Endpunkte, Methoden und Parameter

Alle Pfade gehören zu `https://www.hollisterco.com`.

| Endpunkt | Methode | Beobachtete Parameter / Body | Antwort und Einordnung |
|---|---|---|---|
| `/shop/eu-de/p/camisole-mit-spitzenbesatz-fr-lagenlooks-63270319` | GET | Keine Query für beobachteten Browseraufruf; gespeicherte Sitzung vorhanden | HTML mit Collection-SKUs: bestätigte Bestandsquelle |
| `/api/bff/product` | GET | Marktparameter, `operationName`, JSON-`variables`, `extensions.persistedQuery` | GraphQL `data.savesList`, `content.specificESpot`, `outfits`, `matchingSets`; kein beobachteter Online-Stock-Response |
| `/api/bff/catalog` | POST | Marktparameter; GraphQL-Batch mit `operationName`, `variables`, `query` | Array von Ergebnissen, `data.currentCountry` beziehungsweise `data.content` |
| `/api/bff/fulfillment` | POST | `FetchStoreAvailabilityText`, `FetchStoreLocatorText`, `FetchStoreLocatorCountries`; jeweils `variables` und `query` | Texte und `storeLocatorCountries`; keine tatsächlichen Online-Größenbestände |
| `/static/product/000f69d1/static/tmnt/-3_19158_DE.json` | GET | Locale/Markt im Pfad | Statische Texte, keine bestätigte SKU-Bestandsquelle |

Öffentliche Marktparameter: `storeId=19158`, `catalogId=11558`, `langId=-3`, `brand=hol`, `store=h-eu-de`, `country=DE`, `urlRoot=/shop/eu-de`, `currency=EUR`. Zusätzlich beim Catalog: `storePreview=false`, `aemContentAuthoring=0`.

Beobachtete Product-Operationen: `SavesListQuery`, `HowToMeasureEspot`, `GetOutfits`, `GetMatchingSets`. Persisted Queries verwenden `version: 1` und operationabhängige `sha256Hash`-Werte. Die bereinigte Aufnahme enthält diese öffentlichen Metadaten.

**Beobachtet ist nicht gleich erforderlich:** Einzelne Parameter wurden nicht systematisch entfernt. Unbekannte Variablenfelder und Querytexte wurden nicht exportiert. Ein bereinigtes `variables={}` beweist keine ursprünglich leeren Variablen. Vollständig ausführbare BFF-Abfragen oder ein erforderliches Authentifizierungsverfahren sind daher nicht für alle Operationen behauptet. POSTs wurden nicht automatisch wiederholt; die beobachteten Hilfsoperationen sind ohnehin keine Online-Bestandsquelle.

## Direkte HTTP-Prüfung

Ausführung auf der Synology über Python `urllib`, ohne Playwright, Browsercookies oder Authorization:

| Anfrage | Messergebnis | Bewertung |
|---|---|---|
| GET auf Produktseite | HTTP 200, Weiterleitung nach `/shop/eu/p/...63270319`, 3038 Bytes, Schutzseite, keine Produktcontrols/Bestandsrecords | nicht prüfbar; HTTP 200 allein ist kein Erfolg |
| Beobachteter BFF-GET `SavesListQuery`, sicherheitsgeprüfte Originalparameter | HTTP 400 | Wunschlistenoperation, keine Bestandsquelle; kein erfolgreicher HTTP-Stock-Test |

Der BFF-400 beweist weder einen generellen Cookie-Zwang noch eine allgemeine API-Sperre. Cookie-/Header-/Persisted-Query-Bedingungen wurden nicht isoliert. Ein HTTP-Test mit Browsercookies fand nicht statt. Belastbar ist: **Die identifizierte HTML-Bestandsquelle ist über die getestete cookie-freie Anfrage nicht nutzbar.** Kein CAPTCHA wurde umgangen.

## Zuverlässigkeit und Empfehlung

Der separate Offline-Analyzer verlangt die eindeutig gewählte Weiß-ID, konkrete Größe, eigene `shortSku`, widerspruchsfreie Status-/Mengenwerte und übereinstimmende UI. `Available` mit positiver ganzzahliger Menge ergibt verfügbar; `Unavailable` mit 0 ergibt ausverkauft. Fehlende/mehrdeutige Identität, fehlende Größe, unbekannter Status, widersprüchliche Menge oder UI ergeben nicht prüfbar. Eine fehlende Größe ist kein Nullbestand.

Grenzen: zwei erfolgreiche Aufnahmen am selben Tag, keine langfristige Schema-/Sitzungsprüfung, keine Bestellung, keine Garantie der Cache-Aktualität. Eine spätere Prüfung muss aus einer erfolgreich frisch geladenen Produktantwort lesen; alte DOM-/Cache-Daten dürfen nicht weiter als aktueller Bestand gelten.

**Vorerst keine vollständige HTTP-Umstellung.** Die Struktur ist bekannt, der cookie-freie Zugriff auf die tatsächliche Quelle funktioniert aber nicht. Sinnvoll wäre als gesondert freizugebender Schritt ein vergleichend laufender Adapter im bestehenden Browsermonitor, der alle drei Größen aus einer einzigen frischen Collection-Antwort liest. Er muss Farbe → interne Produkt-ID → Größe/SKU explizit verbinden und Schutzseiten/Strukturfehler als unbekannt behandeln. Diese Monitoränderung wurde nicht vorgenommen.

Ein späterer HTTP-Vergleichstest mit ausschließlich intern gehaltenen Sitzungscookies könnte klären, ob der Browser nur zur Sitzungserhaltung benötigt wird. Das wäre noch keine robuste vollständige Playwright-Ablösung. Produktive Umstellung erst nach Freigabe und erfolgreichem Vergleich über mehrere Läufe einschließlich Fehlerfällen.

## Artefakte und Datenschutz

NAS-Ordner: `/volume1/docker/hollister/diagnostics-63617320/`. Der historische Ordnername ändert die aktuelle Ziel-ID 63270319 nicht.

- `diagnose_availability.py`: separate Live-Diagnose/HTTP-Prüfung.
- `diagnostic_browser_entry.py`, `run-nas-diagnosis.sh`: temporärer Diagnosejob mit Wiederherstellung.
- `analyze_availability_capture.py`: Offline-Auswertung.
- `availability-diagnostic.json`: bereinigte finale Aufnahme.
- `availability-summary.json`: kompakte Ergebnisse.
- `job-status.log`: Abschlussnachweis.

Keine Headers, Cookies, Authentifizierung, Roh-HTML oder Rohbodys wurden exportiert. Sensible Objektzweige werden verworfen; Ausgabe enthält ausgewählte Produktfelder, öffentliche Markt-/GraphQL-Metadaten und bereinigte Strukturpfade. Unbekannte Werte werden ausgelassen. Größen-/Tiefen-/Mengenlimits begrenzen die Auswertung. Ausführbares JS und `JSON.parse`-Stringliterale werden nicht vollständig rekonstruiert.

22 relevante lokale Tests bestanden: Datenschutz-/GraphQL-Metadatenfilter, exakte Variantenauswertung, falsche Farbe, fehlende Größe, Bestandswiderspruch und bestehende Produkt-/Varianten-/Sessiontests. Zusätzlich liegt die echte NAS-Aufnahme vor. Keine produktive Umstellung erfolgte.
