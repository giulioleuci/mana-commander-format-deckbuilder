"""Rule-based tags on oracle text (Scryfall Tagger tags are not in the bulk data; regexes are the baseline)."""
import re

from .cards import Card

GENERIC = {"draw", "removal", "landsearch", "protection"}  # the consistency set: any House can use these
_R = {
    "landsearch": r"search your library for [^.]*\b(lands?|plains|island|swamp|mountain|forest)\b",
    "ramp": r"\badd (\{|one |two |three |x |an amount)|mana of any",
    "draw": r"\bdraws? (a|an|one|two|three|four|five|x|that many|\d+) cards?\b|\bdraws? cards equal",
    "removal": (r"(destroy|exile) target (\w+ )?(creature|artifact|enchantment|permanent|nonland|planeswalker|attacking|tapped|nonblack|nonartifact)"
                r"|deals? (x|\d+) damage to (any target|target creature|each creature)|target creature gets -\d+/-\d+"
                r"|(destroy|exile) all (creatures|nonland|permanents|artifacts|enchantments)|return target (nonland permanent|creature)[^.]*owner's hand"),
    "wipe": r"(destroy|exile) all (creatures|nonland|permanents)|damage to each creature",
    "protection": r"hexproof|indestructible|protection from|counter target (spell|noncreature)|phase out|can't be countered",
    "wincon": r"you win the game|loses the game|each opponent loses|damage to each opponent|additional combat|double strike|creatures you control (get \+\w+/\+\w+|gain trample)",
}
_C = {k: re.compile(v) for k, v in _R.items()}


def tag(card: Card) -> set[str]:
    t = card.text.lower()
    out = {k for k, rx in _C.items() if rx.search(t)}
    if "landsearch" in out and "onto the battlefield" not in t:
        out -= {"landsearch"}  # ends in hand: dead here (decks.dead)
    if "landsearch" in out:
        out.add("ramp")
    if card.power is not None and card.power >= 5 and {"Flying", "Trample", "Haste"} & set(card.keywords):
        out.add("wincon")
    return out


def is_generic(card: Card) -> bool:
    return not card.is_land and bool(GENERIC & tag(card))
