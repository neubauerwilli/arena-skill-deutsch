---
name: arena
description: "Lass viele Versionen von Claude gegeneinander kämpfen, bis nur die beste Antwort übrig bleibt. Startet N Sub-Agents (Standard 16, bis 100), gibt jedem dieselbe Aufgabe und eine andere Strategiekarte und spielt ein K.-o.-Turnier: Ein Richter greift je zwei Lösungen an, wertet sie nach einer Rubrik, der Verlierer fliegt raus. Nutze den Skill, wenn der Nutzer mit einer Antwort unzufrieden ist, „Arena“ sagt oder verlangt, dass mehrere Lösungen gegeneinander antreten."
argument-hint: "[--agents N | --quick] [--seed S] <Aufgabe>"
---

# Arena

Für den Fall, dass Claude schlechte Antworten gibt. Statt dieselbe Frage immer wieder zu stellen, bekommen N Sub-Agents
dieselbe Aufgabe, jeder mit einer anderen Strategiekarte, und spielen ein K.-o.-Turnier. Du bist die Spielleitung.
Du trittst nie selbst an und du wertest nie selbst.

Was der Nutzer nach `/arena` getippt hat: `$ARGUMENTS`
Ist das leer, nimm die Aufgabe aus dem Gespräch und die letzte Antwort darauf als die Antwort, die geschlagen werden soll.

## Das Werkzeug

Die ganze Buchführung läuft über `bracket.py` im Ordner dieses Skills:

```bash
python3 "${CLAUDE_SKILL_DIR}/bracket.py" <Befehl>
```

Unten steht `ARENA` für genau diesen Aufruf. Ist der Pfad nicht aufgelöst, nimm den „Base directory for this skill“,
den Claude Code oben ausgibt. Der Zustand liegt in `.arena/<Lauf>/arena.json` im aktuellen Ordner.

## Schritt 1: Größe festlegen

- `--quick` oder nichts angegeben: 16 Teilnehmer, der Alltagswert.
- `--agents N`: N Teilnehmer, höchstens 288 (so viele verschiedene Karten gibt es). Für die wichtige Aufgabe sind 100 üblich.
- `--seed S`: gleiche Karten und gleiche Paarungen. Ohne Angabe zufällig, der Wert wird gespeichert.

Rufe `ARENA plan --agents N` auf und nenne dem Nutzer in einer Zeile die Größe, zum Beispiel „16 Teilnehmer, 4 Runden,
31 Sub-Agent-Aufrufe“. Hat der Nutzer die Arena nicht selbst verlangt (er ist nur unzufrieden), frage einmal vorher
und biete an: `--quick` (16), die große Arena (100) oder ein normaler zweiter Versuch. Warte auf die Antwort.

Sub-Agents schreiben Dateien in `.arena/`. Empfiehl dem Nutzer vor dem Start den Modus „Änderungen akzeptieren“ (Shift+Tab),
sonst fragt Claude Code bei jeder Datei nach. Ändere seine Einstellungen nicht selbst.

## Schritt 2: Aufgabendatei schreiben

Das entscheidet das Ergebnis. **Sub-Agents sehen dieses Gespräch nicht.** Jeder Teilnehmer und jeder Richter kennt nur,
was in der Aufgabendatei steht. Schreibe `.arena/task.md` so, dass sie für sich allein verständlich ist:

- die Anfrage, möglichst in den Worten des Nutzers
- jede Anforderung und Vorgabe aus dem Gespräch: Zielgruppe, Länge, Format, Ton, Technik
- Kontext, den ein Fremder braucht: absolute Pfade wichtiger Dateien, eingefügte Daten, was das Produkt ist
- was „fertig“ bedeutet, wenn der Nutzer es gesagt hat
- falls es eine Antwort zu schlagen gibt: was dem Nutzer daran nicht gefallen hat, in seinen Worten

Füge keine Anforderungen hinzu, die der Nutzer nie genannt hat, und schreibe nicht deine eigene Lösung hinein.
Das würde alle Teilnehmer in dieselbe Richtung schieben und genau den Sinn der Arena zerstören.

## Schritt 3: Start

```bash
ARENA init --agents N --seed S --task-file .arena/task.md
```

`init` kopiert die Aufgabe, teilt jedem Teilnehmer eine andere Karte zu (keine Wiederholung) und schreibt alle Briefings.

## Schritt 4: Die Schleife

Steuere alles mit `ARENA next`. Es liest den Zustand von der Platte und sagt dir den nächsten Schritt.

Jede Phase mit Sub-Agents läuft gleich:

1. `ARENA next` listet die offenen Aufträge in Wellen zu höchstens 10 mit dem Pfad des Briefings.
2. Starte **eine Welle auf einmal**: In einer einzigen Nachricht ein Agent-Aufruf pro Auftrag der Welle.
   - `subagent_type`: `general-purpose`
   - `description`: `arena <Auftrag>`
   - `prompt`: `Lies <Pfad des Briefings> und befolge es genau. Es ist dein ganzer Auftrag.`
   - Wähle für die Sub-Agents das Modell, das der Nutzer verlangt hat. Ohne Wunsch nimm das Modell des Gesprächs.
   Warte, bis alle Antworten der Welle da sind, dann die nächste Welle.
3. Danach wieder `ARENA next`. Fehlt eine Ausgabe, listet es genau diese Aufträge erneut. Führe sie einmal neu aus.
   Scheitert ein Auftrag zweimal, entscheide ein Duell nie selbst: Ein Richter bekommt einen dritten, frischen Lauf.

Die Reihenfolge: zuerst die Lösungen aller Teilnehmer, dann Runde für Runde ein Duell je Paar. `next` wertet die
Urteile aus, wirft die Verlierer raus, paart die Überlebenden neu (bei ungerader Zahl gibt es ein Freilos) und meldet FERTIG.

Nach jeder Runde sagst du dem Nutzer eine Zeile, etwa „Runde 2 fertig: 8 von 16 übrig.“ Mehr nicht.
Füge nie Paarungen, Angriffe, Urteile oder Lösungen in den Chat ein.

## Schritt 5: Das Ergebnis

`ARENA winner` zeigt den Sieger, seine Karte, die Zahl der Runden und den Pfad seiner Lösung. Lies nur diese eine
Lösungsdatei. Gib dem Nutzer:

- die Siegerlösung
- die Runden, die sie überstanden hat, und die Gründe aus den gewonnenen Duellen
- die Karte, mit der sie entstanden ist
- einen Satz Ehrlichkeit: Das ist die stärkste Antwort, die dieses Turnier gefunden hat, kein Beweis, dass sie stimmt.

Gab es eine Antwort, die der Nutzer abgelehnt hat, lass sie am Ende von einem frischen Richter gegen den Sieger bewerten
(ohne zu verraten, welche welche ist) und sag ihm das Ergebnis, auch wenn die alte Antwort gewinnt.

## Grenzen

- Der Skill ändert nie die Dateien des Nutzers. Alles, was Teilnehmer schreiben, liegt in `.arena/`. Code kommt als Lösungstext
  zurück, einbauen entscheidet der Nutzer.
- 100 Sub-Agents verbrauchen viel Limit. Nimm `--quick` für Alltägliches und die große Arena für die Antwort, auf die es ankommt.
- Eine vage Aufgabe ergibt viele vage Lösungen. Der Skill rettet keine schlechte Aufgabe.
- „Beste Antwort“ heißt: die, die jedes Duell überstanden hat. Die Richter sind auch Claude und bewerten nach `rubric.md`,
  die du lesen und ändern kannst.
