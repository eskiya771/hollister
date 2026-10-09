# Implementierungsstand

Die verbindliche aktuelle Funktionsbeschreibung, Testnachweise, Einschränkungen und Synology-Anleitung stehen in [README.md](../README.md).

Die frühere Planung, nur Zustandswechsel zu melden, ist durch den aktuellen Auftrag ersetzt: sofortige erste Bestandsabfrage und danach bei jedem 900-Sekunden-Durchlauf eine Meldung, auch bei unverändertem oder unbekanntem Status.

Die lokale Chromium-Laufzeit ist inzwischen erfolgreich geprüft. Der aktuelle externe Blocker ist eine Hollister-Client-Challenge, kein lokaler Socket-Fehler. Eine erfolgreich arbeitende Bestandsüberwachung auf der NAS ist noch nicht bestätigt.
