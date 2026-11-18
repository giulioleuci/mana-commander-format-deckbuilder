import re
import pytest
from manaforge import fmt, rules
from tests.conftest import FIXTURES


@pytest.mark.parametrize("lang", ["en", "it"])
def test_sheet_fills_every_placeholder_from_config(lang):
    title, lines = rules.sheet(fmt.load(), lang)
    body = "\n".join(lines)
    assert not re.search(r"\{(?!T\})\w+\}", body), re.findall(r"\{(?!T\})\w+\}", body)  # {T} is the mana symbol, not a placeholder
    assert {"en": "30 to 40 cards", "it": "Da 30 a 40 carte"}[lang] in body
    assert "Mana Commander" in title


def test_sheet_follows_config_flags():
    cfg = fmt.load()
    cfg["start"]["life"], cfg["commander_ability"]["land_enters"], cfg["commander_ability"]["look_at_top"] = 25, "tapped", 2
    _, lines = rules.sheet(cfg, "en")
    body = "\n".join(lines)
    assert "25 life" in body and "30 life" not in body
    assert "look at the top 2" in body.lower() and "tapped" in body and "untapped" not in body.split("Commander ability")[1].split("\n")[0]
    assert any("stay on top" in ln for ln in lines)


def test_markdown_source_and_mirror_have_same_sections():
    heads = lambda f: [re.match(r"#+", l)[0] + re.sub(r"\D", "", l) for l in (rules.RULES / f).read_text().splitlines() if l.startswith("#")]
    assert heads("regolamento.md") == heads("regolamento.en.md")  # same heading levels and numbers in both languages
