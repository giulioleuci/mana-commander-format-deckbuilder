import os, subprocess, sys
import pytest

from manaforge import fmt, forge as F, http, synergy as S, tags
from manaforge.decks import dead, flags, validate


def test_tags(db):
    T = lambda n: tags.tag(db[n])
    assert "draw" in T("Divination") and "draw" in T("Rhystic Study") and "draw" not in T("Swords to Plowshares")
    assert {"removal"} <= T("Swords to Plowshares") and {"removal", "wipe"} <= T("Wrath of God") and "removal" in T("Lightning Bolt")
    assert "landsearch" in T("Rampant Growth") and "landsearch" in T("Farseek") and "landsearch" in T("Kodama's Reach")
    assert "landsearch" not in T("Land Tax") and "landsearch" not in T("Sylvan Ranger")  # these end in hand: dead, not ramp
    assert "ramp" in T("Sol Ring") and "ramp" in T("Birds of Paradise") and "ramp" in T("Cultivate")
    assert {"protection"} <= T("Heroic Intervention") and "protection" in T("Counterspell") and "protection" in T("Swiftfoot Boots")
    assert "wincon" in T("Approach of the Second Sun") and "wincon" in T("Craterhoof Behemoth")
    assert tags.is_generic(db["Divination"]) and not tags.is_generic(db["Hardened Scales"]) and not tags.is_generic(db["Command Tower"])


def test_overlap_and_ids(db):
    from manaforge.decks import parse_text
    from manaforge.cards import lookup
    a = parse_text("Main\n1 Murder\n1 Doom Blade\n1 Divination\n1 Counterspell", lookup(db))
    b = parse_text("Main\n1 Murder\n1 Doom Blade\n1 Harmonize\n1 Brainstorm", lookup(db))
    assert F.overlap(a, a) == 1 and F.overlap(a, b) == 0.5 and F.overlap(b, a) == 0.5


def test_forge_tiny_pool_errors(db):
    with pytest.raises(ValueError, match="no legal deck after 100 attempts"):
        F.forge(1, {n: c for i, (n, c) in enumerate(sorted(db.items())) if c.is_land or i % 4 == 0})  # ~30 cards cannot fill a 36-card main deck


def test_forge_deterministic(real_db):
    a, b = F.forge(42, real_db), F.forge(42, real_db)
    assert a.commander == b.commander and a.main == b.main and a.lands == b.lands and a.name == b.name
    assert F.forge(43, real_db).main != a.main


def test_forge_hashseed_stable(tmp_path, real_db):
    code = ("from manaforge.forge import forge\nfrom manaforge.cards import load\nfrom manaforge.decks import to_text\n"
            "print(to_text(forge(7, load())))")

    def run(hashseed):  # fresh process; shares the downloaded Scryfall file through the cache dir
        env = {**os.environ, "PYTHONHASHSEED": hashseed}
        return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, env=env).stdout

    assert run("1") == run("2") != ""


def test_forge_legal_not_pile_not_dead(real_db):
    cfg = fmt.load()
    for seed in range(20):
        d = F.forge(seed, real_db)
        assert validate(d, cfg) == [], (seed, validate(d, cfg))
        assert not F.piles(d), (seed, F.piles(d))  # every card is in a House or the generic consistency set
        assert not [c.name for c, _ in d.main if dead(c, cfg)], seed
        assert sum(q for _, q in d.main) == cfg["generator"]["main_size"] and sum(q for _, q in d.lands) == cfg["generator"]["land_deck_size"]
        assert 1 <= len(d.meta["houses"]) <= 3 and d.meta["id"] == F.deck_id(seed)
        assert d.meta["estimator"] and isinstance(d.meta["flags"], list) and d.name.startswith("The ")


def test_forge_never_uses_mdfc_lands_or_banned(real_db):
    cfg = fmt.load()
    for seed in range(20, 35):
        d = F.forge(seed, real_db)
        assert not any(c.mdfc_land or c.name in cfg["banned"]["names"] for c, _ in d.main)


def test_forge_respects_config_and_commander(real_db):
    cfg = fmt.load()
    cfg["generator"]["main_size"], cfg["generator"]["land_deck_size"] = 31, 15
    d = F.forge(5, real_db, commander="Atraxa, Praetors' Voice", cfg=cfg)
    assert d.commander.name == "Atraxa, Praetors' Voice" and sum(q for _, q in d.main) == 31 and sum(q for _, q in d.lands) == 15
    assert validate(d, cfg) == [] and sum(q for c, q in d.lands if not c.is_basic) <= 4  # cap for 15 cards
    with pytest.raises(ValueError, match="cannot be the commander"):
        F.forge(5, real_db, commander="Sol Ring")


def test_land_deck_basics_follow_the_colors(real_db):
    d = F.forge(11, real_db, commander="Krenko, Mob Boss")  # mono red
    basics = {c.name for c, _ in d.lands if c.is_basic}
    assert basics <= {"Mountain"}
    w = F.forge(12, real_db, commander="Urza, Lord High Artificer")  # mono blue
    assert {c.name for c, _ in w.lands if c.is_basic} <= {"Island"}
    k = F.forge(13, real_db, commander="Karn, Scion of Urza")  # colourless
    assert {c.name for c, _ in k.lands if c.is_basic} <= {"Wastes"}


def test_batch_rejects_clones(real_db):
    batch = F.forge_batch(range(100, 112), real_db)
    assert len(batch) == 12
    for i, a in enumerate(batch):
        assert all(F.overlap(a, b) < F.CLONE_THRESHOLD for b in batch[:i])


def test_clone_threshold_forces_a_different_deck(real_db):
    a = F.forge(3, real_db)
    again = F.forge(3, real_db, against=[a])  # same seed would give the identical deck: must move to the next sub-seed
    assert F.overlap(a, again) < F.CLONE_THRESHOLD


def test_synergy_traits_and_dead_payoffs(db):
    F_ = lambda n: S.feat(db[n])
    assert "counters" in F_("Hardened Scales").want and "fodder" in F_("Viscera Seer").want and "fodder" in F_("Zulaport Cutthroat").want
    assert "tokens" in F_("Krenko, Mob Boss").give and "landfall" in F_("Rampant Growth").give and F_("Wrath of God").wipe
    cmd, filler = db["Edgar Markov"], [db[n] for n in ("Murder", "Doom Blade", "Divination", "Counterspell")]
    aristocrats = [db[n] for n in ("Viscera Seer", "Blood Artist", "Zulaport Cutthroat", "Krenko, Mob Boss", "Bloodghast")]
    lonely = [db["Hardened Scales"]] + filler  # counters payoff, no counters: antisynergy
    assert S.score(aristocrats, cmd) > S.score(filler + [db["Viscera Seer"]], cmd)
    assert any("dead payoff: Hardened Scales" in n for n in S.score(lonely, db["Urza, Lord High Artificer"], explain=True)[2])


def test_forge_balanced_power_no_unfun(real_db):
    import re
    cfg = fmt.load()
    for power in (2, 4):
        target, max_gc = F.POWER[power]
        for seed in range(3):
            d = F.forge(seed, real_db, power=power)
            main = [c for c, _ in d.main]
            assert abs(sum(map(S.quality, main)) / len(main) - target) < 0.03, (power, seed)  # same level = same power
            assert sum(c.game_changer for c in main) <= max_gc
            assert not [c.name for c in main if any(re.search(p, c.text.lower()) for p in cfg["generator"]["unfun_patterns"])]


def test_rebalance_moves_power_with_few_swaps(real_db):
    d = F.forge(1, real_db, power=4)  # quality ~0.65, 2 game changers
    r = F.rebalance(d, real_db, power=2)  # -> 0.45, 0 game changers
    main = [c for c, _ in r.main]
    assert abs(sum(map(S.quality, main)) / len(main) - F.POWER[2][0]) <= F.POWER_TOL + 0.002 and not any(c.game_changer for c in main)
    assert r.commander == d.commander and r.lands == d.lands and validate(r) == []
    assert 0 < len(r.meta["swaps"]["out"]) == len(r.meta["swaps"]["in"]) < len(main)
    assert F.rebalance(r, real_db, power=2).meta["swaps"]["out"] == []  # already on target: left alone
