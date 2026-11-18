"""On-demand card images from Scryfall (png, full front face: never cropped, artist line intact), cached on disk."""
import hashlib, io, json
from pathlib import Path

from PIL import Image

from . import cards, http
from .cards import Card


GATHERER = "https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid={}&type=card"  # official Wizards scans, up to ~650 px wide, in the printing's language
GATHERER_TRIES = 3  # printings tried per card and language


def _grab(url: str, min_dpi: float) -> bytes | None:
    """PNG bytes of the image at `url` if its REAL pixel width gives >= min_dpi at 63 mm, else None."""
    try:
        data = http.get(url)
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:  # 404, offline, not an image
        return None
    if im.width / (63 / 25.4) < min_dpi:
        return None
    if im.format == "PNG":
        return data
    out = io.BytesIO()
    im.convert("RGB").save(out, "PNG")  # Gatherer serves webp; the PDF engine gets png
    return out.getvalue()


def _tries(card: Card, lang: str):
    """(source, language, printed name, url), best first: Scryfall sharp scan, then Gatherer, in the language; then the same for English."""
    for lg in ([lang] if lang == "en" else [lang, "en"]):
        if lg == "en" and card.image and card.image_status == "highres_scan":
            yield "scryfall", "en", None, card.image
            continue
        ps = cards.printings(card, lg)
        name = lambda p: p["name"] if lg != "en" else None
        yield from (("scryfall", lg, name(p), p["png"]) for p in ps if p["png"] and p["status"] == "highres_scan")
        yield from (("gatherer", lg, name(p), GATHERER.format(p["mvid"])) for p in ps[:GATHERER_TRIES] if p["mvid"])


def fetch(card: Card, lang: str = "en", min_dpi: float = 200) -> Path | None:
    """Best print-quality image: `lang` if a sharp one exists (Scryfall, then Gatherer), else English, never modified or marked.
    card.image_lang / printed_name / image_source / image_quality say what was used."""
    h = hashlib.sha1(card.name.encode()).hexdigest()[:16]
    f = http.cache_dir() / "img" / f"{lang}-{int(min_dpi)}-{h}.png"
    meta = f.with_suffix(".json")
    if f.exists() and meta.exists():
        m = json.loads(meta.read_text())
    else:
        got = next(((src, lg, nm, png) for src, lg, nm, url in _tries(card, lang) if (png := _grab(url, min_dpi))), None)
        if got:
            m = {"source": got[0], "lang": got[1], "name": got[2], "quality": "good"}
        elif card.image and (png := _grab(card.image, 0)):  # last resort: printed anyway, flagged on the cover
            got, m = (None, png), {"source": "scryfall", "lang": "en", "name": None, "quality": "low"}
        else:
            return None
        png = got[3] if len(got) == 4 else got[1]
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(png)
        meta.write_text(json.dumps(m))
    card.image_source, card.image_lang, card.printed_name, card.image_quality = m["source"], m["lang"], m["name"], m["quality"]
    return f


def dpi(path: Path) -> float:
    from PIL import Image
    with Image.open(path) as im:
        return im.width / (63 / 25.4)


def quality(dpi: float, warn: float = 200, low: float = 150) -> str:
    return "low" if dpi < low else "warn" if dpi < warn else "ok"
