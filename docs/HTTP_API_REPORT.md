# Bestandsprüfung über direkte HTTP-/GraphQL-Abfragen

Stand: 09.10.2026. Dieser Bericht ergänzt und ersetzt die früheren Aussagen, dass noch kein nutzbarer API-Endpunkt bestätigt sei. **Für beide Oberteile wurde nun ein funktionierender direkter API-Weg auf der Synology bestätigt.**

## Ergebnis

Der unabhängige Python-Checker fragt `/api/bff/product` mit einer lesenden GraphQL-POST-Anfrage ab. Er läuft auf dem NAS-Host, ohne Playwright-Import, Browsersteuerung, Cookie-Übernahme oder Authentifizierung. Browserartige Standard-Header werden verwendet; TLS-Fingerprints, CAPTCHA-Lösung oder eine Sicherheitsumgehung sind nicht implementiert.

| Produktseite | Farbe | `collectionId` | interne `productId` | Größe | `shortSku` | aktueller API-Bestand |
|---|---|---|---|---|---|---|
| 63757420, Henley | Helles Pink | 711658 | 63766393 | XS | 673107742 | 0 / Unavailable |
| 63757420, Henley | Helles Pink | 711658 | 63766393 | S | 673107911 | 0 / Unavailable |
| 63270319, Camisole | Weiß | 706282 | 63617331 | XS | 671819156 | 0 / Unavailable |
| 63270319, Camisole | Weiß | 706282 | 63617331 | S | 671635648 | 0 / Unavailable |
| 63270319, Camisole | Weiß | 706282 | 63617331 | XXL | 670148021 | 42 / Available |

Die IDs und Größen-SKUs entsprechen den zuvor bestätigten Browserauswahlen. Die Bestandswerte sind Momentaufnahmen, keine Reservierung. Der Camisole-Browseraufruf war im aktuellen Vergleichslauf gesperrt; die nachfolgende direkte API-Abfrage war dennoch erfolgreich. Ältere Browserdaten wurden zur Identitätsprüfung verwendet, nicht als neuer Bestand ausgegeben.

## Gefundener Endpunkt und ausführbare Anfrage

```text
POST https://www.hollisterco.com/api/bff/product
  ?storeId=19158&catalogId=11558&langId=-3
  &brand=hol&store=h-eu-de&country=DE
  &urlRoot=%2Fshop%2Feu-de&currency=EUR
Content-Type: application/json
```

Body für Henley / Helles Pink:

```json
{
  "query": "query DiagnosticCollection { collection(collectionId: \"711658\", productId: \"63766393\", faceout: \"\") { collection { skus { productId shortSku sizePrimary sizeSecondary inventory inventoryStatus } } } }"
}
```

Für Camisole / Weiß: `collectionId="706282"`, `productId="63617331"`. Kein Persisted-Query-Hash ist für diese ausdrücklich übertragene Query nötig. Die Anfragen wurden ohne Authorization und ohne zuvor gespeicherte Cookies ausgeführt; pro Anfrage wird eine neue leere CookieJar angelegt. API-Responses kamen ohne Umleitung zurück.

Antwortstruktur:

```json
{
  "data": {
    "collection": {
      "collection": {
        "skus": [
          {"productId":"63617331","shortSku":"670148021",
           "sizePrimary":"XXL_p","sizeSecondary":null,
           "inventory":42,"inventoryStatus":"Available"}
        ]
      }
    }
  }
}
```

Die Collection-Antwort enthält mehrere Farben und Größen. Auswertung muss nach **interner Farb-Produkt-ID, Größenkennung und bestätigter SKU** filtern; der erste Record oder irgendein positiver Bestand wäre falsch.

## Entdeckung und Parameterprüfung

1. Das initiale Henley-HTML enthält `CACHE.ROOT_QUERY.collection(...)` mit den öffentlichen Argumenten `collectionId=711658`, `productId=63757975`, `faceout=""`. Daraus wurde eine ausdrücklich lesende Query mit den bereits bekannten SKU-Feldern rekonstruiert. Sie lieferte HTTP 200 und sämtliche Collection-SKUs.
2. `productId=63757975` ist die ursprünglich geladene andere Farbvariante. Der spätere Checker verwendet die bestätigte Ziel-Farb-ID 63766393. Beide Variantenaufrufe liefern die Collection, deren SKU-Liste anschließend nach Zielfarbe gefiltert wird.
3. Eine Query nur mit `productId` liefert HTTP 400. Mit leerer `collectionId` und passender `productId` folgt HTTP 200, aber keine nutzbare Collection. Die richtige interne Collection-ID ist daher entscheidend; Produktseiten-ID und Collection-ID sind nicht austauschbar.
4. Weglassen von `productId` bei korrekter Collection-ID liefert HTTP 400 mit Fehlerbezug auf das Argument `productId`.
5. Weglassen von `faceout` bei korrekter Collection- und Produkt-ID wurde erfolgreich getestet. `faceout` ist für diesen geprüften Stock-Aufruf nicht erforderlich; der Standardchecker behält den beobachteten Leerstring bei.
6. Die Camisole-Collection-ID wurde ohne neuen Browserlauf über das schon beobachtete Feld `outfits` ermittelt. Die bestätigte öffentliche KIC für Weiß ist `KIC_339-6340-00307-101`:

```graphql
query DiagnosticOutfits {
  outfits(kicId: "KIC_339-6340-00307-101") {
    products { productId collectionId kicId }
  }
}
```

Diese POST-Query lieferte sechs übereinstimmende Produktrecords für 63617331 mit `collectionId=706282`. Damit konnte dieselbe Collection-Stock-Abfrage für Camisole ausgeführt werden. Ein vorheriger Persisted-Query-GET lieferte eine leere Antwort und wurde nicht als Erfolg gewertet.

Die genannten Marktparameter wurden beibehalten, um den deutschen Shop zu prüfen. Die Erforderlichkeit jedes einzelnen URL-Parameters wurde nicht isoliert getestet. Eine einmalige Schema-Introspection lieferte HTTP 400; sie wurde nicht umgangen. Die erfolgreich verwendeten Felder stammen aus tatsächlichen Produktantworten. Hintergrund zum Schema-Verfahren: [offizielle GraphQL-Dokumentation](https://graphql.org/learn/introspection/).

## Browser- und Cookie-Vergleich

Der Vergleichslauf vom 09.10.2026, 13:07:50–13:08:49 Uhr Europe/Berlin, zeigte:

- Browser: Henley Helles Pink / XS und S jeweils ausverkauft, exakte SKUs bestätigt.
- Normale Python-HTTP-Anfrage mit Browser-Headern, **ohne Cookies**: einmal vollständiges Henley-HTML, gleiche Bestandswerte.
- Dieselbe Produktseite mit übernommenen Sitzungscookies: Schutzseite. Wiederholung wurde ausgelassen.
- Unabhängige Produktseitenanfragen vom NAS-Host: weiterhin Schutzseiten. Die einmalige HTML-Erreichbarkeit ist daher nicht stabil genug als Lösung.

**Der Fortschritt ist der explizite GraphQL-POST**, nicht ein behaupteter dauerhafter Erfolg beim HTTP-HTML-Abruf. Übertragene Browsercookies blieben nur im Arbeitsspeicher und wurden nicht protokolliert oder gespeichert.

## Wiederholbarkeit und Cache-Grenzen

Die erfolgreiche Henley-API wurde mehrfach auf dem NAS-Host abgerufen, darunter 13:11:25, 13:15:42 und 13:16:12 Uhr Europe/Berlin. Die Bestands-SKUs stimmten jeweils überein. Der Lauf um 13:16:12 meldete `Age: 29`; mindestens eine Antwort kam also aus einem Cache. Die gemeinsamen Aufrufe ab 13:20:29 lieferten für beide Produkte HTTP 200 und `Cache-Control: max-age=0, no-store`.

Der gemeinsame Wiederholungslauf um **13:22:30 Uhr Europe/Berlin** lieferte erneut für beide Produkte dieselben exakten SKUs und Statuswerte. Beide Antworten meldeten zugleich **`Age: 120`** und `Cache-Control: max-age=0, no-store`. Deshalb ist ausdrücklich keine frische Backend-Lagerabfrage bei jedem Aufruf bewiesen; eine vorgelagerte Cache-Schicht kann die Daten trotz der ausgelieferten Cache-Control-Angabe wiederverwenden.

Kurzfristige Wiederholbarkeit ist belegt. Langfristige Erreichbarkeit, Bestandsänderungen und die interne Aktualität upstreamseitiger Lager-/Produktcaches sind noch nicht nachgewiesen. Deshalb weiterhin Fehler und unvollständige Daten als nicht prüfbar behandeln; keine Kaufgarantie aus einer Menge ableiten.

## Eigenständiger Checker und Zustandsregeln

`http_stock_check.py` ist ein separates Diagnoseskript. Zusammen mit `session_http_diagnostic.py` und `diagnose_availability.py` benötigt es für diesen Modus nur die Python-Standardbibliothek; Playwright wird nicht importiert oder gestartet.

```sh
cd /volume1/docker/hollister/diagnostics-63617320
python3 http_stock_check.py --output /tmp/hollister-http-stock.json
```

Optional `--product henley` oder `--product camisole`; Standard ist beide. Keine Telegram-Nachricht, kein Monitorstart, keine Konfigurationsänderung.

Statusregeln: eindeutige richtige Farb-/Größen-SKU, `Available` mit positiver ganzzahliger Menge ergibt verfügbar; `Unavailable` mit 0 ergibt ausverkauft. Falsche oder neue unbestätigte SKU, fehlende Größe, mehrdeutige Records, Widerspruch, GraphQL-Fehler trotz Teilantwort, HTTP-Fehler, Schutzseite oder Größenlimit ergeben nicht prüfbar. Mengen als Boolean werden nicht akzeptiert.

## Empfehlung und unveränderter Betrieb

**Eine HTTP-Lösung ist jetzt für beide Zielvarianten technisch nachgewiesen.** Eine produktive Umstellung wurde nicht vorgenommen. Empfohlen ist zunächst ein gesondert freizugebender Vergleichsbetrieb über mehrere reguläre Monitorzyklen, mit konservativer Fehlerbehandlung, respektiertem Abfrageintervall und Abgleich bei einer echten Bestandsänderung. Browser-Fallback wäre optional; er würde die Zahl zusätzlich ausgelöster Seitenaufrufe erhöhen und sollte gesondert entschieden werden.

Der originale Browsermonitor wurde nach dem Diagnosejob wieder gestartet. Die danach ausgeführten API-Anfragen liefen unabhängig davon über SSH auf dem NAS-Host, ohne weiteren Containerstopp oder Browserneustart. Produktionsdateien sind unverändert. Geheimnisse, Rohbodys und Authentifizierung werden nicht ausgegeben. Der ursprünglich nach 63617320 benannte Diagnoseordner bleibt lediglich der Ablageort.

32 relevante lokale Tests bestanden, einschließlich exakter API-SKU-Zuordnung, falscher Farbe/SKU, fehlender Größe, GraphQL-Teilantwortfehler und ungültiger Mengen. Auf der NAS liegen `http_stock_check.py`, `both-api-confirmation-1.json`, `both-api-confirmation-2.json` und die zugehörigen Diagnosemodule. Ein neuer API-Abruf benötigt keine DSM-root-Aufgabe und keinen Monitorstopp.
