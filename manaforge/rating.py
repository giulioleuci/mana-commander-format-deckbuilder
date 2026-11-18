"""Relative star rating from a heuristic score (no simulator): score -> quintile cut-offs from a forged calibration batch.

The scorer is pluggable: SCORERS maps a name to fn(deck, cfg) -> float. A simulator would register itself there."""
import json
import statistics
from bisect import bisect_right
from collections import Counter
from pathlib import Path

from . import cards, estimate, fmt, forge as forge_mod, tags, spellbook
from .decks import Deck

CUTOFFS = Path(__file__).parent / "CUTOFFS.json"
CALIBRATION_SEEDS = 1_000_000
COVER = {"draw": (9, 5), "removal": (9, 5), "landsearch": (8, 4), "wincon": (9, 3), "protection": (5, 2)}  # tag: (points, cards for full marks)


def local_bracket(deck: Deck) -> int:
    # ponytail: game changers only (Commander brackets: 0 -> Core, 1-3 -> Upgraded, 4+ -> Optimized); Spellbook sees combos and tutors
    gc = sum(c.game_changer for c, _ in deck.main)
    return 2 if gc == 0 else 3 if gc <= 3 else 4


def components(deck: Deck, cfg: dict | None = None) -> dict[str, float]:
    cfg = cfg or fmt.load()
    main = [c for c, _ in deck.main]
    cover = Counter(t for c in main for t in tags.tag(c) & COVER.keys())
    avg = sum(c.cmc for c in main) / len(main)
    p = statistics.mean(r["p_castable"] for r in estimate.curve(deck, cfg, turns=4))
    gc = sum(c.game_changer for c in main)
    bracket = deck.meta.get("bracket") or local_bracket(deck)
    return {"curve": 12.5 * max(0.0, 1 - abs(avg - 3.0) / 2) + 12.5 * p,
            "coverage": sum(w * min(cover[t] / need, 1) for t, (w, need) in COVER.items()),
            "game_changers": 15 * min(gc, 4) / 4,
            "bracket": 20 * (bracket - 1) / 4}


def heuristic(deck: Deck, cfg: dict | None = None) -> float:
    """0-100: curve 25, tag coverage 40, game changers 15, bracket 20. Higher = stronger, not 'better'."""
    return sum(components(deck, cfg).values())


SCORERS = {"heuristic": heuristic}


def stars(score: float, cutoffs: list[float]) -> int:
    return bisect_right(cutoffs, score) + 1


def calibrate(db, scorer: str = "heuristic", *, n: int = 50, use_spellbook: bool = False) -> list[float]:
    decks = forge_mod.forge_batch(range(CALIBRATION_SEEDS, CALIBRATION_SEEDS + n), db)
    scores = []
    for d in decks:
        if use_spellbook:
            spellbook.attach(d)
        scores.append(SCORERS[scorer](d, None))
    cut = statistics.quantiles(scores, n=5)
    CUTOFFS.write_text(json.dumps({"data_version": cards.data_version(), "scorer": scorer, "n": n,
                                   "bracket_source": "spellbook" if use_spellbook else "local", "cutoffs": cut}))
    return cut


def rate(deck: Deck, scorer: str = "heuristic", *, use_spellbook: bool = False) -> str:
    cal = json.loads(CUTOFFS.read_text()) if CUTOFFS.exists() else None
    if not cal:
        return "unrated (not calibrated: run 'manaforge calibrate')"
    src = "spellbook" if use_spellbook else "local"
    if cal["data_version"] != cards.data_version():
        return f"unrated (calibrated for {cal['data_version'][:10]}, data is {cards.data_version()[:10]}: recalibrate)"
    if cal["scorer"] != scorer:
        return f"unrated (calibrated with scorer '{cal['scorer']}', not '{scorer}')"
    if cal["bracket_source"] != src:
        return f"unrated (calibrated with bracket source '{cal['bracket_source']}', not '{src}')"
    if use_spellbook:
        spellbook.attach(deck)
    s = SCORERS[scorer](deck, None)
    return f"{stars(s, cal['cutoffs'])}/5 (score {s:.1f}, {scorer} scorer, {cal['n']} calibration decks)"
