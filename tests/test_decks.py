import copy, math
import pytest
from manaforge import fmt
from manaforge.decks import banned_reason, can_command, flags, nonbasic_cap, parse_text, to_text, validate
from manaforge.cards import lookup
from tests.conftest import FIXTURES

LEGAL = (FIXTURES / "decks" / "legal.txt").read_text()


@pytest.fixture
def cfg():
    return fmt.load()


@pytest.fixture
def mk(db):
    return lambda text: parse_text(text, lookup(db))


def errs(mk, text, cfg=None, *words):
    msgs = validate(mk(text), cfg)
    for w in words:
        assert any(w in m for m in msgs), (w, msgs)
    return msgs


def test_legal_deck_is_clean(mk):
    d = mk(LEGAL)
    assert validate(d) == [] and len(d.main) == 31 and sum(q for _, q in d.lands) == 18 and d.commander.name.startswith("Atraxa")


def test_roundtrip(mk, db):
    d = mk(LEGAL)
    assert parse_text(to_text(d), lookup(db)).main == d.main
    assert [c.name for c, _ in parse_text(to_text(d), lookup(db)).lands] == [c.name for c, _ in d.lands]


def test_parse_forms(mk):
    d = mk("Commander\n1x Edgar Markov (CMR) 91\n1 Sol Ring\n2 Forest\n// comment\n\n1 Command Tower")
    assert d.commander.name == "Edgar Markov" and [c.name for c, _ in d.main] == ["Sol Ring"]
    assert [(c.name, q) for c, q in d.lands] == [("Forest", 2), ("Command Tower", 1)]  # no header: lands split off
    with pytest.raises(ValueError, match="Mewtwo"):
        mk("1 Mewtwo")


# ---- commander
def test_commander_rules(db, cfg):
    ok = lambda n: can_command(db[n], cfg)
    assert ok("Atraxa, Praetors' Voice") and ok("Jace Beleren") and ok("Teferi, Temporal Archmage")
    assert not ok("Llanowar Elves") and not ok("Sol Ring")
    cfg["commander"]["planeswalker"] = False
    assert not can_command(db["Jace Beleren"], cfg) and can_command(db["Teferi, Temporal Archmage"], cfg)  # needs the text


def test_commander_missing_and_bad(mk, cfg):
    errs(mk, LEGAL.replace("Commander\n1 Atraxa, Praetors' Voice\n", ""), cfg, "no commander")
    errs(mk, LEGAL.replace("Atraxa, Praetors' Voice", "Llanowar Elves"), cfg, "cannot be the commander")
    errs(mk, LEGAL.replace("1 Swords to Plowshares", "1 Atraxa, Praetors' Voice"), cfg, "commander")


# ---- main deck
def test_color_identity(mk, cfg):
    errs(mk, LEGAL.replace("1 Wrath of God", "1 Lightning Bolt"), cfg, "color identity")
    assert not any("color identity" in m for m in validate(mk(LEGAL.replace("1 Wrath of God", "1 Sol Ring"))))  # colourless: banned, not off-identity
    errs(mk, LEGAL.replace("4 Plains", "4 Mountain"), cfg, "color identity")
    assert validate(mk(LEGAL.replace("4 Plains", "4 Wastes"))) == []  # colourless always fits


EXTRA = ["Brainstorm", "Ponder", "Fellwar Stone", "Commander's Sphere", "Thran Dynamo", "Cultivator's Caravan", "Wayfarer's Bauble",
         "Nature's Lore", "Three Visits", "Sakura-Tribe Elder"]


def add_main(text, *names):
    return text.replace("\nLands", "\n" + "\n".join(f"1 {n}" for n in names) + "\n\nLands")


def drop(text, *names):
    for n in names:
        text = text.replace(f"1 {n}\n", "")
    return text


def test_main_size(mk, cfg):
    assert validate(mk(add_main(LEGAL, *EXTRA[:9]))) == []  # 40 = maximum
    errs(mk, add_main(LEGAL, *EXTRA), cfg, "main deck has 41")
    assert validate(mk(drop(LEGAL, "Skullclamp"))) == []  # 30 = minimum
    errs(mk, drop(LEGAL, "Skullclamp", "Murder"), cfg, "main deck has 29")


def test_no_lands_in_main(mk, cfg):
    msgs = errs(mk, add_main(LEGAL, "Command Tower", "Forest"), cfg, "Command Tower: lands are not allowed", "Forest: lands are not allowed")
    assert len(msgs) == 2 and not any("main deck has" in m for m in msgs)  # 33 cards is a fine size; only the lands are wrong


def test_mdfc_land_is_a_flagged_gap(db, cfg):
    d = lambda c: parse_text("Commander\n1 Krenko, Mob Boss\nMain\n1 Valakut Awakening\n", lookup(db))
    assert any("MDFC" in m for m in validate(d(cfg), cfg))
    cfg["main_deck"]["allow_mdfc_lands"] = True
    assert not any("MDFC" in m for m in validate(d(cfg), cfg))
    assert any("MDFC" in f for f in flags(d(cfg), cfg))  # still reported, never silent


def test_singleton(mk, cfg):
    errs(mk, LEGAL.replace("1 Murder", "2 Murder"), cfg, "2 copies of Murder")


# ---- banned
@pytest.mark.parametrize("card,why", [
    ("Mana Crypt", "Commander"), ("Sol Ring", "format ban"), ("Mana Vault", "format ban"), ("Grim Monolith", "format ban"),
    ("Hermit Druid", "format ban"), ("Animist's Awakening", "format ban"), ("Exploration", "format ban"),
    ("Oracle of Mul Daya", "format ban"), ("Crucible of Worlds", "format ban"), ("Bloodbraid Elf", "Cascade")])
def test_banned_cards(db, cfg, card, why):
    assert why in banned_reason(db[card], cfg)


def test_banned_by_text_pattern_not_just_name(db, cfg):
    cfg["banned"]["names"] = []
    for n in ("Hermit Druid", "Exploration", "Crucible of Worlds", "Azusa, Lost but Seeking"):
        assert banned_reason(db[n], cfg), n  # caught by the regexes alone


def test_banned_in_deck(mk, cfg):
    errs(mk, LEGAL.replace("1 Wrath of God", "1 Mana Crypt"), cfg, "Mana Crypt", "banned")
    errs(mk, LEGAL.replace("1 Wrath of God", "1 Hermit Druid"), cfg, "Hermit Druid")
    errs(mk, LEGAL.replace("1 Evolving Wilds", "1 Crucible of Worlds"), cfg, "Crucible of Worlds")


def test_banned_clean_cards(db, cfg):
    for n in ("Rampant Growth", "Kodama's Reach", "Cultivate", "Rhystic Study", "Command Tower", "Evolving Wilds", "Gaea's Cradle"):
        assert banned_reason(db[n], cfg) is None, n


# ---- land deck
@pytest.mark.parametrize("n,cap", [(15, 4), (16, 4), (17, 5), (18, 5), (19, 5), (20, 5)])
def test_nonbasic_cap_formula(cfg, n, cap):
    assert nonbasic_cap(n, cfg) == cap == math.ceil(n / 4)


def test_land_deck_size(mk, cfg):
    assert validate(mk(LEGAL.replace("4 Plains", "1 Plains"))) == []  # 15 = minimum
    errs(mk, LEGAL.replace("4 Plains\n", ""), cfg, "land deck has 14")
    assert validate(mk(LEGAL.replace("4 Plains", "6 Plains"))) == []  # 20 = maximum
    errs(mk, LEGAL.replace("4 Plains", "7 Plains"), cfg, "land deck has 21")


def test_nonbasic_singleton_and_cap(mk, cfg):
    errs(mk, LEGAL.replace("1 Command Tower", "2 Command Tower").replace("4 Island", "3 Island"), cfg, "2 copies of Command Tower")
    five = LEGAL.replace("4 Plains", "3 Plains\n1 Exotic Orchard")  # 5 non-basic in 18 (cap 5)
    assert validate(mk(five)) == []
    six = five.replace("4 Island", "3 Island\n1 Ancient Tomb")
    errs(mk, six, cfg, "6 non-basic lands (max 5")
    twenty = six.replace("3 Swamp", "5 Swamp")  # 20 cards -> cap 5 still
    errs(mk, twenty, cfg, "6 non-basic lands (max 5")


def test_land_deck_only_lands(mk, cfg):
    errs(mk, LEGAL.replace("4 Plains", "3 Plains\n1 Sol Ring"), cfg, "Sol Ring", "not a land")


def test_flags_gaps(mk, db, cfg):
    assert not any("land-search" in x for x in flags(mk(LEGAL), cfg))  # Rampant Growth, Farseek, Kodama's Reach present
    no_search = drop(LEGAL, "Rampant Growth", "Farseek", "Kodama's Reach")
    assert any("land-search" in x for x in flags(mk(no_search), cfg))  # commander exiled early -> no land source
    deck = lambda *n: parse_text("Commander\n1 Atraxa, Praetors' Voice\nMain\n" + "\n".join(f"1 {x}" for x in n), lookup(db))
    assert not any("commander-tutor" in x for x in flags(deck("Commander's Sphere"), cfg))  # "commander's color identity" is not a tutor
    assert any("commander-tutor" in x and "Command Beacon" in x for x in flags(deck("Command Beacon"), cfg))
    assert not any("commander-tutor" in x for x in flags(parse_text("Commander\n1 Atraxa, Praetors' Voice\nMain\n1 Sol Ring\nLands\n1 Path of Ancestry", lookup(db)), cfg))  # mentions the commander, doesn't tutor it
    assert not any("fast mana" in x for x in flags(deck("Sol Ring"), cfg))  # already on the ban list
    cfg["banned"]["names"] = []
    assert any("fast mana" in x and "Sol Ring" in x for x in flags(deck("Sol Ring"), cfg))
    assert not any("fast mana" in x for x in flags(deck("Arcane Signet", "Fellwar Stone"), cfg))
    assert not any("fast mana" in x for x in flags(deck("Priest of Forgotten Gods"), cfg))  # BB is a sacrifice payoff, not a tap-for-mana ability


def test_dead_cards(db, cfg):
    from manaforge.decks import dead
    for n in ("Land Tax", "Sylvan Ranger", "Burgeoning", "Command Tower", "Valakut Awakening // Valakut Stoneforge"):
        assert dead(db[n], cfg), n
    for n in ("Rampant Growth", "Kodama's Reach", "Cultivate", "Farseek", "Sakura-Tribe Elder", "Explosive Vegetation", "Mind Spring", "Rhystic Study"):
        assert dead(db[n], cfg) is None, n  # land-search to the battlefield searches the land deck: fine
    cfg["main_deck"]["allow_mdfc_lands"] = True
    assert dead(db["Valakut Awakening // Valakut Stoneforge"], cfg) is None
