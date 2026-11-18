"""Playtest log: one YAML per game in playtests/, aggregated by rule variant (format version + the flags under test)."""
from collections import Counter, defaultdict
from pathlib import Path

import yaml

DIR = Path(__file__).parent.parent / "playtests"


def load(d: Path | None = None) -> list[dict]:
    games = []
    for f in sorted((d or DIR).glob("*.yaml")):
        if f.name.startswith("_"):
            continue  # _template.yaml
        g = yaml.safe_load(f.read_text())
        if g["winner"] != "draw" and g["winner"] not in g["decks"]:
            raise ValueError(f"{f.name}: winner {g['winner']} is not one of the decks {g['decks']}")
        games.append(g)
    return games


def variant_key(g: dict) -> str:
    return f"v{g['format_version']} " + " ".join(f"{k}={v}" for k, v in sorted(g["variant"].items()))


def aggregate(games: list[dict]) -> list[dict]:
    by = defaultdict(list)
    for g in games:
        by[variant_key(g)].append(g)
    out = []
    for k, gs in sorted(by.items()):
        fp = [g for g in gs if g.get("first_player")]
        out.append({"variant": k, "games": len(gs), "draws": sum(g["winner"] == "draw" for g in gs),
                    "avg_turns": round(sum(g["turns"] for g in gs) / len(gs), 1),
                    "wins": dict(Counter(g["winner"] for g in gs if g["winner"] != "draw")),
                    "first_player_games": len(fp), "first_player_wins": sum(g["winner"] == g["first_player"] for g in fp)})
    return out


def report(d: Path | None = None) -> str:
    rows = aggregate(load(d))
    if not rows:
        return "no games logged yet (copy playtests/_template.yaml)"
    return "\n".join(f"{r['variant']}: {r['games']} games ({r['draws']} draws), avg {r['avg_turns']} turns, "
                     f"first player won {r['first_player_wins']}/{r['first_player_games']}, wins by deck {r['wins']}" for r in rows)
