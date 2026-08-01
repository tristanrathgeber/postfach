# Rückstand — was als Nächstes besser werden könnte

Diese Liste ist der Einstiegspunkt für die **wöchentliche automatische
Weiterentwicklung** (`.github/workflows/weekly-improve.yml`). Der Agent liest
sie, sucht sich Punkte heraus, entwickelt sie fertig und legt sie als
Entwurfs-PR ab. Erledigtes wird nach unten verschoben, nicht gelöscht — so
wiederholt sich nichts.

Du darfst hier jederzeit selbst Punkte eintragen oder streichen. Was oben
steht, wird bevorzugt angefasst.

## Offen

### Auslieferung & Betrieb

- **Testwerkzeug wandert ins Bundle.** `pytest`, `setuptools`, `pluggy`,
  `iniconfig`, `Pygments` und `packaging` landen im ausgelieferten
  `Postfach.app`, obwohl sie nur zum Testen gebraucht werden. Kein
  Lizenzproblem (alle MIT/BSD, in `THIRD-PARTY-LICENSES.md` erfasst), aber
  unnötiger Ballast im Download. Über `excludes` in `postfach.spec` entfernen —
  danach unbedingt prüfen, dass die App noch startet (der macOS-Job in der CI
  macht genau das).
- **Intel-Macs bleiben außen vor.** Der Release ist arm64-only. Ein
  `universal2`-Build oder ein zweiter Job wäre möglich; ehrlich abwägen, ob
  sich das für die Nutzerzahl lohnt.

### Qualität

- **Frontend-Tests decken vor allem Hilfsfunktionen ab.** Es fehlen Tests, die
  Komponenten wirklich rendern (React Testing Library) — etwa für die
  Anhang-Vorschau (Tastenabschirmung, Blättern) oder den Composer.
- **Kein Test für den Ollama-Einrichtungspfad Ende-zu-Ende.** Die Bausteine
  sind getestet, der Zusammenbau in `api.py` (`/ollama/install`) nicht.

### Funktionen

- **Termine-Übersicht.** Postfach erkennt bereits Termin-Daten in Mails
  (`extract.py`, Chips im Reader). Daraus ließe sich eine Ansicht „was steht
  an?" bauen — die Frage, an der die reine Chat-Suche scheitert.
- **Mehrsprachigkeit.** Oberfläche und Handbuch sind deutsch. Englisch würde
  die Reichweite deutlich erhöhen, ist aber ein großer, sorgfältiger Umbau
  (Textkatalog statt verstreuter Strings).

## Bewusst nicht geplant

- **Windows-Portierung** — separat bewertet (grob 2 Tage für „läuft", 3–6 Tage
  für Parität); die harten Punkte sind SmartScreen/Signatur und ein fehlendes
  Schlüsselbund-Äquivalent. Erst sinnvoll, wenn macOS rund läuft.
- **Signierung/Notarisierung** — braucht ein kostenpflichtiges
  Apple-Entwicklerkonto. Bewusste Entscheidung, nicht vergessen.

## Erledigt

- Sicherheit: Schutz gegen DNS-Rebinding (Host-/Origin-Prüfung)
- Kein Doppelversand mehr (zweiphasiger Versand, Backoff, Wiederholen)
- Live-Push auch für per Oberfläche angelegte Konten
- Anhang-Vorschau mit zuverlässigem Download
- Ollama richtet sich selbst ein
- Protokolldatei, Diagnose-Endpunkt, Fehlerfenster beim Start
- Nutzerdaten liegen außerhalb des Repos
- CI: Linting, macOS-Build mit Rauchtest, CodeQL, Dependabot, Doku-Prüfung
