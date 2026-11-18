import json
import pytest

from manaforge import cards, rating, spellbook
from manaforge.cards import lookup
from manaforge.decks import parse_text
from tests.conftest import FIXTURES
from tests.test_decks import drop

LEGAL = (FIXTURES / "decks" / "legal.txt").read_text()


@pytest.fixture
def deck(db):
    return parse_text(LEGAL, lookup(db))


def test_stars_boundaries():
    c = [30, 40, 50, 60]
    assert [rating.stars(x, c) for x in (10, 30, 45, 60, 90)] == [1, 2, 3, 5, 5]


def test_components_sum_to_score_and_stay_in_bounds(deck):
    comp = rating.components(deck)
    assert set(comp) == {"curve", "coverage", "game_changers", "bracket"}
    assert sum(comp.values()) == pytest.approx(rating.heuristic(deck)) and 0 < rating.heuristic(deck) < 100
    assert 0 <= comp["curve"] <= 25 and 0 <= comp["coverage"] <= 40 and 0 <= comp["game_changers"] <= 15 and 0 <= comp["bracket"] <= 20


def test_coverage_counts_tagged_cards_with_partial_credit(deck):
    from dataclasses import replace
    from manaforge import tags
    blank = lambda c, i: replace(c, name=f"Filler {i}", text="", keywords=(), power=None)
    cover = {"draw", "removal", "landsearch", "wincon", "protection"}
    none = type(deck)(deck.commander, [(blank(c, i) if tags.tag(c) & cover else c, q) for i, (c, q) in enumerate(deck.main)], deck.lands)
    assert rating.components(none)["coverage"] == 0 and rating.components(deck)["coverage"] > 25
    # one removal spell is worth 9 * 1/5 points
    one = type(deck)(deck.commander, [(c, q) for c, q in none.main[:-1]] + [(deck.main[[x.name for x, _ in deck.main].index("Swords to Plowshares")][0], 1)], deck.lands)
    assert rating.components(one)["coverage"] == pytest.approx(9 / 5)


def test_game_changers_and_bracket_raise_the_score(db, deck):
    gc = parse_text(drop(LEGAL, "Murder", "Doom Blade", "Skullclamp").replace("\nLands", "\n1 Demonic Tutor\n1 Vampiric Tutor\n1 Worldly Tutor\n\nLands"), lookup(db))
    assert sum(c.game_changer for c, _ in gc.main) >= 4  # Rhystic, Cyclonic Rift, Demonic, Vampiric, Worldly
    a, b = rating.components(deck), rating.components(gc)
    assert b["game_changers"] > a["game_changers"] and b["bracket"] > a["bracket"]
    assert rating.local_bracket(parse_text(drop(LEGAL, "Rhystic Study", "Cyclonic Rift"), lookup(db))) == 2
    assert rating.local_bracket(deck) == 3 and rating.local_bracket(gc) == 4


def test_spellbook_bracket_overrides_local(deck):
    deck.meta["bracket"] = 5
    assert rating.components(deck)["bracket"] == 20


def test_curve_prefers_a_sane_average(db, deck):
    top = parse_text(drop(LEGAL, "Swiftfoot Boots", "Arcane Signet", "Birds of Paradise", "Farseek", "Rampant Growth", "Counterspell", "Hardened Scales")
                     .replace("\nLands", "\n1 Sun Titan\n1 Craterhoof Behemoth\n\nLands").replace("1 Sun Titan\n", "", 1), lookup(db))
    assert rating.components(top)["curve"] < rating.components(deck)["curve"]


def test_scorer_is_pluggable(monkeypatch, deck, tmp_path):
    monkeypatch.setitem(rating.SCORERS, "sim", lambda d, cfg=None: 55.0)  # a simulator would plug in here
    monkeypatch.setattr(rating, "CUTOFFS", tmp_path / "c.json")
    monkeypatch.setattr(rating.cards, "data_version", lambda: "v1")
    (tmp_path / "c.json").write_text(json.dumps({"data_version": "v1", "scorer": "sim", "bracket_source": "local", "n": 50, "cutoffs": [30, 40, 50, 60]}))
    assert rating.rate(deck, "sim") == "4/5 (score 55.0, sim scorer, 50 calibration decks)"


def test_rate_unrated_paths(monkeypatch, deck, tmp_path):
    monkeypatch.setattr(rating, "CUTOFFS", tmp_path / "c.json")
    monkeypatch.setattr(rating.cards, "data_version", lambda: "v1")
    assert rating.rate(deck) == "unrated (not calibrated: run 'manaforge calibrate')"
    good = {"data_version": "other", "scorer": "heuristic", "bracket_source": "local", "n": 50, "cutoffs": [30, 40, 50, 60]}
    (tmp_path / "c.json").write_text(json.dumps(good))
    assert rating.rate(deck).startswith("unrated (calibrated for other")
    (tmp_path / "c.json").write_text(json.dumps({**good, "data_version": "v1", "scorer": "sim"}))
    assert rating.rate(deck).startswith("unrated (calibrated with scorer 'sim'")
    (tmp_path / "c.json").write_text(json.dumps({**good, "data_version": "v1", "bracket_source": "spellbook"}))
    assert "bracket source" in rating.rate(deck)  # cut-offs from Spellbook brackets aren't comparable to local ones


def test_calibrate_writes_quintiles(monkeypatch, tmp_path, deck):
    monkeypatch.setattr(rating, "CUTOFFS", tmp_path / "c.json")
    monkeypatch.setattr(rating.cards, "data_version", lambda: "v1")
    monkeypatch.setattr(rating.forge_mod, "forge_batch", lambda seeds, db, **k: [deck for _ in seeds])
    vals = iter(range(50))
    monkeypatch.setitem(rating.SCORERS, "ramp", lambda d, cfg=None: next(vals))
    cut = rating.calibrate({}, "ramp", n=50)
    assert len(cut) == 4 and cut == sorted(cut) and 9 < cut[0] < 11 and 38 < cut[3] < 40  # quintiles of 0..49
    saved = json.loads((tmp_path / "c.json").read_text())
    assert saved["scorer"] == "ramp" and saved["data_version"] == "v1" and saved["bracket_source"] == "local"


# ---- spellbook
def test_spellbook_estimate(monkeypatch, deck):
    seen = {}
    def post(url, body, max_age=None):
        seen.update(url=url, body=body)
        return {"bracketTag": "S", "cards": [], "combos": [{"definitelyTwoCard": True, "relevant": True}, {"definitelyTwoCard": False, "relevant": True},
                                                          {"definitelyTwoCard": True, "relevant": False}]}
    monkeypatch.setattr(spellbook.http, "post_json", post)
    r = spellbook.estimate(deck)
    assert r == {"bracket": 3, "tag": "S", "combos": 2, "two_card_combos": 1}
    assert seen["url"].endswith("/estimate-bracket") and seen["body"]["commanders"] == [{"card": "Atraxa, Praetors' Voice"}]
    assert len(seen["body"]["main"]) == 31 and {"card": "Ghave, Guru of Spores", "quantity": 1} in seen["body"]["main"]  # main deck only: the land deck is not a library
    spellbook.attach(deck)
    assert deck.meta["bracket"] == 3 and deck.meta["spellbook"]["tag"] == "S"


def test_spellbook_tags_and_failure(monkeypatch, deck):
    for tag, want in {"E": 1, "C": 2, "O": 2, "S": 3, "P": 4, "R": 5, "B": None}.items():
        monkeypatch.setattr(spellbook.http, "post_json", lambda *a, tag=tag, **k: {"bracketTag": tag, "cards": [], "combos": []})
        assert spellbook.estimate(deck)["bracket"] == want
    monkeypatch.setattr(spellbook.http, "post_json", lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    assert spellbook.estimate(deck) is None
    spellbook.attach(deck)
    assert "bracket" not in deck.meta  # offline: falls back to the local estimate, never blocks
