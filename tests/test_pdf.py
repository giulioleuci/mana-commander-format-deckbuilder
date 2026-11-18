import re
import pytest
from PIL import Image
from reportlab.pdfgen.canvas import Canvas

from manaforge import images, pdf
from manaforge.cards import lookup
from manaforge.decks import parse_text
from tests.conftest import FIXTURES

LEGAL = (FIXTURES / "decks" / "legal.txt").read_text()


@pytest.fixture
def deck(db):
    d = parse_text(LEGAL, lookup(db))
    d.name, d.seed = "The Test Deck", 7
    return d


def test_dpi_and_quality(tmp_path):
    lo, hi = tmp_path / "lo.png", tmp_path / "hi.png"
    Image.new("RGB", (367, 512)).save(lo)
    Image.new("RGB", (745, 1040)).save(hi)  # Scryfall png size
    assert 147 < images.dpi(lo) < 149 and images.quality(images.dpi(lo)) == "low"
    assert 299 < images.dpi(hi) < 301 and images.quality(images.dpi(hi)) == "ok"
    assert images.quality(180) == "warn"


def test_grid_fits_both_papers():
    for paper, b, g in (("a4", 0, 0), ("letter", 0, 1), ("a4", 2, 2)):
        cells = pdf.grid(paper, b, g)
        w, h = pdf.PAPER[paper]
        assert len(cells) == 9
        assert all(0 <= x and x + (63 + 2 * b) * pdf.mm <= w and 0 <= y and y + (88 + 2 * b) * pdf.mm <= h for x, y in cells)


def test_grid_too_big_raises():
    with pytest.raises(ValueError, match="does not fit"):
        pdf.grid("letter", 10, 0)


def test_render_sections_notice_and_rules(tmp_path, deck, monkeypatch):
    monkeypatch.setattr(images, "fetch", lambda c, lang="en", min_dpi=200: None)  # placeholders, no network
    spy, right = [], []
    monkeypatch.setattr(Canvas, "drawString", lambda self, x, y, s, *a, **k: spy.append(s))
    monkeypatch.setattr(Canvas, "drawRightString", lambda self, x, y, s, *a, **k: right.append(s))
    out = tmp_path / "o.pdf"
    pdf.render([deck], out)
    pages = lambda: len(re.findall(rb"/Type /Page[^s]", out.read_bytes()))
    n = pages()
    assert spy.count(pdf.NOTICE) == n  # the notice is on every page, cover and rules sheet included
    # sections: 1 commander page, 31 main -> 4 pages, 18 lands -> 2 pages, each labelled
    sect = lambda name: [r for r in right if f"| {name} |" in r]
    assert (len(sect("Commander")), len(sect("Main deck")), len(sect("Land deck"))) == (1, 4, 2)
    assert "The Test Deck | Main deck | page 4/4" in right
    assert "Commander" in spy and any(s.startswith("1 Atraxa") for s in spy) and any("Land deck (18)" in s for s in spy) and any(pdf.ATTRIBUTION == s for s in spy)
    assert any("Mana Commander" in s for s in spy)  # rules sheet generated from the rules file
    right.clear()
    pdf.render([deck], out, once=True)  # 8 distinct lands -> 1 page instead of 2
    assert pages() == n - 1 and len([r for r in right if "| Land deck |" in r]) == 1
