"""format.yaml loader: the single source of the format numbers (validator, generator, rules sheet)."""
import math, os
from pathlib import Path

import yaml

FILE = Path(os.environ.get("MANAFORGE_FORMAT") or Path(__file__).parent.parent / "format.yaml")
CHOICES = {("commander_ability", "land_enters"): ("untapped", "tapped"), ("commander_ability", "look_at_top"): (1, 2)}


def load(path: Path | None = None) -> dict:
    cfg = yaml.safe_load((path or FILE).read_text())
    for (sec, key), ok in CHOICES.items():
        if cfg[sec][key] not in ok:
            raise ValueError(f"format.yaml: {sec}.{key} = {cfg[sec][key]!r}, expected one of {ok}")
    return cfg


def nonbasic_cap(size: int, cfg: dict) -> int:
    return math.ceil(size / cfg["land_deck"]["nonbasic_cap_divisor"])
