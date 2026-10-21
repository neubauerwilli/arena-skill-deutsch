#!/usr/bin/env python3
"""Arena (Willis Fassung): Buchführung für das K.-o.-Turnier.

Nur Standardbibliothek. Der Zustand liegt in .arena/<lauf>/arena.json im aktuellen Ordner.

    python3 bracket.py plan --agents 16
    python3 bracket.py init --agents 16 --seed 7 --task-file .arena/task.md
    python3 bracket.py next
    python3 bracket.py status
    python3 bracket.py winner

Ablauf: Jeder Teilnehmer bekommt dieselbe Aufgabe und eine andere Strategiekarte und schreibt eine Lösung.
Dann spielen jeweils zwei Lösungen ein Duell: Ein Richter greift beide an, wertet sie nach rubric.md,
der Verlierer fliegt raus. Bei ungerader Zahl gibt es ein Freilos.
Aufrufe insgesamt: N Teilnehmer plus N minus 1 Duelle.
"""
import argparse
import itertools
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WAVE = 10
ROOT = ".arena"


def wr(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def rd(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def rounds_for(n):
    r, a = 0, n
    while a > 1:
        a = (a + 1) // 2
        r += 1
    return r


def plan_rows(n):
    rows, alive, r = [], n, 0
    while alive > 1:
        r += 1
        matches = alive // 2
        rows.append((r, alive, matches, "ja" if alive % 2 else "-", matches))
        alive = matches + alive % 2
    return rows


def cmd_plan(args):
    n = args.agents
    rows = plan_rows(n)
    calls = n + sum(r[4] for r in rows)
    waves = math.ceil(n / WAVE) + sum(math.ceil(r[4] / WAVE) for r in rows)
    print(f"{'Runde':>7} {'am Leben':>9} {'Duelle':>7} {'Freilos':>8} {'Aufrufe':>8}")
    print(f"{'Start':>7} {n:>9} {'-':>7} {'-':>8} {n:>8}")
    for r, alive, m, bye, c in rows:
        print(f"{r:>7} {alive:>9} {m:>7} {bye:>8} {c:>8}")
    print(f"Gesamt: {calls} Sub-Agent-Aufrufe in {waves} Wellen zu je {WAVE}, {rounds_for(n)} Runden.")


def deal_cards(n, rng):
    data = json.loads(rd(os.path.join(HERE, "strategies.json")))
    combos = list(itertools.product(data["reasoning"], data["workflow"], data["strategy"]))
    if n > len(combos):
        sys.exit(f"Es gibt nur {len(combos)} verschiedene Karten, du willst {n} Teilnehmer.")
    rng.shuffle(combos)
    cards = {}
    for i in range(n):
        d, w, s = combos[i]
        cards[f"a{i + 1:03d}"] = {"denkweise": d, "ablauf": w, "strategie": s}
    return cards


def paths(state):
    run = state["run"]
    return {
        "task": os.path.join(run, "task.md"),
        "solutions": os.path.join(run, "solutions"),
        "prompts": os.path.join(run, "prompts"),
        "verdicts": os.path.join(run, "verdicts"),
    }


def save(state):
    wr(os.path.join(state["run"], "arena.json"), json.dumps(state, ensure_ascii=False, indent=1))


def load():
    latest = os.path.join(ROOT, "LATEST")
    if not os.path.exists(latest):
        sys.exit("Kein Lauf gefunden. Zuerst: init")
    run = rd(latest).strip()
    return json.loads(rd(os.path.join(run, "arena.json")))


def spawn_prompt(state, aid):
    p = paths(state)
    c = state["cards"][aid]
    out = os.path.abspath(os.path.join(p["solutions"], aid + ".md"))
    return (
        f"# Du bist Teilnehmer {aid} in einem Turnier\n\n"
        f"Lies die Aufgabe in `{os.path.abspath(p['task'])}`. Das ist alles, was du über sie weißt.\n\n"
        f"Deine Karte (so greifst du die Aufgabe an):\n"
        f"- Denkweise, {c['denkweise']['name']}: {c['denkweise']['text']}\n"
        f"- Ablauf, {c['ablauf']['name']}: {c['ablauf']['text']}\n"
        f"- Strategie, {c['strategie']['name']}: {c['strategie']['text']}\n\n"
        f"Löse die Aufgabe nach deiner Karte, so gut du kannst. Schreibe nur die fertige Lösung in `{out}`, "
        f"ohne Erklärung deiner Karte. Ändere keine anderen Dateien.\n"
        f"Antworte danach mit genau einer Zeile: FERTIG {aid}\n"
    )


def duel_prompt(state, rnd, mid, a, b):
    p = paths(state)
    sa = os.path.abspath(os.path.join(p["solutions"], a + ".md"))
    sb = os.path.abspath(os.path.join(p["solutions"], b + ".md"))
    out = os.path.abspath(os.path.join(p["verdicts"], f"r{rnd}-{mid}.json"))
    rub = os.path.join(HERE, "rubric.md")
    return (
        f"# Richter im Duell {mid}, Runde {rnd}\n\n"
        f"Aufgabe: `{os.path.abspath(p['task'])}`\n"
        f"Lösung {a}: `{sa}`\n"
        f"Lösung {b}: `{sb}`\n"
        f"Wertung: `{rub}` (lies sie ganz)\n\n"
        f"1. Lies die Aufgabe und beide Lösungen. Du kennst die Strategiekarten nicht und sollst sie nicht erraten.\n"
        f"2. Greife jede Lösung an: bis zu fünf Angriffe je Lösung, jeder mit der genauen Stelle und dem Beleg, "
        f"markiert als FATAL, MAJOR oder MINOR. Prüfe jeden Angriff selbst nach.\n"
        f"3. Bewerte beide Lösungen nach der Wertung, je Kriterium 0 bis 10, und rechne die Gesamtpunkte aus.\n"
        f"4. Schreibe als Ergebnis genau eine JSON-Datei nach `{out}` in diesem Format:\n"
        f'{{"scores": {{"{a}": 0, "{b}": 0}}, "fatal": [], "winner": "{a}", "reason": "ein Satz"}}\n'
        f"   `fatal` enthält nur die Nummern von Lösungen mit einem geprüften fatalen Fehler. `winner` ist {a} oder {b}, "
        f"bei Gleichstand wähle die Lösung, die du dem Nutzer geben würdest.\n"
        f"5. Antworte danach mit genau einer Zeile: FERTIG {mid}\n"
        f"Verändere keine anderen Dateien.\n"
    )


def make_pairs(state):
    """Paart die Überlebenden. Ungerade Zahl: ein Freilos an den mit den wenigsten Freilosen."""
    rng = random.Random(f"{state['seed']}-{state['round']}")
    alive = sorted(state["alive"])
    rng.shuffle(alive)
    bye = None
    if len(alive) % 2:
        fewest = min(state["byes"].get(a, 0) for a in alive)
        cand = [a for a in alive if state["byes"].get(a, 0) == fewest]
        bye = cand[0]
        state["byes"][bye] = state["byes"].get(bye, 0) + 1
        alive.remove(bye)
    pairs = []
    pool = alive[:]
    while pool:
        a = pool.pop(0)
        pick = None
        for i, b in enumerate(pool):
            if state["cards"][a]["denkweise"]["id"] != state["cards"][b]["denkweise"]["id"]:
                pick = i
                break
        b = pool.pop(pick if pick is not None else 0)
        pairs.append([a, b])
    state["pairs"] = pairs
    state["bye"] = bye


def write_duel_prompts(state):
    p = paths(state)
    os.makedirs(p["verdicts"], exist_ok=True)
    for i, (a, b) in enumerate(state["pairs"], 1):
        mid = f"m{i:02d}"
        wr(os.path.join(p["prompts"], f"r{state['round']}-{mid}.md"), duel_prompt(state, state["round"], mid, a, b))


def decide(verdict, a, b):
    scores = verdict["scores"]
    fatal = set(verdict.get("fatal", []))
    if (a in fatal) != (b in fatal):
        return b if a in fatal else a
    if scores[a] != scores[b]:
        return a if scores[a] > scores[b] else b
    w = verdict.get("winner")
    if w not in (a, b):
        raise ValueError(f"winner {w} gehört nicht zum Duell {a} gegen {b}")
    return w


def read_verdicts(state):
    p = paths(state)
    got, missing = {}, []
    for i, (a, b) in enumerate(state["pairs"], 1):
        mid = f"m{i:02d}"
        f = os.path.join(p["verdicts"], f"r{state['round']}-{mid}.json")
        if not os.path.exists(f):
            missing.append((mid, a, b))
            continue
        try:
            v = json.loads(rd(f))
            got[mid] = (decide(v, a, b), v.get("reason", ""))
        except (ValueError, KeyError, json.JSONDecodeError):
            missing.append((mid, a, b))
    return got, missing


def waves(items, size=WAVE):
    return [items[i:i + size] for i in range(0, len(items), size)]


def cmd_init(args):
    n = args.agents
    if n < 2:
        sys.exit("Mindestens 2 Teilnehmer.")
    seed = args.seed if args.seed is not None else random.randrange(1, 10 ** 6)
    rng = random.Random(seed)
    run = os.path.join(ROOT, f"lauf-{time.strftime('%Y%m%d-%H%M%S')}-s{seed}")
    os.makedirs(os.path.join(run, "solutions"))
    os.makedirs(os.path.join(run, "prompts"))
    os.makedirs(os.path.join(run, "verdicts"))
    task = rd(args.task_file)
    wr(os.path.join(run, "task.md"), task)
    state = {"run": run, "seed": seed, "agents": n, "round": 0, "phase": "spawn",
             "cards": deal_cards(n, rng), "alive": [], "pairs": [], "bye": None, "byes": {},
             "history": [], "eliminated": {}}
    state["alive"] = sorted(state["cards"])
    for aid in state["cards"]:
        wr(os.path.join(run, "prompts", f"spawn-{aid}.md"), spawn_prompt(state, aid))
    save(state)
    wr(os.path.join(ROOT, "LATEST"), run)
    print(f"Lauf {run} angelegt: {n} Teilnehmer, Seed {seed}.")
    print("Weiter mit: next")


def job_lines(state, kind, jobs):
    p = paths(state)
    for wi, w in enumerate(waves(jobs), 1):
        print(f"Welle {wi}:")
        for j in w:
            print(f"  {j}  ->  {os.path.abspath(os.path.join(p['prompts'], kind + j + '.md'))}")


def cmd_next(args):
    state = load()
    p = paths(state)
    if state["phase"] == "spawn":
        missing = [a for a in sorted(state["cards"])
                   if not os.path.exists(os.path.join(p["solutions"], a + ".md"))]
        if missing:
            print(f"PHASE spawn: {len(missing)} Lösungen fehlen. Starte je Welle höchstens {WAVE} Sub-Agents, "
                  f"jeder liest sein Briefing und schreibt seine Lösung:")
            job_lines(state, "spawn-", missing)
            return
        state["round"] = 1
        make_pairs(state)
        state["phase"] = "duel"
        write_duel_prompts(state)
        save(state)
        print("Alle Lösungen sind da. Runde 1 beginnt.")
    if state["phase"] == "duel":
        got, missing = read_verdicts(state)
        if missing:
            ids = [m[0] for m in missing]
            print(f"PHASE duel, Runde {state['round']}: {len(ids)} Duelle offen (Freilos: {state['bye'] or 'keins'}). "
                  f"Starte je Welle höchstens {WAVE} Richter:")
            job_lines(state, f"r{state['round']}-", ids)
            return
        survivors = []
        for i, (a, b) in enumerate(state["pairs"], 1):
            w, reason = got[f"m{i:02d}"]
            loser = b if w == a else a
            state["eliminated"][loser] = state["round"]
            state["history"].append({"runde": state["round"], "duell": f"m{i:02d}", "sieger": w, "verlierer": loser, "grund": reason})
            survivors.append(w)
        if state["bye"]:
            survivors.append(state["bye"])
        state["alive"] = sorted(survivors)
        print(f"Runde {state['round']} fertig: {len(state['alive'])} von {state['agents']} übrig.")
        if len(state["alive"]) == 1:
            state["phase"] = "done"
            save(state)
            print("FERTIG. Weiter mit: winner")
            return
        state["round"] += 1
        make_pairs(state)
        write_duel_prompts(state)
        save(state)
        print(f"Runde {state['round']} beginnt. Noch einmal: next")
        return
    if state["phase"] == "done":
        print("FERTIG. Weiter mit: winner")


def cmd_status(args):
    s = load()
    print(f"Phase {s['phase']}, Runde {s['round']}, am Leben {len(s['alive'])} von {s['agents']}")
    for rnd in sorted(set(s["eliminated"].values())):
        out = [a for a, r in s["eliminated"].items() if r == rnd]
        print(f"  Runde {rnd}: raus {len(out)}")


def cmd_winner(args):
    s = load()
    if s["phase"] != "done":
        sys.exit("Das Turnier läuft noch. Zuerst: next")
    w = s["alive"][0]
    c = s["cards"][w]
    path = os.path.abspath(os.path.join(paths(s)["solutions"], w + ".md"))
    print(f"Sieger: {w} nach {s['round']} Runden")
    print(f"Karte: {c['denkweise']['name']} / {c['ablauf']['name']} / {c['strategie']['name']}")
    print(f"Lösung: {path}")
    print("Gewonnene Duelle:")
    for h in s["history"]:
        if h["sieger"] == w:
            print(f"  Runde {h['runde']}: {h['grund']}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bracket.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("plan"); a.add_argument("--agents", type=int, required=True); a.set_defaults(f=cmd_plan)
    a = sub.add_parser("init"); a.add_argument("--agents", type=int, required=True)
    a.add_argument("--seed", type=int); a.add_argument("--task-file", required=True); a.set_defaults(f=cmd_init)
    a = sub.add_parser("next"); a.set_defaults(f=cmd_next)
    a = sub.add_parser("status"); a.set_defaults(f=cmd_status)
    a = sub.add_parser("winner"); a.set_defaults(f=cmd_winner)
    args = ap.parse_args(argv)
    args.f(args)


if __name__ == "__main__":
    main()
