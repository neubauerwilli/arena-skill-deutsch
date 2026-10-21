# Der Arena-Skill

Wenn Claude dir schlechte Antworten gibt, lass hundert Versionen von ihm gegeneinander kämpfen. Ein Claude-Skill, kostenlos, MIT, ohne Anmeldung, ohne API-Schlüssel, nichts zu verbinden.

Du nutzt ihn, wenn dir eine Antwort von Claude nicht reicht. Statt dieselbe Frage immer wieder zu stellen, startet `/arena` viele Sub-Agents und gibt jedem dieselbe Aufgabe, Wort für Wort. Jeder bekommt eine andere Strategiekarte, also eine andere Denkweise, einen anderen Ablauf und eine andere Strategie, und greift die Aufgabe deshalb anders an. Dann spielen je zwei Lösungen ein Duell: Ein Richter greift beide an, wertet sie nach einer festen Rubrik, und der Verlierer fliegt raus. Aus 16 werden 8, dann 4, 2, 1. Bei 100 sind es 100, 50, 25, 13, 7, 4, 2, 1.

Zurück kommt die eine Lösung, die alle Duelle überstanden hat, dazu die Gründe, warum sie gewonnen hat.

**Er fasst deine Dateien nie an.** Alle Sub-Agents schreiben nur in den Ordner `.arena/`. Was am Ende mit der Siegerlösung passiert, entscheidest du.

Das ist eine eigene, schlankere deutsche Umsetzung. Die Idee und das Grundkonzept stammen von [Jakeschincariol/arena-skill](https://github.com/Jakeschincariol/arena-skill) (MIT). Der Unterschied: Hier greift der Richter beide Lösungen selbst an und wertet sie in einem einzigen Aufruf. Das braucht etwa ein Drittel der Aufrufe.

## Einrichten

Der Skill braucht [Claude Code](https://code.claude.com/docs/en/overview), weil er Sub-Agents startet, und Python 3.8 oder neuer. Nichts per pip installieren.

Als Plugin: Sende diese zwei Befehle einzeln in Claude Code, prüfe die Quelle und bestätige den angezeigten Installationsstatus.

```
/plugin marketplace add neubauerwilli/arena-skill-deutsch
/plugin install arena-skill-deutsch@arena-skill-deutsch
```

Als Plugin bekommt der Skill einen Namensraum und heißt dann `/arena-skill-deutsch:arena`. Willst du einfach `/arena`, kopiere den Ordner:

```bash
git clone https://github.com/neubauerwilli/arena-skill-deutsch.git
mkdir -p ~/.claude/skills
cp -r arena-skill-deutsch/skills/arena ~/.claude/skills/
```

Unter Windows PowerShell:

```powershell
git clone https://github.com/neubauerwilli/arena-skill-deutsch.git
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE/.claude/skills" | Out-Null
Copy-Item -Path 'arena-skill-deutsch/skills/arena' -Destination "$env:USERPROFILE/.claude/skills" -Recurse
```

Starte die Sitzung bei Bedarf neu. Unter `/` sollte jetzt `/arena` erscheinen. Ein GitHub-Link im normalen Webchat ist kein Nachweis einer Installation: Das Turnier läuft nur in Claude Code, weil dort die Sub-Agents und das Werkzeug `bracket.py` laufen.

## Benutzen

```
/arena
/arena --quick schreibe die Überschrift für unsere Preisseite
/arena --agents 32 behebe den wackeligen Test in tests/test_api.py
/arena --seed 7 plane meine Launch-Woche, ich habe 6 Stunden am Tag
```

Ohne Text nimmt `/arena` deine letzte Anfrage als Aufgabe und die Antwort, die dir nicht gefallen hat, als die, die geschlagen werden soll.

| Schalter | Was er macht |
|---|---|
| `--agents N` | N Teilnehmer, höchstens 288. Üblich für die wichtige Aufgabe: 100. |
| `--quick` | 16 Teilnehmer, der Alltagswert. Auch der Standard, wenn nichts angegeben ist. |
| `--seed S` | Gleiche Seed, gleiche Karten, gleiche Paarungen. Ohne Angabe zufällig und gespeichert. |

## So funktioniert es

1. **Aufgabe schreiben.** Sub-Agents sehen dein Gespräch nicht. Claude schreibt darum eine Aufgabendatei, die für sich allein verständlich ist. Sie ist alles, was alle Teilnehmer und Richter über die Aufgabe wissen.
2. **Austeilen.** Jeder Teilnehmer bekommt dieselbe Aufgabe und eine eigene Karte. Es gibt 8 Denkweisen, 6 Abläufe und 6 Strategien, also 288 verschiedene Karten, keine wird doppelt vergeben. Die Karten stehen in `skills/arena/strategies.json`.
3. **Lösen.** Jeder schreibt seine Lösung in eine Datei und meldet sich mit einer Zeile.
4. **Duell.** Je zwei Lösungen treffen sich. Ein Richter, der die Karten nicht kennt, greift jede Lösung an (FATAL, MAJOR oder MINOR, mit Beleg), bewertet beide nach der [Rubrik](skills/arena/rubric.md) und schreibt das Ergebnis. `bracket.py` rechnet: Die höhere Punktzahl kommt weiter, eine Lösung mit einem geprüften fatalen Fehler schlägt nie eine ohne.
5. **Weiter.** Die Überlebenden spielen die nächste Runde. Bei ungerader Zahl gibt es ein Freilos, immer an den mit den wenigsten.
6. **Ergebnis.** Eine Lösung bleibt übrig. Du bekommst sie, die Gründe aus ihren Duellen und ihre Karte.

Das ganze Turnier steht in einer JSON-Datei, die `bracket.py` führt. Claude liest nie die hunderten Lösungsdateien, sondern nur Quittungen. Wird das Gespräch unterwegs gekürzt, macht `bracket.py next` an der richtigen Stelle weiter.

## Was es kostet

Der Skill ist kostenlos, die Tokens sind deine. Jeder Aufruf liest die Aufgabe und eine oder zwei Lösungen, die Rechnung wächst also mit der Aufgabe.

| Teilnehmer | Runden | Sub-Agent-Aufrufe |
|---|---|---|
| 100 | 7 | 199 |
| 64 | 6 | 127 |
| 32 | 5 | 63 |
| 16, `--quick` | 4 | 31 |
| 8 | 3 | 15 |

Die Zahlen druckt `python3 skills/arena/bracket.py plan --agents N` jederzeit. Nimm `--quick` für Alltägliches und die große Arena für die Antwort, auf die es ankommt.

## Die Werkzeuge

`bracket.py` ist reine Standardbibliothek und der Grund, warum die Spielleitung nie den Faden verliert.

```bash
python3 bracket.py plan --agents 100                       # Runden und Aufrufe, schreibt nichts
python3 bracket.py init --agents 16 --seed 7 --task-file task.md
python3 bracket.py next                                    # was jetzt zu tun ist, mit den Pfaden
python3 bracket.py status                                  # wer lebt, wer ist raus
python3 bracket.py winner                                  # Sieger, Karte, Pfad der Lösung
```

Unter Windows heißt der Aufruf oft `py` statt `python3`.

Die Tests spielen ganze Turniere mit zufälligen Siegern über die Kommandozeile durch (2, 7, 16 und 100 Teilnehmer) und prüfen, dass genau einer übrig bleibt, dass die Zahl der Aufrufe stimmt und dass alle Karten verschieden sind:

```bash
python3 -m unittest discover -s tests -v
```

## Das Kleingedruckte

**„Hundert Versionen von Claude“ heißt hundert Sub-Agents desselben Modells.** Nicht hundert verschiedene Modelle. Verschieden macht sie nur die Karte.

**„Die beste Antwort“ heißt: die, die jedes Duell überstanden hat.** Die Richter sind auch Claude und bewerten nach einer Rubrik, die du lesen und ändern kannst. Du bekommst die stärkste Antwort, die dieses Turnier gefunden hat, keinen Beweis, dass sie stimmt. Darum zeigt der Skill dir die Gründe.

**Hundert Teilnehmer laufen nicht gleichzeitig.** Claude Code führt standardmäßig höchstens 10 Aufrufe gleichzeitig aus. Der Skill arbeitet deshalb in Wellen zu 10, die große Arena dauert entsprechend.

**Rechne mit Rückfragen.** Jeder Sub-Agent schreibt eine Datei in `.arena/`. Im Standardmodus fragt Claude Code bei jeder Datei nach. Empfehlenswert ist der Modus „Änderungen akzeptieren“ (Umschalt+Tab) für die Dauer des Laufs.

**Der Skill rettet keine schlechte Aufgabe.** Vage Aufgabe rein, hundert vage Lösungen raus.

**Stand dieser Fassung:** Die Turnierlogik ist mit 11 automatischen Tests geprüft. Ein vollständiger Lauf mit echten Sub-Agents ist hier noch nicht dokumentiert. Melde Fehler gern als Issue.

## Dateien

```
.claude-plugin/        Plugin und Marktplatz
skills/arena/
  SKILL.md             die Anleitung für Claude
  bracket.py           Buchführung, Paarungen, Auswertung
  strategies.json      die Strategiekarten
  rubric.md            die Wertung
tests/test_bracket.py
LICENSE                MIT
```

## Lizenz

MIT. Idee und Grundkonzept: Jake Schincariol, [Jakeschincariol/arena-skill](https://github.com/Jakeschincariol/arena-skill). Deutsche, schlankere Umsetzung: Willi Neubauer, [willineubauer.com](https://willineubauer.com).
