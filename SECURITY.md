# Sicherheit

Postfach ist eine Mail-App: sie hält IMAP-Zugangsdaten und stellt fremdes,
ungeprüftes HTML dar. Sicherheitslücken sind hier also keine Kleinigkeit —
Meldungen sind ausdrücklich willkommen.

## Welche Versionen Fixes bekommen

Solange Postfach in der Beta ist: **nur die jeweils neueste Version.** Es gibt
keine Backports auf ältere Releases. Bitte prüfe vor einer Meldung im Dialog
**Über Postfach** (⌘K → „Über Postfach"), ob du die aktuelle Version hast.

## Wie du eine Lücke meldest

Nutze **GitHub Private Vulnerability Reporting**: Repository → Tab **Security** →
*Report a vulnerability*. Das ist der bevorzugte Weg, weil die Meldung dort
privat bleibt, bis ein Fix draußen ist.

**Bitte kein öffentliches Issue** für Sicherheitslücken — ein öffentliches Issue
erzählt die Lücke allen, die sie noch nicht kannten. Für normale Fehler ist der
Issue-Tracker richtig, für Lücken nicht.

Hilfreich in der Meldung: betroffene Version, was ein Angreifer damit erreichen
kann, und wenn möglich eine kurze Schritt-für-Schritt-Reproduktion. Bitte keine
echten Passwörter und keine privaten Mail-Inhalte mitschicken.

## Was du erwarten kannst

Postfach ist ein Hobby-Projekt einer einzelnen Person. Es gibt **keine
zugesicherte Reaktionszeit** und kein Bug-Bounty. Ich schaue mir jede Meldung an
und antworte, so schnell es privat geht — realistisch innerhalb einiger Tage,
in Urlaubszeiten später. Ernst gemeinte Meldungen bekommen im Changelog eine
Erwähnung, wenn du das möchtest.

## Sicherheitsmodell (was die App tut, damit du weißt, was ein Bug wäre)

- **Nur lokal erreichbar.** Der Server bindet auf `127.0.0.1:8722`. Zusätzlich
  prüft eine Middleware den `Host`-Header (nur localhost — Schutz gegen
  DNS-Rebinding) und lehnt Requests mit fremdem `Origin` ab (CSRF), damit keine
  Webseite im Browser deine lokale API benutzen kann.
- **Mail-HTML ist doppelt eingesperrt.** Serverseitig durch nh3/ammonia
  bereinigt (inklusive Bild-/Tracker-Blocking im Parser, nicht per Regex),
  danach in einem `<iframe sandbox>` **ohne `allow-scripts`** gerendert. Skripte
  aus einer Mail laufen nie.
- **Passwörter nur im macOS-Schlüsselbund.** Nie in `config.yaml`, nie im Log,
  nie im Suchindex; der 422-Handler redigiert Passwortfelder aus Fehlermeldungen.
- **KI standardmäßig lokal.** Emilia rechnet über Ollama auf deinem Mac; die KI
  darf klassifizieren und Entwürfe schreiben, aber **nie senden, verschieben
  oder löschen**. Cloud-KI ist ein ausdrückliches Opt-in und wird dann im Dialog
  *Über Postfach* mit aufgeführt.

Wenn du eine dieser vier Aussagen brechen kannst, ist das ein Sicherheitsbug —
bitte melden.
