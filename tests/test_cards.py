import json
import pytest
from manaforge import cards, http
from manaforge.cards import lookup, slim


def test_slim_fields(db):
    s = db["Sol Ring"]
    assert (s.cmc, s.produced, s.legal, s.is_land) == (1, ("C",), "legal", False)
    assert "/png/" in s.image and ".png" in s.image and "scryfall" in s.image
    a = db["Atraxa, Praetors' Voice"]
    assert set(a.identity) == set("WUBG") and a.subtypes == ("Phyrexian", "Angel", "Horror") and a.power == 4
    assert db["Mana Crypt"].legal == "banned" and db["Mana Vault"].game_changer
    assert db["Forest"].is_basic and not db["Command Tower"].is_basic and db["Command Tower"].is_land


def test_mdfc_land_flags(db):
    v, p = db["Valakut Awakening // Valakut Stoneforge"], db["Blightstep Pathway // Searstep Pathway"]
    assert v.mdfc_land and not v.is_land  # spell front, land back
    assert p.is_land and not p.mdfc_land  # land on both sides is simply a land


def test_skips_non_cards():
    raw = {"name": "Elf", "type_line": "Token Creature", "layout": "token", "legalities": {"commander": "not_legal"}}
    assert slim(raw) is None


def test_lookup_front_face_and_case(db):
    get = lookup(db)
    assert get("valakut awakening").name.startswith("Valakut Awakening //") and get(" sol ring ").name == "Sol Ring"
    with pytest.raises(KeyError):
        get("Nonexistent Card")


def test_data_version_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAFORGE_CACHE", str(tmp_path))
    bulk = {"data": [{"type": "default_cards", "updated_at": "x", "jsonl_download_uri": "u0"},
                     {"type": "oracle_cards", "updated_at": "2026-11-18T10:01:54", "jsonl_download_uri": "https://d/x.jsonl.gz"}]}
    monkeypatch.setattr(http, "get_json", lambda url, max_age=None: bulk)
    assert cards.data_version() == "2026-11-18T10:01:54"
    assert json.loads((tmp_path / "scryfall" / "VERSION").read_text())["uri"] == "https://d/x.jsonl.gz"
