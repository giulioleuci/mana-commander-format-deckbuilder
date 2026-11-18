"""Rule-based forge: commander -> themes (give/want traits) -> seeded start -> simulated annealing on synergy at a fixed power
-> Houses + identity + estimator.

Determinism rule (as in PokéForge): every pool is sorted by name before it reaches `rng`; rng seeds are strings."""
import hashlib
import json
import math
import random
import re
from collections import Counter

from . import cards, fmt, playgroup, synergy as S, tags
from .cards import Card
from .decks import Deck, banned_reason, can_command, dead, flags, nonbasic_cap, validate
from .estimate import estimate

FORGE_VERSION = "2"
CLONE_THRESHOLD = 0.6  # share of main-deck cards two forged decks may have in common
MAX_ATTEMPTS = 100
MIN_HOUSE_POOL = 12
POWER = {1: (0.35, 0), 2: (0.45, 0), 3: (0.55, 1), 4: (0.65, 2), 5: (0.75, 4)}  # level -> (target mean card quality, game changers: exact target, hard max)
DEFAULT_POWER = 3
POWER_TOL, POWER_WALL = 0.01, 5000  # outside +-0.01 of the target, power beats everything (swap costs included)
GC_WEIGHT = 1000  # per game changer off the level's count: brackets are counted in game changers
ELO_QUALITY = 0.03  # mean card quality traded per 100 Playgroup Elo above 1500: a strong commander gets a weaker 35
# ponytail: calibration knob, not measured (no 1v1 win-rate data for forged decks); tune it from playtests/*.yaml results
POWER_WEIGHT = 400  # synergy points lost per 1.0 of mean-quality distance from the target: every deck lands at the same power
MIN_QUALITY = 0.14  # popularity floor (rank ~12000): no obscure junk, whatever its synergy
ANNEAL_STEPS, T_START, T_END = 3000, 2.0, 0.02
BASIC = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
COLOR_WORD = {"white": "W", "blue": "U", "black": "B", "red": "R", "green": "G"}

ADJ = ["Unwavering", "Gilded", "Restless", "Hollow", "Crimson", "Quiet", "Thundering", "Forgotten", "Gentle", "Wandering",
       "Ashen", "Radiant", "Stubborn", "Moonlit", "Brazen", "Patient", "Wild", "Verdant", "Frostbound", "Cunning"]
NOUN = ["Tide-Seer", "Ember-Warden", "Stone-Singer", "Gale-Caller", "Root-Weaver", "Spark-Smith", "Dusk-Walker", "Moss-Keeper",
        "Storm-Reader", "Star-Herder", "Shell-Binder", "Wing-Tamer", "Bone-Reader", "Dew-Gatherer", "Flame-Sower", "Mist-Pilgrim"]
PLACE = ["Cinder Hollow", "Pale Harbor", "Thistle Reach", "Quartz Vale", "Lantern Fen", "Ironwood", "Saltmarsh Keep", "Ember Crossing",
         "Mirror Lake", "Briar Heights", "Copper Dunes", "Silent Orchard", "Windmere", "Stormgate", "Fogbridge", "Amber Fields"]
EPITHET = ["Ascendant", "Unbound", "Reborn", "Eternal", "Sworn", "Hunted", "Awakened", "Forsaken", "Triumphant", "Lost",
           "Burning", "Silent", "Swift", "Ancient", "Rising", "Fallen"]


def deck_id(seed: int, power: int = 3, stats: str = "") -> str:
    return hashlib.sha1(f"{seed}|{FORGE_VERSION}|{power}|{stats}|{cards.data_version()}".encode()).hexdigest()[:8]


def overlap(a: Deck, b: Deck) -> float:
    sa, sb = ({c.name for c, _ in d.main} for d in (a, b))
    return len(sa & sb) / max(len(sa), 1)


def piles(deck: Deck) -> list[str]:
    """Main-deck cards that are in no House and not in the generic consistency set (must be empty)."""
    housed = {n for names in deck.meta["houses"].values() for n in names}
    return [c.name for c, _ in deck.main if c.name not in housed and not tags.is_generic(c)]


# ---------------------------------------------------------------- pools
_POOL: dict = {}  # ponytail: keyed by id(db); a long-lived process loading many dbs would leak. Fine for a CLI.


def _pool(db: dict[str, Card], cfg: dict):
    key = (id(db), len(db), repr((cfg["banned"], cfg["generator"], cfg["main_deck"], cfg["commander"])))
    if key not in _POOL:
        ok = [c for c in sorted(db.values(), key=lambda c: c.name) if c.legal == "legal" and not banned_reason(c, cfg)]
        unfun = [re.compile(x) for x in cfg["generator"]["unfun_patterns"]]
        spells = [c for c in ok if not c.is_land and not dead(c, cfg) and not any(x.search(c.text.lower()) for x in unfun)]
        _POOL[key] = (spells, [c for c in ok if c.is_land and not c.is_basic],
                      [c for c in ok if can_command(c, cfg)])
    return _POOL[key]


def _w(c: Card) -> float:
    return 1 / (200 + (c.rank if c.rank is not None else 30000)) ** 2  # popular cards are far likelier (~85% of picks from the top 1000): keeps decks away from junk


def _pick(rng: random.Random, pool: list[Card], k: int, taken: set[str]) -> list[Card]:
    pool, out = [c for c in pool if c.name not in taken], []
    for _ in range(min(k, len(pool))):
        out.append(c := rng.choices(pool, weights=[_w(x) for x in pool])[0])
        pool.remove(c)
    taken |= {c.name for c in out}
    return out


def _themes(cmd: Card, cand: list[Card], tribes: tuple[str, ...]) -> dict[str, tuple[float, list[Card]]]:
    """Trait -> (weight, pool of cards that give or want it). A theme needs depth AND both sides (>= 4 payoffs, >= 4 enablers),
    or it is a pile. The commander's wants weigh 3, its gives 1; with none of its own, any deep theme."""
    feats = {c.name: S.feat(c, tribes) for c in cand}
    def pool(t):
        p = [c for c in cand if t in feats[c.name].give or t in feats[c.name].want]
        w = sum(t in feats[c.name].want for c in p)
        return p if len(p) >= MIN_HOUSE_POOL and w >= 4 and len(p) - w >= 4 else None
    cf = S.feat(cmd, tribes)
    own = {t: 1.0 for t in cf.give if t not in ("creatures", "spells")} | {t: 3.0 for t in cf.want}
    out = {t: (w, p) for t, w in sorted(own.items()) if (p := pool(t))}
    return out or {t: (1.0, p) for t in sorted(S.TRAITS) if (p := pool(t))}


def _house(t: str) -> str:
    return f"{t[6:]} Kin" if t.startswith("tribe:") else t.capitalize()


def _basics(pips: Counter, ident: set[str], n: int) -> dict[str, int]:
    cols = sorted(ident)
    if not cols:
        return {"Wastes": n}
    w = {c: pips[c] for c in cols} if any(pips[c] for c in cols) else {c: 1 for c in cols}
    tot = sum(w.values())
    raw = {c: n * w[c] / tot for c in cols}
    out = {c: int(raw[c]) for c in cols}
    for c in sorted(cols, key=lambda c: (-(raw[c] - out[c]), c))[: n - sum(out.values())]:
        out[c] += 1
    for c in cols:  # every color we need gets at least one source
        if w[c] and not out[c] and n >= len(cols):
            out[max(cols, key=lambda x: (out[x], x))] -= 1
            out[c] = 1
    return {BASIC[c]: q for c, q in out.items() if q}


def _anneal(rng: random.Random, main: list[Card], allowed: list[Card], obj) -> list[Card]:
    """Simulated annealing over single-card swaps (the 'heuristic mutation' of evolutionary deckbuilding, one deck at a time)."""
    cur = best = obj(main)
    best_main, names = main, {c.name for c in main}
    for i in range(ANNEAL_STEPS):
        T = T_START * (T_END / T_START) ** (i / ANNEAL_STEPS)
        j, new = rng.randrange(len(main)), allowed[rng.randrange(len(allowed))]
        if new.name in names:
            continue
        trial = main[:j] + [new] + main[j + 1:]
        v = obj(trial)
        if v >= cur or rng.random() < math.exp((v - cur) / T):
            names = names - {main[j].name} | {new.name}
            main, cur = trial, v
            if v > best:
                best, best_main = v, main
    return best_main


def _cmd_weights(cmds: list[Card], table: dict[str, dict]) -> list[float] | None:
    """Fun to play: (pilot fun - opponent salt)^2 from Playgroup; unknown commanders get the median weight."""
    if not table:
        return None
    w = [max(s["fun"] - s["salt"], 0.1) ** 2 if (s := playgroup.of(c.name, table)) else None for c in cmds]
    known = sorted(x for x in w if x is not None)
    return [known[len(known) // 2] if x is None else x for x in w] if known else None


def _cands(cmd: Card, spells: list[Card]) -> list[Card]:
    ident = set(cmd.identity)
    off = [w for w, col in COLOR_WORD.items() if col not in ident]
    off = re.compile(rf"\b({'|'.join(off)}) (creature |permanent )?(spells?|creatures?|permanents?) you") if off else None
    return [c for c in spells if set(c.identity) <= ident and c.name != cmd.name and S.quality(c) >= MIN_QUALITY
            and not (off and off.search(c.text.lower()))]  # 'white creature spells you cast' in mono-green: dead


def _objective(cmd: Card, tribes, power: int, cstat: dict | None, keep=frozenset(), swap_cost: float = 0.0):
    target, gc = POWER[power]
    if cstat:  # balance the whole deck, commander included: it is in every game
        target = min(max(target - ELO_QUALITY * (cstat["elo"] - 1500) / 100, 0.2), 0.9)
    def obj(m: list[Card]) -> float:
        q = sum(S.quality(c) for c in m) / len(m)
        return (S.score(m, cmd, tribes) - POWER_WEIGHT * abs(q - target) - POWER_WALL * max(0.0, abs(q - target) - POWER_TOL)
                - GC_WEIGHT * abs(sum(c.game_changer for c in m) - gc)
                - swap_cost * sum(c.name not in keep for c in m))
    return obj


def _attempt(rng: random.Random, db, pool, cfg: dict, forced: Card | None, power: int, table: dict, cw) -> Deck | None:
    spells, lands, cmds = pool
    cmd = forced or (rng.choices(cmds, weights=cw)[0] if cw else rng.choice(cmds))
    cstat = playgroup.of(cmd.name, table)
    ident, tribes = set(cmd.identity), S.tribes_of(cmd)
    cand = _cands(cmd, spells)
    themes = _themes(cmd, cand, tribes)
    if not themes:
        return None
    names = sorted(themes)
    wts = [themes[t][0] for t in names]
    chosen = []
    for _ in range(min(rng.choices([1, 2, 3], weights=[1, 3, 1])[0], len(names))):
        i = rng.choices(range(len(names)), weights=wts)[0]
        chosen.append(names.pop(i))
        wts.pop(i)
    allowed = {c.name: c for t in chosen for c in themes[t][1]} | {c.name: c for c in cand if tags.is_generic(c)}
    allowed = [allowed[n] for n in sorted(allowed)]
    size, max_gc = cfg["generator"]["main_size"], POWER[power][1]
    main = _pick(rng, allowed, size, set())
    if len(main) < size:
        return None
    main = sorted(_anneal(rng, main, allowed, _objective(cmd, tribes, power, cstat)), key=lambda c: c.name)
    if sum(c.game_changer for c in main) > max_gc or sum(c.cmc for c in main) / size > 3.7:
        return None
    houses: dict[str, list[str]] = {}
    for t in chosen:
        got = [c.name for c in main if t in (f := S.feat(c, tribes)).give + f.want and not any(c.name in v for v in houses.values())]
        if got:
            houses[f"{_house(t)} {rng.choice(EPITHET)}"] = got
    L = cfg["generator"]["land_deck_size"]
    types = {t: col for col, t in BASIC.items()}
    nb_pool = [c for c in lands if set(c.identity) <= ident and all(types[t] in ident for t in re.findall(r"Plains|Island|Swamp|Mountain|Forest", c.text))]  # a fetch for a basic type we lack is dead
    nb = _pick(rng, nb_pool, min(nonbasic_cap(L, cfg), len(nb_pool), rng.choice([2, 3, 3, 4, 4, 5])), set())
    pips = Counter(s for c in main + [cmd] for m in re.findall(r"\{([^}]+)\}", c.mana_cost) for s in re.findall(r"[WUBRG]", m))
    basics = _basics(pips, ident, L - len(nb))
    d = Deck(cmd, [(c, 1) for c in main], [(c, 1) for c in nb] + [(db[n], q) for n, q in sorted(basics.items())])
    d.meta |= {"houses": houses, "power": power, "synergy": S.report(main, cmd) + ([playgroup.line(cmd.name, cstat)] if cstat else [])}
    return d


def forge(seed: int, db: dict[str, Card], *, commander: str | None = None, cfg: dict | None = None, against=(), power: int = DEFAULT_POWER,
          commander_stats: dict[str, dict] | None = None) -> Deck:
    """commander_stats: playgroup.stats() (fun/salt-weighted commander choice, Elo-adjusted power target); None = popularity only."""
    cfg = cfg or fmt.load()
    if power not in POWER:
        raise ValueError(f"power must be one of {sorted(POWER)}")
    pool, forced = _pool(db, cfg), None
    if commander:
        try:
            forced = cards.lookup(db)(commander)
        except KeyError:
            raise ValueError(f"unknown card {commander!r}") from None
        if not can_command(forced, cfg) or banned_reason(forced, cfg):
            raise ValueError(f"{forced.name} cannot be the commander")
    table = commander_stats or {}
    cw = None if forced else _cmd_weights(pool[2], table)
    sv = hashlib.sha1(json.dumps(sorted(table.items())).encode()).hexdigest()[:8] if table else ""  # new stats week, new deck ids
    for a in range(MAX_ATTEMPTS):
        d = _attempt(random.Random(f"{seed}:{a}"), db, pool, cfg, forced, power, table, cw)
        if d and not validate(d, cfg) and not piles(d) and all(overlap(d, e) < CLONE_THRESHOLD for e in against):
            nr = random.Random(f"{seed}:{a}:name")
            d.name = f"The {nr.choice(ADJ)} {nr.choice(NOUN)} of {nr.choice(PLACE)}"
            d.seed, d.source = seed, "ManaForge"
            d.meta |= {"id": deck_id(seed, power, sv), "estimator": estimate(d, cfg), "flags": flags(d, cfg)}
            return d
    raise ValueError(f"no legal deck after {MAX_ATTEMPTS} attempts for seed {seed} (pool too small?)")


def forge_batch(seeds, db: dict[str, Card], **kw) -> list[Deck]:
    """Clone rejection across a batch: each deck must differ from every earlier one."""
    out: list[Deck] = []
    for s in seeds:
        out.append(forge(s, db, against=out, **kw))
    return out


RESTARTS = 3  # annealing from a fixed start can stall: best of 3
STAR_WALL = 200  # per heuristic point outside the star band of the power level


def _star_band(power: int) -> tuple[float, float] | None:
    """(centre, half width minus a margin) of the middle star band (3/5). Stars are quintiles of a calibration batch forged at
    DEFAULT_POWER, so the band means 'like a typical forged deck' only at that level; None at other levels or uncalibrated."""
    from . import rating
    if power != DEFAULT_POWER or not rating.CUTOFFS.exists():
        return None
    cut = json.loads(rating.CUTOFFS.read_text())["cutoffs"]
    return (cut[1] + cut[2]) / 2, max((cut[2] - cut[1]) / 2 - 0.1, 0.0)


SWAP_COST = 5.0  # synergy points a swap must earn on its own: a rebalanced deck stays the same deck


def rebalance(deck: Deck, db: dict[str, Card], *, power: int = DEFAULT_POWER, commander_stats: dict[str, dict] | None = None,
              cfg: dict | None = None) -> Deck:
    """Same commander and land deck; the fewest main-deck swaps that put it on the power target (quality, Elo, game changers)
    and fix dead payoffs. meta['swaps'] = {'out': [...], 'in': [...]}."""
    cfg = cfg or fmt.load()
    cmd, tribes, main = deck.commander, S.tribes_of(deck.commander), [c for c, _ in deck.main]
    cand = _cands(cmd, _pool(db, cfg)[0])
    themes = _themes(cmd, cand, tribes)
    allowed = {c.name: c for _, p in themes.values() for c in p} | {c.name: c for c in cand if tags.is_generic(c)} | {c.name: c for c in main}
    cstat = playgroup.of(cmd.name, commander_stats or {})
    base = _objective(cmd, tribes, power, cstat, keep=frozenset(c.name for c in main), swap_cost=SWAP_COST)
    band = _star_band(power)
    def obj(m: list[Card]) -> float:  # also inside the printed star band, or the covers would disagree with the balance
        if not band:
            return base(m)
        from .rating import heuristic
        h = heuristic(Deck(cmd, [(c, 1) for c in m], deck.lands), cfg)
        return base(m) - STAR_WALL * max(0.0, abs(h - band[0]) - band[1])
    pool = [allowed[n] for n in sorted(allowed)]
    new = max((_anneal(random.Random(f"rebalance:{deck.seed}:{cmd.name}:{k}"), main, pool, obj) for k in range(RESTARTS)), key=obj)
    new = sorted(new, key=lambda c: c.name)
    old_n, new_n = {c.name for c in main}, {c.name for c in new}
    d = Deck(cmd, [(c, 1) for c in new], deck.lands, deck.name, deck.source, deck.seed, dict(deck.meta))
    top = sorted(themes, key=lambda t: (-sum(t in S.feat(c, tribes).give + S.feat(c, tribes).want for c in new), t))[:3]
    houses: dict[str, list[str]] = {}
    for t in top:
        if got := [c.name for c in new if t in (f := S.feat(c, tribes)).give + f.want and not any(c.name in v for v in houses.values())]:
            houses[_house(t)] = got
    d.meta |= {"houses": houses, "power": power, "swaps": {"out": sorted(old_n - new_n), "in": sorted(new_n - old_n)},
               "synergy": S.report(new, cmd) + ([playgroup.line(cmd.name, cstat)] if cstat else []),
               "estimator": estimate(d, cfg), "flags": flags(d, cfg)}
    return d
