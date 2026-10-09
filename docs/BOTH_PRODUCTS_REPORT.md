# Browserdiagnose beider Oberteile – 09.10.2026

> Neuer Stand: [HTTP_API_REPORT.md](HTTP_API_REPORT.md) bestätigt inzwischen direkte API-Abfragen für beide Oberteile, einschließlich aktueller Camisole-Daten. Die Challenge-Angaben unten gelten für diesen früheren Browserlauf.

Die gemeinsame Aufnahme lief am 09.10.2026 von 12:53:56 bis 12:54:57 Uhr Europe/Berlin. Originale Zeitstempel sind in UTC gespeichert. Beide Produkte wurden nacheinander im selben Diagnosebrowser mit dem vorhandenen persistenten Profil geprüft. Der Originalmonitor wurde vorübergehend gestoppt und anschließend unverändert wieder gestartet.

## Aktuelle Ergebnisse

| Produktseiten-ID | Farbe | Größe | interne Farb-Produkt-ID | shortSku | Bestand / Status | Ergebnis |
|---|---|---|---|---|---|---|
| 63757420, Henley | Helles Pink | XS | 63766393 | 673107742 | 0 / Unavailable | ausverkauft |
| 63757420, Henley | Helles Pink | S | 63766393 | 673107911 | 0 / Unavailable | ausverkauft |
| 63270319, Camisole | Weiß | XS | nicht neu bestätigt | nicht neu bestätigt | Schutzseite | nicht prüfbar |
| 63270319, Camisole | Weiß | S | nicht neu bestätigt | nicht neu bestätigt | Schutzseite | nicht prüfbar |
| 63270319, Camisole | Weiß | XXL | nicht neu bestätigt | nicht neu bestätigt | Schutzseite | nicht prüfbar |

„Helles Pink“ ist die ausdrücklich gewählte Shopfarbe für das vom Benutzer als hell rosa bezeichnete Henley. Farbüberschrift und gewählter Radiobutton wurden bestätigt. Die interne ID 63766393 stammt aus dessen Wert, nicht aus einer alten konfigurierten SKU. Die genaue SKU unterscheidet sich pro Größe.

## Henley-Datenquelle und Zuverlässigkeit

Die aktuellen XS-/S-Records standen bereits im **initialen HTML-Response**, unter `CACHE.ROOT_QUERY.*.collection.skus`:

```json
[
  {"productId":"63766393","shortSku":"673107742",
   "sizePrimary":"XS_p","sizeSecondary":null,
   "inventory":0,"inventoryStatus":"Unavailable"},
  {"productId":"63766393","shortSku":"673107911",
   "sizePrimary":"S_p","sizeSecondary":null,
   "inventory":0,"inventoryStatus":"Unavailable"}
]
```

Farb-/Größenauswahl und sichtbarer Bestandsstatus wurden jeweils über sechs Sekunden überprüft. Beide UI-Prüfungen lieferten durchgehend ausverkauft. Der Offline-Analyzer bestätigte die exakte Farb-ID, Größenkennung, eigene SKU und widerspruchsfreie Bestandswerte.

Die Aufnahme enthält 35 Requests und 35 Responses des Hollister-Hosts. Phasen: Laden 30, Zielfarbe wählen 3, alternative Farbe 1, zurück zur Zielfarbe 1. Bei XS-/S-Wechsel wurden keine weiteren Document-/Fetch-/XHR-Requests an `www.hollisterco.com` erfasst. Das stützt die Größenprüfung aus bereits geladenen Daten. Es gilt zum Messzeitpunkt; Bestandsaktualität über längere Zeit und Käufe wurden nicht geprüft.

## Camisole in diesem Lauf

Der Camisole-Aufruf folgte nach dem erfolgreichen Henley-Lauf. Es wurden 6 Requests und 6 Responses erfasst. Bereits die initiale Darstellung wurde als Challenge erkannt; keine Farb-ID oder Größen-SKU wurde neu bestätigt. Die Diagnose hat die Challenge nicht gelöst oder umgangen.

Die früher erfolgreich ermittelten Camisole-Daten stehen in [AVAILABILITY_REPORT.md](AVAILABILITY_REPORT.md). Dort waren Weiß / XS und S ausverkauft, XXL verfügbar. **Diese älteren Werte wurden nicht als neues Ergebnis übernommen.** Ein unbekanntes Ergebnis ist keine Ausverkauft-Meldung.

## HTTP und Empfehlung

Dieser gemeinsame Job führte ausschließlich Browserdiagnosen aus. Die vorausgegangenen cookie-freien HTTP-Tests für beide Produktseiten lieferten Schutzseiten statt Bestandsdaten. Es wurde keine funktionierende cookie-freie HTTP-Stock-API bestätigt und keine HTTP-Umstellung vorgenommen.

Für beide Oberteile ist das beobachtete Collection-Cache-Schema grundsätzlich eine geeignete Quelle für eine spätere Browserauswertung nach einer frischen Navigation. Solange Schutzseiten auftreten, muss der Adapter den jeweiligen Artikel unabhängig als nicht prüfbar behandeln. Eine produktive Implementierung oder Umstellung benötigt weiterhin Freigabe; sie war nicht Teil dieses Diagnosejobs.

## Betrieb und Artefakte

Der Job protokolliert den erfolgreichen Neustart des Originalcontainers und Exitcode 0. Dieser Exitcode belegt den technischen Abschluss des Jobs, **nicht die erfolgreiche Bestandsprüfung beider Artikel**: Die Camisole-Aufnahme enthält einen Challenge-Fehler. Produktiver Code und Konfiguration wurden nicht geändert; der temporäre Diagnosecontainer wurde entfernt.

NAS-Ordner: `/volume1/docker/hollister/diagnostics-63617320/`.

- `availability-both.json`: bereinigte gemeinsame Aufnahme mit separaten Produktreports und abgeleiteten Ergebnissen.
- `availability-both-summary.json`: kompakte Zusammenfassung einschließlich Fehlern und Zeitstempeln.
- `run_both_diagnostics.py`: nacheinander ausgeführte, voneinander getrennte Produktprüfungen im selben Browser.
- `job-status.log`: Abschluss- und Neustartnachweis.

Cookies, Authentifizierung, Roh-HTML, Headers und Rohresponsebodys sind nicht enthalten. Unbekannte Werte wurden ausgelassen. 24 relevante lokale Tests bestanden, einschließlich Produkt-/URL-Abgleich und der unabhängigen Henley-Farb-/Größenauswertung.
