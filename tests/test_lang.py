import io
from dataclasses import replace

import pytest
from PIL import Image

from manaforge import cards, cli, http, images, pdf
from manaforge.cards import lookup
from manaforge.decks import parse_text
from tests.conftest import FIXTURES

LEGAL = (FIXTURES / "decks" / "legal.txt").read_text()


def img_bytes(w, fmt="PNG"):
    """A gradient (not a flat colour, so 'unchanged pixels' is a real check) of width w."""
    im = Image.new("RGB", (w, int(w * 1.4)))
    im.putdata([(x * 7 % 256, y * 3 % 256, (x + y) % 256) for y in range(im.height) for x in range(im.width)])
    b = io.BytesIO(); im.save(b, fmt); return b.getvalue()


def pr(status="highres_scan", mvid=None, name="Anello Solare", n=1, png=True):
    return {"name": name, "png": f"https://s/{status}-{n}.png" if png and status not in ("placeholder", "missing") else None, "status": status, "mvid": mvid, "set": f"s{n}"}


@pytest.fixture
def net(monkeypatch, tmp_path):
    """Fake network: `served` maps url -> bytes; printings are set per test."""
    monkeypatch.setenv("MANAFORGE_CACHE", str(tmp_path))
    state = {"served": {}, "calls": [], "printings": {}}
    def get(url, max_age=None):
        state["calls"].append(url)
        if url not in state["served"]:
            raise OSError(f"404 {url}")
        return state["served"][url]
    monkeypatch.setattr(images.http, "get", get)
    monkeypatch.setattr(images.cards, "printings", lambda card, lang: state["printings"].get(lang, []))
    return state


G = images.GATHERER


# ---------------------------------------------------------------- cards.printings
def search_result(*ps):
    return {"data": list(ps)}


def raw(lang, status, mv=None, name="Anello Solare", set_="trc"):
    return {"lang": lang, "printed_name": name, "image_status": status, "set": set_, "multiverse_ids": mv or [], "image_uris": {"png": f"https://s/{status}-{set_}.png"}}


def test_printings_parse_and_query(monkeypatch, db, tmp_path):
    monkeypatch.setenv("MANAFORGE_CACHE", str(tmp_path))
    seen = []
    monkeypatch.setattr(cards.http, "get_json", lambda u, max_age=None: (seen.append(u), search_result(raw("it", "lowres", [11], set_="a"), raw("it", "placeholder", [], set_="b"),
                                                                                                         raw("it", "highres_scan", [22, 23], set_="c")))[1])
    got = cards.printings(db["Sol Ring"], "it")
    assert [(p["set"], p["status"], p["mvid"]) for p in got] == [("a", "lowres", 11), ("b", "placeholder", None), ("c", "highres_scan", 22)]
    assert got[1]["png"] is None and got[0]["png"] and got[2]["name"] == "Anello Solare"  # a placeholder image is never offered
    assert db["Sol Ring"].oracle_id in seen[0] and "lang%3Ait" in seen[0] and "unique=prints" in seen[0]
    monkeypatch.setattr(cards.http, "get_json", lambda *a, **k: pytest.fail("cached"))
    assert cards.printings(db["Sol Ring"], "it") == got


def test_printings_double_faced_404_and_offline(monkeypatch, db, tmp_path):
    import urllib.error
    monkeypatch.setenv("MANAFORGE_CACHE", str(tmp_path))
    dfc = {"lang": "it", "image_status": "lowres", "set": "znr", "multiverse_ids": [5], "card_faces": [{"printed_name": "Risveglio di Valakut", "image_uris": {"png": "https://s/f.png"}}, {}]}
    monkeypatch.setattr(cards.http, "get_json", lambda u, max_age=None: search_result(dfc))
    assert cards.printings(db["Valakut Awakening // Valakut Stoneforge"], "it")[0]["name"] == "Risveglio di Valakut"
    calls = []
    def nf(u, max_age=None):
        calls.append(u); raise urllib.error.HTTPError(u, 404, "Not Found", {}, io.BytesIO(b""))
    monkeypatch.setattr(cards.http, "get_json", nf)
    assert cards.printings(db["Forest"], "it") == [] and cards.printings(db["Forest"], "it") == [] and len(calls) == 1  # a 404 is remembered
    def offline(u, max_age=None):
        raise OSError("offline")
    monkeypatch.setattr(cards.http, "get_json", offline)
    assert cards.printings(db["Island"], "it") == []  # transient errors: nothing cached, no crash
    assert not (tmp_path / "lang" / f"p-it-{db['Island'].oracle_id}.json").exists()


def test_slim_keeps_image_status(db):
    assert db["Sol Ring"].image_status == "highres_scan"


# ---------------------------------------------------------------- images.fetch chain
def test_scryfall_highres_in_the_requested_language_wins(net, db):
    sol = db["Sol Ring"]
    net["printings"]["it"] = [pr("lowres", mvid=9), pr("highres_scan", n=2)]
    net["served"]["https://s/highres_scan-2.png"] = img_bytes(745)
    p = images.fetch(sol, "it")
    assert (sol.image_lang, sol.image_source, sol.printed_name, sol.image_quality) == ("it", "scryfall", "Anello Solare", "good")
    assert Image.open(p).width == 745 and net["calls"] == ["https://s/highres_scan-2.png"]  # Gatherer is not even asked


def test_gatherer_is_the_second_source_for_the_language(net, db):
    sol = db["Sol Ring"]
    net["printings"]["it"] = [pr("lowres", mvid=22)]  # Scryfall only has a blurry scan
    net["served"][G.format(22)] = img_bytes(646, "WEBP")  # Gatherer serves webp, 646 px = 260 dpi
    p = images.fetch(sol, "it")
    assert (sol.image_lang, sol.image_source, sol.printed_name, sol.image_quality) == ("it", "gatherer", "Anello Solare", "good")
    im = Image.open(p)
    assert im.format == "PNG" and im.width == 646 and "multiverseid=22" in net["calls"][-1]  # stored as png for the PDF engine
    assert "https://s/lowres-1.png" not in net["calls"]  # the blurry scan was never used


def test_placeholder_is_never_used(net, db):
    sol = db["Sol Ring"]
    net["printings"]["it"] = [pr("placeholder")]
    net["served"][sol.image] = img_bytes(745)
    images.fetch(sol, "it")
    assert sol.image_lang == "en" and net["calls"] == [sol.image]


def test_small_gatherer_image_falls_back_to_english_unmodified(net, db):
    sol = db["Sol Ring"]
    net["printings"]["it"] = [pr("lowres", mvid=22)]
    net["served"][G.format(22)] = img_bytes(300)  # ~121 dpi: not good enough for print
    src = img_bytes(745)
    net["served"][sol.image] = src
    p = images.fetch(sol, "it")
    assert (sol.image_lang, sol.printed_name, sol.image_source, sol.image_quality) == ("en", None, "scryfall", "good")
    assert Image.open(p).tobytes() == Image.open(io.BytesIO(src)).tobytes()  # no watermark, no overlay: the English scan as it is


def test_min_dpi_is_configurable(net, db):
    sol = db["Sol Ring"]
    net["printings"]["it"] = [pr("lowres", mvid=22)]
    net["served"][G.format(22)] = img_bytes(300)
    net["served"][sol.image] = img_bytes(745)
    images.fetch(sol, "it", min_dpi=100)
    assert sol.image_source == "gatherer" and sol.image_lang == "it"


def test_gatherer_tries_are_capped(net, db):
    sol = db["Sol Ring"]
    net["printings"]["it"] = [pr("lowres", mvid=100 + i, n=i) for i in range(6)]
    net["served"][sol.image] = img_bytes(745)
    images.fetch(sol, "it")
    assert len([c for c in net["calls"] if "multiverseid" in c]) == images.GATHERER_TRIES and sol.image_lang == "en"


def test_english_card_with_blurry_oracle_printing_looks_elsewhere(net, db):
    sol = replace(db["Sol Ring"], image_status="lowres")
    net["printings"]["en"] = [pr("highres_scan", n=7, name="Sol Ring")]
    net["served"]["https://s/highres_scan-7.png"] = img_bytes(745)
    images.fetch(sol, "en")
    assert sol.image_lang == "en" and sol.image_quality == "good" and "highres_scan-7" in net["calls"][-1]
    sol2 = replace(db["Island"], image_status="lowres")  # another card: same name would hit the cache of the first
    net["printings"]["en"] = [pr("lowres", mvid=31, name="Sol Ring")]
    net["served"][G.format(31)] = img_bytes(646, "WEBP")
    images.fetch(sol2, "en")
    assert sol2.image_source == "gatherer" and sol2.image_quality == "good"


def test_last_resort_is_flagged_not_hidden(net, db):
    sol = replace(db["Sol Ring"], image_status="lowres")
    net["printings"]["en"] = []
    net["served"][sol.image] = img_bytes(745)
    p = images.fetch(sol, "en")
    assert p is not None and sol.image_quality == "low"  # printed anyway, but the cover will say so


def test_cache_restores_everything_without_network(net, db):
    sol = db["Sol Ring"]
    net["printings"]["it"] = [pr("lowres", mvid=22)]
    net["served"][G.format(22)] = img_bytes(646, "WEBP")
    p1 = images.fetch(sol, "it")
    n = len(net["calls"])
    fresh = replace(db["Sol Ring"], image_lang="en", printed_name=None, image_source=None, image_quality="good")
    p2 = images.fetch(fresh, "it")
    assert p1 == p2 and len(net["calls"]) == n
    assert (fresh.image_lang, fresh.image_source, fresh.printed_name) == ("it", "gatherer", "Anello Solare")


def test_english_default_needs_no_search(net, db):
    sol = db["Sol Ring"]
    net["printings"] = {}
    net["served"][sol.image] = img_bytes(745)
    images.fetch(sol)
    assert net["calls"] == [sol.image] and sol.image_lang == "en"


def test_offline_returns_none(net, db):
    assert images.fetch(db["Sol Ring"], "it") is None


# ---------------------------------------------------------------- cover + cli
def test_cover_notes(tmp_path, db, monkeypatch):
    png = tmp_path / "c.png"
    png.write_bytes(img_bytes(745))
    def fetch(card, lang="en", min_dpi=200):
        card.image_lang, card.printed_name, card.image_source, card.image_quality = {
            "Sol Ring": ("it", "Anello Solare", "scryfall", "good"), "Rhystic Study": ("it", "Studio Ristico", "gatherer", "good"),
            "Forest": ("en", None, "scryfall", "low")}.get(card.name, ("en", None, "scryfall", "good"))
        return png
    monkeypatch.setattr(images, "fetch", fetch)
    d = parse_text("Commander\n1 Atraxa, Praetors' Voice\nMain\n1 Sol Ring\n1 Rhystic Study\n1 Murder\nLands\n1 Forest", lookup(db))
    lines = pdf.cover_lines(d, pdf.image_notes(d, "it"))
    assert "1 Sol Ring  [it: Anello Solare]" in lines
    assert "1 Rhystic Study  [it: Studio Ristico, from Gatherer]" in lines
    assert "1 Murder  [no it print good enough: English card]" in lines
    assert "1 Forest  [no it print good enough: English card]  (LOW source quality: no sharp image found)" in lines
    assert pdf.image_notes(d, "en") == {"Forest": "  (LOW source quality: no sharp image found)"}  # English: only real problems are noted


def test_pdf_never_draws_on_the_card_image(tmp_path, db, monkeypatch):
    """No watermark/overlay: the only strings drawn on proxy pages are the notice and the section label, outside the cards."""
    from reportlab.pdfgen.canvas import Canvas
    png = tmp_path / "c.png"; png.write_bytes(img_bytes(745))
    monkeypatch.setattr(images, "fetch", lambda c, lang="en", min_dpi=200: png)
    drawn = []
    for m in ("drawString", "drawCentredString", "drawRightString"):
        monkeypatch.setattr(Canvas, m, lambda self, x, y, s, *a, _m=m, **k: drawn.append((_m, s)))
    d = parse_text("Commander\n1 Atraxa, Praetors' Voice\nMain\n1 Sol Ring", lookup(db))
    d.name = "T"
    pdf.render([d], tmp_path / "o.pdf", card_lang="it")
    assert not [s for m, s in drawn if m == "drawCentredString"]  # centred text = the placeholder drawn on a card; none when images exist


def test_cli_passes_card_lang_and_min_dpi(monkeypatch, tmp_path, db):
    seen = []
    png = tmp_path / "c.png"; png.write_bytes(img_bytes(745))
    monkeypatch.setattr(cards, "load", lambda path=None: db)
    monkeypatch.setattr(images, "fetch", lambda c, lang="en", min_dpi=200: (seen.append((lang, min_dpi)), png)[1])
    f = str(FIXTURES / "decks" / "legal.txt")
    cli.main(["print", f, "-o", str(tmp_path / "o.pdf"), "--card-lang", "it", "--min-dpi", "180", "--once"])
    assert set(seen) == {("it", 180.0)}
    seen.clear()
    cli.main(["print", f, "-o", str(tmp_path / "o.pdf"), "--once"])
    assert set(seen) == {("en", 200.0)}
    with pytest.raises(SystemExit):
        cli.main(["print", f, "--card-lang", "xx"])
