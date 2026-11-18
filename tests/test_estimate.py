import pytest
from manaforge import estimate as E, fmt
from manaforge.cards import lookup
from manaforge.decks import parse_text
from tests.conftest import FIXTURES

LEGAL = (FIXTURES / "decks" / "legal.txt").read_text()


def test_p_at_least_one_edges():
    assert E.p_at_least_one(0, 36, 5) == 0
    assert E.p_at_least_one(36, 36, 5) == 1
    assert E.p_at_least_one(5, 6, 3) == 1  # pigeonhole: can't draw 3 cards without a success
    assert E.p_at_least_one(1, 4, 2) == pytest.approx(0.5)


def test_reproduces_the_pdf_design_table():
    """Section 8 of the rules: 18-card land deck, at least 1 non-basic within the first 5 land-deck draws."""
    got = [(k, round(100 * E.p_at_least_one(k, 18, 5)), round(E.mean_hits(k, 18, 5), 1)) for k in range(2, 7)]
    assert got == [(2, 49, 0.6), (3, 65, 0.8), (4, 77, 1.1), (5, 85, 1.4), (6, 91, 1.7)]


def test_nonbasic_table_lines():
    lines = E.nonbasic_table(18)
    assert lines[0].startswith("2 non-basic: 49%") and lines[4].startswith("6 non-basic: 91%")


def test_estimate_deck(db):
    d = parse_text(LEGAL, lookup(db))
    lines = E.estimate(d, fmt.load())
    text = "\n".join(lines)
    assert "Land deck: 4 non-basic in 18" in text and "P(>=1 non-basic in the first 5 land-deck draws) 77%" in text
    assert "Commander mana value 4" in text  # Atraxa
    assert text.count("T") >= 5 and "lands in play" in text
    assert any(l.startswith("P(opening hand of 5 has a spell with mana value <= 2)") for l in lines)


def test_curve_one_land_per_turn(db):
    d = parse_text(LEGAL, lookup(db))
    rows = E.curve(d, fmt.load(), turns=4)
    assert [r["lands"] for r in rows] == [1, 2, 3, 4]  # the commander puts exactly one land per turn
    assert rows[0]["seen"] == 5 and rows[1]["seen"] == 6  # on the play: skip the first draw -> 5, then 6
    assert all(0 <= r["p_castable"] <= 1 for r in rows)
    assert rows[3]["p_castable"] >= rows[0]["p_castable"]
    cfg = fmt.load(); cfg["start"]["starter_skips_first_draw"] = False
    assert E.curve(d, cfg, turns=2)[0]["seen"] == 6  # draw on turn 1 too
