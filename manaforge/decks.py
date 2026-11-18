"""Deck model (commander + main deck + land deck), validation against format.yaml, text import/export."""
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from . import fmt, tags
from .cards import Card
from .fmt import nonbasic_cap  # re-exported

_HEAD = {"commander": "c", "main": "m", "main deck": "m", "deck": "m", "lands": "l", "land": "l", "land deck": "l", "lands deck": "l"}


@dataclass
class Deck:
    commander: Card | None
    main: list[tuple[Card, int]]
    lands: list[tuple[Card, int]]
    name: str = "Imported deck"
    source: str = "pasted list"
    seed: int | None = None
    meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------- rules
def can_command(c: Card, cfg: dict) -> bool:
    k = cfg["commander"]
    return ((k["legendary_creature"] and "Legendary" in c.front and "Creature" in c.front)
            or (k["planeswalker"] and "Planeswalker" in c.front) or k["text"] in c.text.lower())


def banned_reason(c: Card, cfg: dict) -> str | None:
    b = cfg["banned"]
    if b["commander_list"] and c.legal != "legal":
        return f"{c.legal.replace('_', ' ')} in Commander"
    if c.name in b["names"]:
        return "format ban (named)"
    if kw := next((k for k in b["keywords"] if k in c.keywords), None):
        return f"format ban ({kw}: reveal/exile until a hit)"
    t = c.text.lower()
    if rx := next((p for p in b["patterns"] if re.search(p, t)), None):
        return f"format ban (text matches /{rx}/)"


def dead(c: Card, cfg: dict) -> str | None:
    """Why a card does nothing in this format (generator filter). Land-search onto the battlefield is NOT dead: it searches the land deck."""
    if c.is_land:
        return "land card in the main deck"
    if c.mdfc_land and not cfg["main_deck"]["allow_mdfc_lands"]:
        return "MDFC land"
    g, t = cfg["generator"], c.text.lower()
    pats = g["dead_patterns"] + ([] if g["dead_to_hand_unless"] in t else g["dead_to_hand_patterns"])
    if rx := next((p for p in pats if re.search(p, t)), None):
        return f"needs lands in hand or draws lands (/{rx}/)"


def validate(deck: Deck, cfg: dict | None = None) -> list[str]:
    cfg = cfg or fmt.load()
    out, m, L = [], cfg["main_deck"], cfg["land_deck"]
    ident = None
    if deck.commander is None:
        out.append("no commander")
    else:
        ident = set(deck.commander.identity)
        if not can_command(deck.commander, cfg):
            out.append(f"{deck.commander.name} cannot be the commander")
        if r := banned_reason(deck.commander, cfg):
            out.append(f"{deck.commander.name}: banned ({r})")

    def card_msgs(c: Card):
        if ident is not None and not set(c.identity) <= ident:
            out.append(f"{c.name}: outside the commander's color identity")
        if r := banned_reason(c, cfg):
            out.append(f"{c.name}: banned ({r})")

    n = sum(q for _, q in deck.main)
    if not m["min"] <= n <= m["max"]:
        out.append(f"main deck has {n} cards, needs {m['min']}-{m['max']}")
    copies = Counter()
    for c, q in deck.main:
        copies[c.name] += q
        card_msgs(c)
        if c.is_land and not m["lands"]:
            out.append(f"{c.name}: lands are not allowed in the main deck")
        elif c.mdfc_land and not m["allow_mdfc_lands"]:
            out.append(f"{c.name}: MDFC with a land face counts as a land (not allowed in the main deck)")
        if deck.commander and c.name == deck.commander.name:
            out.append(f"{c.name}: the commander is also in the main deck")
    if m["singleton"]:
        out += [f"{q} copies of {nm} (singleton)" for nm, q in sorted(copies.items()) if q > 1]

    n = sum(q for _, q in deck.lands)
    if not L["min"] <= n <= L["max"]:
        out.append(f"land deck has {n} cards, needs {L['min']}-{L['max']}")
    nb = Counter()
    for c, q in deck.lands:
        card_msgs(c)
        if not c.is_land:
            out.append(f"{c.name}: not a land (land deck)")
        elif not c.is_basic:
            nb[c.name] += q
    if L["nonbasic_singleton"]:
        out += [f"{q} copies of {nm} (non-basic lands are singleton)" for nm, q in sorted(nb.items()) if q > 1]
    if (total := sum(nb.values())) > (cap := nonbasic_cap(n, cfg)):
        out.append(f"{total} non-basic lands (max {cap} for a {n}-card land deck)")
    return out


_TUTOR = re.compile(r"\b(put|return|search for|move)\b[^.]*\byour commander\b(?!'s)")


def flags(deck: Deck, cfg: dict | None = None) -> list[str]:
    """Judgement calls: reported, never silently decided."""
    cfg, out = cfg or fmt.load(), []
    for c, _ in deck.main:
        if c.mdfc_land:
            out.append(f"MDFC land: {c.name} (allow_mdfc_lands={cfg['main_deck']['allow_mdfc_lands']})")
        if _TUTOR.search(c.text.lower()):
            out.append(f"commander-tutor effect: {c.name}")
        f = cfg["banned"]["fast_mana_candidate"]
        if (not c.is_land and c.cmc <= f["max_cmc"] and c.name not in cfg["banned"]["names"] and c.legal == "legal"
                and (m := re.search(r"\{t\}[^.:]*:\s*add ((?:\{[^}]+\}){%d,})" % f["min_output"], c.text.lower()))):
            out.append(f"fast mana candidate: {c.name} (adds {m[1]} for cmc {c.cmc:g}; review the ban list)")
    for c, _ in deck.lands:
        if _TUTOR.search(c.text.lower()):
            out.append(f"commander-tutor effect: {c.name}")
    if not any("landsearch" in tags.tag(c) for c, _ in deck.main):
        out.append("no land-search effect in the main deck: if the commander is exiled early you have no land source")
    return out


# ---------------------------------------------------------------- text
_LINE = re.compile(r"(\d+)x?\s+(.+?)(?:\s+\([A-Za-z0-9]+\)\s*\S*)?")


def parse_text(text: str, lookup: Callable[[str], Card]) -> Deck:
    sec, cmd, main, lands = None, None, [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("//", "#")):
            continue
        if line.rstrip(":").lower() in _HEAD:
            sec = _HEAD[line.rstrip(":").lower()]
            continue
        m = _LINE.fullmatch(line)
        try:
            if not m:
                raise KeyError
            card, q = lookup(m[2]), int(m[1])
        except KeyError:
            raise ValueError(f"unknown or unparsable card line: {line!r}") from None
        if sec == "c":  # a Commander header holds one card; what follows is headerless again
            cmd, sec = card, None
        elif sec == "l" or (sec is None and card.is_land):  # no header: lands go to the land deck
            lands.append((card, q))
        else:
            main.append((card, q))
    return Deck(cmd, main, lands)


def to_text(deck: Deck) -> str:
    fmt_ = lambda es: "\n".join(f"{q} {c.name}" for c, q in es)
    return f"Commander\n1 {deck.commander.name if deck.commander else ''}\n\nMain\n{fmt_(deck.main)}\n\nLands\n{fmt_(deck.lands)}\n"
