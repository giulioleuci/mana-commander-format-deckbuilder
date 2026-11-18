"""Commander Spellbook bracket + combo estimate (one cached POST per deck; their docs ask clients not to page the whole dataset)."""
from . import http
from .decks import Deck

URL = "https://backend.commanderspellbook.com/estimate-bracket"
TAG = {"E": 1, "C": 2, "O": 2, "S": 3, "P": 4, "R": 5, "B": None}  # Exhibition, Core, Oddball, Spicy, Powerful, Ruthless, Banned
WEEK = 7 * 86400


def estimate(deck: Deck) -> dict | None:
    """{bracket 1-5 (None if banned cards), tag, combos, two_card_combos}, or None when offline."""
    front = lambda c: c.name.split(" // ")[0]
    body = {"commanders": [{"card": front(deck.commander)}], "main": [{"card": front(c), "quantity": q} for c, q in deck.main]}
    try:
        r = http.post_json(URL, body, WEEK)
    except Exception:  # offline / rate limited: the local estimate takes over
        return None
    rel = [v for v in r["combos"] if v["relevant"]]
    return {"bracket": TAG[r["bracketTag"]], "tag": r["bracketTag"], "combos": len(rel), "two_card_combos": sum(v["definitelyTwoCard"] for v in rel)}


def attach(deck: Deck) -> None:
    if (r := estimate(deck)) and r["bracket"]:
        deck.meta["spellbook"], deck.meta["bracket"] = r, r["bracket"]
