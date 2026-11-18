from pathlib import Path
import pytest
from manaforge.cards import load

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def db():
    return load(FIXTURES / "scryfall.jsonl")


@pytest.fixture(scope="session")
def real_db():
    return load()  # cached Scryfall oracle_cards (downloads once into the cache)
