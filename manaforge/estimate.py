"""Built-in estimator (stdlib only): hypergeometric tables for the land deck, the opening hand and the curve vs 1 land per turn."""
import math

from .decks import Deck


def p_at_least_one(hits: int, n: int, drawn: int) -> float:
    """P(>= 1 of `hits` marked cards among `drawn` cards drawn without replacement from `n`)."""
    if hits <= 0 or drawn <= 0:
        return 0.0
    return 1.0 if n - hits < drawn else 1 - math.comb(n - hits, drawn) / math.comb(n, drawn)


def mean_hits(hits: int, n: int, drawn: int) -> float:
    return hits * drawn / n


def nonbasic_table(land_n: int, draws: int = 5, ks=range(2, 7)) -> list[str]:
    return [f"{k} non-basic: {100 * p_at_least_one(k, land_n, draws):.0f}% (mean {mean_hits(k, land_n, draws):.1f})" for k in ks]


def curve(deck: Deck, cfg: dict, turns: int = 6) -> list[dict]:
    """Per turn t: lands in play (commander gives 1/turn), cards seen, P(a spell castable with t lands is among them)."""
    n, hand, skip = sum(q for _, q in deck.main), cfg["start"]["hand"], cfg["start"]["starter_skips_first_draw"]
    rows = []
    for t in range(1, turns + 1):
        seen = hand + t - (1 if skip else 0)
        cheap = sum(q for c, q in deck.main if c.cmc <= t)
        rows.append({"turn": t, "lands": t, "seen": seen, "castable_in_deck": cheap, "expected": round(mean_hits(cheap, n, seen), 1),
                     "p_castable": p_at_least_one(cheap, n, seen)})
    return rows


def estimate(deck: Deck, cfg: dict) -> list[str]:
    n, hand = sum(q for _, q in deck.main), cfg["start"]["hand"]
    out = []
    L = sum(q for _, q in deck.lands)
    nb = sum(q for c, q in deck.lands if not c.is_basic)
    out.append(f"Land deck: {nb} non-basic in {L}; P(>=1 non-basic in the first 5 land-deck draws) {100 * p_at_least_one(nb, L, 5):.0f}% "
               f"(mean {mean_hits(nb, L, 5):.1f}), in the first 3: {100 * p_at_least_one(nb, L, 3):.0f}%")
    for cmc in (1, 2, 3):
        k = sum(q for c, q in deck.main if c.cmc <= cmc)
        out.append(f"P(opening hand of {hand} has a spell with mana value <= {cmc}) {100 * p_at_least_one(k, n, hand):.0f}% ({k} such cards)")
    if deck.commander:
        cc = deck.commander.cmc
        out.append(f"Commander mana value {cc:g}: castable on turn {cc:g} at 1 land per turn; with commander tax after one death, turn {cc + 2:g}")
    for r in curve(deck, cfg):
        out.append(f"T{r['turn']}: {r['lands']} lands in play, {r['seen']} cards seen, "
                   f"expect {r['expected']} spells castable (mv <= {r['turn']}), P(>=1) {100 * r['p_castable']:.0f}%")
    return out
