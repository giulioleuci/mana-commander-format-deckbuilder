import re
import pytest
from manaforge import cards, cli, images, playgroup
from tests.conftest import FIXTURES

LEGAL = FIXTURES / "decks" / "legal.txt"


@pytest.fixture(autouse=True)
def offline(monkeypatch, db):
    monkeypatch.setattr(cards, "load", lambda path=None: db)
    monkeypatch.setattr(images, "fetch", lambda c, lang="en", min_dpi=200: None)
    monkeypatch.setattr(playgroup, "stats", dict)


def test_validate_legal_and_illegal(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["validate", str(LEGAL)])
    assert e.value.code == 0 and "legal" in capsys.readouterr().out
    bad = tmp_path / "bad.txt"
    bad.write_text(LEGAL.read_text().replace("1 Wrath of God", "1 Mana Crypt"))
    with pytest.raises(SystemExit) as e:
        cli.main(["validate", str(bad)])
    out = capsys.readouterr().out
    assert e.value.code == 1 and "Mana Crypt: banned" in out


def test_print_writes_pdf_with_cover_and_rules(tmp_path, capsys):
    out = tmp_path / "p.pdf"
    cli.main(["print", str(LEGAL), "-o", str(out), "--paper", "letter", "--bleed", "0", "--gap", "1", "--once"])
    assert out.exists() and len(re.findall(rb"/Type /Page[^s]", out.read_bytes())) >= 8 and "wrote" in capsys.readouterr().out


def test_print_split_and_stdin(tmp_path, monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(LEGAL.read_text()))
    out = tmp_path / "p.pdf"
    cli.main(["print", "-", str(LEGAL), "--split", "-o", str(out)])
    assert (tmp_path / "p-1.pdf").exists() and (tmp_path / "p-2.pdf").exists()


def test_url_input_is_refused_with_reason(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["print", "https://moxfield.com/decks/abc"])
    assert "paste the decklist" in str(e.value)


def test_estimate_and_rules(tmp_path, capsys):
    cli.main(["estimate", str(LEGAL)])
    out = capsys.readouterr().out
    assert "2 non-basic: 49%" in out and "Land deck: 4 non-basic in 18" in out
    cli.main(["rules", "-o", str(tmp_path / "r.pdf"), "--lang", "it"])
    assert (tmp_path / "r.pdf").stat().st_size > 2000
