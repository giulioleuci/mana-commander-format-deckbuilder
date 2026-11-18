"""Card model + Scryfall oracle_cards loader (canonical DB, downloaded once, cached)."""
import gzip, json, time, urllib.error, urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import http

API = "https://api.scryfall.com"
SKIP_LAYOUTS = {"art_series", "token", "double_faced_token", "emblem", "vanguard", "scheme", "planar", "augment", "host"}
# no `games: paper` filter: oracle_cards may pick a digital-only printing of a paper card (Black Lotus -> VMA)


@dataclass
class Card:
    name: str
    type_line: str
    cmc: float = 0
    mana_cost: str = ""
    identity: tuple[str, ...] = ()
    text: str = ""
    keywords: tuple[str, ...] = ()
    produced: tuple[str, ...] = ()
    power: int | None = None
    legal: str = "legal"  # legalities.commander
    game_changer: bool = False
    layout: str = "normal"
    mdfc_land: bool = False  # front is a spell, back is a land (see decks.flags)
    image: str | None = None  # front face, png
    rank: int | None = None  # edhrec_rank: popularity, used to weight the forge away from junk
    oracle_id: str = ""
    printed_name: str | None = None  # set by images.fetch when a non-English printing was used
    image_lang: str = "en"
    image_status: str = "highres_scan"  # Scryfall: highres_scan | lowres | placeholder | missing (png size is always 745x1040, even when lowres)
    image_quality: str = "good"  # set by images.fetch: "low" only when no sharp image exists anywhere
    data_source: str = "scryfall"
    image_source: str | None = None

    @property
    def front(self) -> str:
        return self.type_line.split(" // ")[0]

    @property
    def is_land(self) -> bool:
        return "Land" in self.front

    @property
    def is_basic(self) -> bool:
        return "Basic" in self.front and self.is_land

    @property
    def subtypes(self) -> tuple[str, ...]:
        return tuple(self.front.partition("—")[2].split())

    @property
    def key(self) -> str:
        return self.name


def slim(raw: dict) -> Card | None:
    if raw["layout"] in SKIP_LAYOUTS:
        return None
    faces = raw.get("card_faces") or []
    front = faces[0] if faces else raw
    text = "\n//\n".join(f.get("oracle_text", "") for f in faces) if faces else raw.get("oracle_text", "")
    power = front.get("power", "")
    return Card(
        raw["name"], raw["type_line"], raw.get("cmc", 0), raw.get("mana_cost") or front.get("mana_cost", ""),
        tuple(raw.get("color_identity", ())), text, tuple(raw.get("keywords", ())), tuple(raw.get("produced_mana", ())),
        int(power) if power.isdigit() else None, raw["legalities"]["commander"], bool(raw.get("game_changer")), raw["layout"],
        raw["layout"] == "modal_dfc" and "Land" not in front["type_line"] and "Land" in faces[1]["type_line"],
        (raw.get("image_uris") or front.get("image_uris") or {}).get("png"), raw.get("edhrec_rank"), raw.get("oracle_id", ""),
        image_status=raw.get("image_status", "highres_scan"))


def printings(card: Card, lang: str) -> list[dict]:
    """Paper printings of the card in `lang`, newest first: [{name, png, status, mvid, set}].
    png is None for placeholder/missing images; mvid is the Gatherer multiverse id. oracle_cards is English only, so this asks the
    search API (2/s limit) once per card and language and caches the answer, misses included."""
    if not card.oracle_id:
        return []
    f = http.cache_dir() / "lang" / f"p-{lang}-{card.oracle_id}.json"
    if f.exists() and time.time() - f.stat().st_mtime < 30 * 86400:
        return json.loads(f.read_text())
    q = urllib.parse.urlencode({"q": f"oracleid:{card.oracle_id} lang:{lang} -is:digital", "unique": "prints", "order": "released", "dir": "desc"})
    try:
        data, miss = http.get_json(f"{API}/cards/search?{q}", 30 * 86400)["data"], False
    except urllib.error.HTTPError as e:
        data, miss = [], e.code == 404  # Scryfall: 404 = no printing in that language (offline/other errors are not cached)
    except Exception:
        return []
    out = []
    for p in data:
        face = (p.get("card_faces") or [{}])[0]
        png = (p.get("image_uris") or face.get("image_uris") or {}).get("png") if p["image_status"] in ("highres_scan", "lowres") else None
        out.append({"name": p.get("printed_name") or face.get("printed_name") or card.name, "png": png, "status": p["image_status"],
                    "mvid": (p.get("multiverse_ids") or [None])[0], "set": p["set"]})
    if out or miss:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(out))
    return out


def parse_bulk(lines) -> dict[str, Card]:
    return {c.name: c for line in lines if line.strip() and (c := slim(json.loads(line)))}


def _state() -> Path:
    return http.cache_dir() / "scryfall" / "VERSION"


def update_data() -> str:
    """Point the cache at the newest oracle_cards bulk file (Scryfall only serves the latest)."""
    d = next(x for x in http.get_json(f"{API}/bulk-data", 0)["data"] if x["type"] == "oracle_cards")
    _state().parent.mkdir(parents=True, exist_ok=True)
    _state().write_text(json.dumps({"version": d["updated_at"], "uri": d["jsonl_download_uri"]}))
    return d["updated_at"]


def data_version() -> str:
    if not _state().exists():
        update_data()
    return json.loads(_state().read_text())["version"]


def load(path: Path | None = None) -> dict[str, Card]:
    """name -> Card. `path` = a raw oracle jsonl(.gz) (tests); default = the cached/downloaded bulk file."""
    if path is not None:
        op = gzip.open if str(path).endswith(".gz") else open
        with op(path, "rt") as f:
            return parse_bulk(f)
    data_version()
    uri = json.loads(_state().read_text())["uri"]
    return parse_bulk(gzip.decompress(http.get(uri)).decode().splitlines())  # ponytail: ~3 s parse per run; pickle a slim cache if it hurts


def lookup(db: dict[str, Card]) -> Callable[[str], Card]:
    """Case-insensitive name lookup; also matches the front face of 'A // B'."""
    idx = {}
    for n, c in db.items():
        idx.setdefault(n.lower(), c)
        idx.setdefault(n.split(" // ")[0].lower(), c)
    def get(name: str) -> Card:
        return idx[name.strip().lower()]
    return get
