import contextlib
import io
import json
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "arena"))
import bracket  # noqa: E402


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        bracket.main(argv)
    return buf.getvalue()


class Tournament:
    """Spielt ein ganzes Turnier mit Zufallssiegern über die Kommandozeile durch."""

    def __init__(self, n, seed=1, winner_rule=None):
        self.n = n
        self.dir = tempfile.mkdtemp()
        self.old = os.getcwd()
        os.chdir(self.dir)
        bracket.wr("task.md", "Aufgabe: Schreibe einen Satz.")
        run(["init", "--agents", str(n), "--seed", str(seed), "--task-file", "task.md"])
        self.rng = random.Random(seed)
        self.rule = winner_rule

    def close(self):
        os.chdir(self.old)

    def state(self):
        return bracket.load()

    def play(self):
        calls = 0
        for _ in range(500):
            out = run(["next"])
            s = self.state()
            p = bracket.paths(s)
            if s["phase"] == "spawn":
                for a in s["cards"]:
                    f = os.path.join(p["solutions"], a + ".md")
                    if not os.path.exists(f):
                        bracket.wr(f, "Lösung " + a)
                        calls += 1
            elif s["phase"] == "duel":
                for i, (a, b) in enumerate(s["pairs"], 1):
                    f = os.path.join(p["verdicts"], f"r{s['round']}-m{i:02d}.json")
                    if os.path.exists(f):
                        continue
                    w = self.rule(a, b) if self.rule else self.rng.choice([a, b])
                    v = {"scores": {a: 70 if w == a else 60, b: 70 if w == b else 60},
                         "fatal": [], "winner": w, "reason": f"{w} gewinnt"}
                    bracket.wr(f, json.dumps(v))
                    calls += 1
            elif s["phase"] == "done":
                return calls
        raise AssertionError("Turnier endet nicht")


class BracketTests(unittest.TestCase):
    def check(self, n):
        t = Tournament(n)
        try:
            calls = t.play()
            s = t.state()
            self.assertEqual(len(s["alive"]), 1)
            self.assertEqual(calls, n + (n - 1))
            self.assertEqual(s["round"], bracket.rounds_for(n))
            self.assertEqual(len(s["eliminated"]), n - 1)
            out = run(["winner"])
            self.assertIn("Sieger:", out)
        finally:
            t.close()

    def test_zwei(self):
        self.check(2)

    def test_sieben(self):
        self.check(7)

    def test_sechzehn(self):
        self.check(16)

    def test_hundert(self):
        self.check(100)

    def test_karten_sind_alle_verschieden(self):
        rng = random.Random(3)
        cards = bracket.deal_cards(100, rng)
        keys = {(c["denkweise"]["id"], c["ablauf"]["id"], c["strategie"]["id"]) for c in cards.values()}
        self.assertEqual(len(keys), 100)

    def test_zu_viele_teilnehmer(self):
        with self.assertRaises(SystemExit):
            bracket.deal_cards(289, random.Random(1))

    def test_gleiche_seed_gleiche_karten(self):
        a = bracket.deal_cards(16, random.Random(5))
        b = bracket.deal_cards(16, random.Random(5))
        self.assertEqual(a, b)

    def test_freilos_wird_verteilt(self):
        t = Tournament(7)
        try:
            t.play()
            byes = t.state()["byes"]
            self.assertTrue(all(v <= 2 for v in byes.values()))
        finally:
            t.close()

    def test_fatal_schlaegt_punkte(self):
        a, b = "a001", "a002"
        v = {"scores": {a: 90, b: 40}, "fatal": [a], "winner": a, "reason": "x"}
        self.assertEqual(bracket.decide(v, a, b), b)

    def test_gleichstand_nimmt_winner(self):
        a, b = "a001", "a002"
        v = {"scores": {a: 50, b: 50}, "fatal": [], "winner": b, "reason": "x"}
        self.assertEqual(bracket.decide(v, a, b), b)

    def test_plan_zahlen(self):
        out = run(["plan", "--agents", "16"])
        self.assertIn("31 Sub-Agent-Aufrufe", out)
        out = run(["plan", "--agents", "100"])
        self.assertIn("199 Sub-Agent-Aufrufe", out)


if __name__ == "__main__":
    unittest.main()
