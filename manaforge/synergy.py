"""Synergy model, after Decks of KeyForge's SAS (https://decksofkeyforge.com/about/sas): every card GIVES traits and WANTS
traits; a want grows stronger with the number of givers in the deck, a want with no givers is antisynergy (a dead payoff).
The commander counts extra on both sides (it is always available: EDHREC's per-commander synergy idea).

Also here: the role template (10 ramp / 10 draw / 10 removal per 99, scaled to the main deck), the curve target and a card
power proxy (popularity), so the forge can maximise synergy at a FIXED power level (balanced decks, KeyForge-style)."""
import math
import re
from collections import Counter
from typing import NamedTuple

from . import tags
from .cards import Card

# trait: (gives: regex on oracle text, wants: regex on oracle text). Type-based gives are added in _feat().
TRAITS = {
    "creatures": (r"create [^.]*creature tokens?",
                  r"creatures you control (get|have)|for each creature you control|whenever (a|another|one or more) (nontoken )?creatures? (you control )?(enters|attacks?)"
                  r"|creature spells? you cast|cast creature spells|if it's a creature card|\bconvoke\b|equipped creature|enchanted creature gets"),
    "tokens": (r"create [^.]*\btokens?\b|\bpopulate\b",
               r"whenever (a|one or more) [^.]*tokens? |tokens you control|for each token|\bpopulate\b"),
    "fodder": (r"create [^.]*\btokens?\b",
               r"sacrifice (a|another) (creature|artifact|permanent|token)[^.]*:|whenever [^.]*\bcreatures?\b[^.]* dies"),
    "counters": (r"put (a|an|one|two|three|x|that many|\w+) \+1/\+1 counters?|enters with [^.]*\+1/\+1 counter|\bmodular\b|\boutlast\b",
                 r"with (a|one or more) \+1/\+1 counters? on|\+1/\+1 counters? (would be|are) put|\bproliferate\b|for each \+1/\+1 counter"),
    "artifacts": (r"create [^.]*\b(treasure|clue|food|artifact)\b",
                  r"whenever (an|another|one or more) (nontoken )?artifacts? (you control )?(enters|is put)|whenever you cast an artifact|for each artifact|\bmetalcraft\b"
                  r"|affinity for artifacts|\bimprovise\b|artifacts you control|artifact spells? you cast"),
    "enchantments": (r"$^",
                     r"\bconstellation\b|whenever (an|another) (nontoken )?enchantment|enchantment spells? you cast|for each enchantment|whenever you cast an enchantment|auras? you control"),
    "spells": (r"$^",
               r"whenever you cast (an|a) (instant|sorcery|noncreature)|\bmagecraft\b|\bprowess\b|instant (and|or) sorcery spells you cast|whenever you cast or copy"),
    "graveyard": (r"\bmill\b|\bsurveil\b|discard (a|two|that|your|x)|\bdredge\b|put the top [^.]* into your graveyard",
                  r"from your graveyard|\bflashback\b|\bescape\b|\bunearth\b|\bdelve\b|cards? in your graveyard|\bthreshold\b|\bembalm\b|\beternalize\b|\bdisturb\b|\bretrace\b"),
    "lifegain": (r"\bgain (\d+|x|that much|an amount of) life|\blifelink\b",
                 r"whenever you gain life|if you would gain life|life you gained"),
    "landfall": (r"$^", r"\blandfall\b|whenever a land (you control )?enters|for each land you control"),
    "blink": (r"$^", r"exile [^.]*(creature|permanent) you control[^.]*return (it|that card|them)|exile another target [^.]*then return|triggers an additional time"),
}
_TR = {t: (re.compile(g), re.compile(w)) for t, (g, w) in TRAITS.items()}
NEED = {"creatures": 12, "landfall": 6, "spells": 10, "blink": 6}  # givers in the deck for a fully satisfied want (default 8)
BASELINE = {"landfall": 6}  # the commander drops a land every turn: landfall always has a source (section 5)
CMD_WANT, CMD_GIVE = 3.0, 2.0  # commander weight: always available, the deck's identity
DEAD_PAYOFF = 1.0  # penalty for a want with (almost) no givers
WIPE = re.compile(r"(destroy|exile) all (creatures|nonland permanents|permanents)|damage to each creature|all creatures get -")
GY_HATE = re.compile(r"exile (all|each player's) graveyards?|exile all cards from all graveyards|cards in graveyards can't")

# role template: ~10 ramp/draw/removal per 62 non-land cards in a 99 (10-10-10 template), scaled to a 36-card main
ROLES = {"ramp": (5, 8), "draw": (5, 8), "removal": (5, 8), "wipe": (0, 2), "protection": (2, 4), "wincon": (3, 6), "landsearch": (4, 7)}  # lower bounds >= rating.COVER
CREATURES = (10, 22)
CURVE = {1: 4, 2: 9, 3: 9, 4: 7, 5: 4, 6: 3}  # cmc bucket (<=1 and >=6 merged) -> cards in 36; one land per turn = normal pacing
MAX_RANK = 30000


class Feat(NamedTuple):
    give: tuple[str, ...]
    want: tuple[str, ...]
    roles: tuple[str, ...]
    creature: bool
    wipe: bool
    gy_hate: bool
    bucket: int


def _feat(c: Card, tribes: tuple[str, ...]) -> Feat:
    t, f = c.text.lower(), c.front
    give = {k for k, (g, _) in _TR.items() if g.search(t)}
    want = {k for k, (_, w) in _TR.items() if w.search(t)}
    give |= {k for k, ty in (("creatures", "Creature"), ("artifacts", "Artifact"), ("enchantments", "Enchantment")) if ty in f}
    give |= {"spells"} if ("Instant" in f or "Sorcery" in f) else set()
    if "Creature" in f and re.search(r"when [^.]*\bdies\b", t):
        give.add("fodder")  # death-trigger creature: wants to be sacrificed
    if "Creature" in f and re.search(r"when [^.]*\benters\b", t):
        give.add("blink")  # ETB creature
    roles = tags.tag(c)
    if "landsearch" in roles:
        give.add("landfall")
    own = c.text.replace(c.name, "")
    for s in tribes:
        if s in c.subtypes or "Changeling" in c.keywords:
            give.add(f"tribe:{s}")
        if re.search(rf"\b{re.escape(s)}s?\b", own):
            want.add(f"tribe:{s}")
    return Feat(tuple(sorted(give)), tuple(sorted(want)), tuple(sorted(roles & ROLES.keys())), "Creature" in f,
                bool(WIPE.search(t)), bool(GY_HATE.search(t)), min(max(int(c.cmc), 1), 6))


_CACHE: dict = {}  # (name, tribes) -> Feat; Card is unhashable


def feat(c: Card, tribes=()) -> Feat:
    """Sorted tuples throughout (determinism: float sums never depend on set order)."""
    k = (c.name, tuple(tribes))
    if k not in _CACHE:
        _CACHE[k] = _feat(c, k[1])
    return _CACHE[k]


def tribes_of(cmd: Card) -> tuple[str, ...]:
    return tuple(sorted(s for s in cmd.subtypes if s != "Human")) if "Creature" in cmd.front else ()  # Human: too common to be a tribe


def quality(c: Card) -> float:
    """0-1 power proxy from EDHREC popularity rank (rank 1 -> 1, 1000 -> ~0.5, unranked -> 0).
    ponytail: popularity is not power (staples rank high in every deck); a play-rate or win-rate source would replace it."""
    r = c.rank if c.rank is not None else MAX_RANK
    return max(0.0, math.log((MAX_RANK + 50) / (r + 50)) / math.log((MAX_RANK + 50) / 51))


def score(main: list[Card], cmd: Card, tribes=None, *, explain: bool = False):
    """Synergy + template fit of a main deck. Returns the total, or (total, parts, notes) with explain=True."""
    tribes = tribes_of(cmd) if tribes is None else tribes
    fs = [feat(c, tribes) for c in main]
    cf = feat(cmd, tribes)
    G, W = Counter(BASELINE), Counter()
    for f in fs:
        G.update(f.give)
        W.update(f.want)
    for t in cf.give:
        G[t] += CMD_GIVE
    for t in cf.want:
        W[t] += CMD_WANT
    syn, notes = 0.0, []
    for c, f in zip(main, fs):
        for t in f.want:
            have = G[t] - (t in f.give)
            if have < 2:
                syn -= DEAD_PAYOFF
                notes.append(f"dead payoff: {c.name} wants {t}, deck has {have:g}")
            else:
                syn += min(have / NEED.get(t, 8), 1)
        syn += sum(0.3 * min((W[t] - (t in f.want)) / 3, 1) for t in f.give if W[t] - (t in f.want) > 0)
    syn += sum(CMD_WANT * min(G[t] / NEED.get(t, 8), 1) for t in cf.want)
    anti = 0.0
    ncre = sum(f.creature for f in fs)
    for c, f in zip(main, fs):
        if f.wipe and (ncre >= 15 or W["tokens"] + W["creatures"] >= 6):
            anti -= 1.5
            notes.append(f"antisynergy: {c.name} wipes your own board")
        if f.gy_hate and W["graveyard"] >= 4:
            anti -= 1.5
            notes.append(f"antisynergy: {c.name} exiles your own graveyard")
    k = len(main) / 36
    off = lambda n, lo, hi: max(lo * k - n, 0, n - hi * k)
    roles = Counter(r for f in fs for r in f.roles)
    tmpl = -1.5 * sum(off(roles[r], lo, hi) for r, (lo, hi) in ROLES.items())
    if "spells" not in cf.want:
        tmpl -= off(ncre, *CREATURES)
    cur = Counter(f.bucket for f in fs)
    curve = -0.5 * sum(abs(cur[b] - n * k) for b, n in CURVE.items())
    parts = {"synergy": syn, "antisynergy": anti, "template": tmpl, "curve": curve}
    total = sum(parts.values())
    if not explain:
        return total
    notes += [f"template: {roles[r]} {r} (target {lo * k:.0f}-{hi * k:.0f})" for r, (lo, hi) in ROLES.items() if off(roles[r], lo, hi)]
    engines = sorted((t for t in W if W[t] >= 2 and G[t] >= 2 and t != "creatures"), key=lambda t: (-min(W[t], G[t]), t))
    return total, parts, [f"engine: {t} ({G[t]:g} givers, {W[t]:g} wanters)" for t in engines[:4]] + notes


def report(main: list[Card], cmd: Card) -> list[str]:
    """Human-readable synergy summary (cover page, `manaforge estimate`)."""
    total, parts, notes = score(main, cmd, explain=True)
    q = sum(quality(c) for c in main) / len(main)
    return ([f"Synergy score {total:.1f} = " + ", ".join(f"{k} {v:+.1f}" for k, v in parts.items()),
             f"Power: mean card quality {q:.2f} (0-1, popularity rank), game changers {sum(c.game_changer for c in main)}"] + notes)
