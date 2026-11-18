"""Proxy sheets (3x3, 63x88 mm, cut marks), deck cover page, rules sheet. Commander / main deck / land deck print as labelled sections."""
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

from . import fmt, images, rules
from .decks import Deck

NOTICE = "Unofficial proxies for personal playtesting, not for sale."
ATTRIBUTION = "Card data and images: Scryfall and Gatherer (cards (c) Wizards of the Coast). ManaForge is not affiliated with any of them."
PAPER = {"a4": A4, "letter": letter}
FRAME = "#e8e4dc"
MIN_V_MARGIN = 6 * mm  # room for cut marks and the notice


def grid(paper: str, bleed_mm: float, gap_mm: float) -> list[tuple[float, float]]:
    pw, ph = PAPER[paper]
    cw, ch, g = (63 + 2 * bleed_mm) * mm, (88 + 2 * bleed_mm) * mm, gap_mm * mm
    gw, gh = 3 * cw + 2 * g, 3 * ch + 2 * g
    if gw > pw or (ph - gh) / 2 < MIN_V_MARGIN:
        raise ValueError(f"3x3 grid of {bleed_mm} mm bleed / {gap_mm} mm gap does not fit on {paper}")
    x0, y0 = (pw - gw) / 2, (ph - gh) / 2
    return [(x0 + c * (cw + g), y0 + (2 - r) * (ch + g)) for r in range(3) for c in range(3)]


def _marks(c: Canvas, cells, bleed_mm):
    b, L, off = bleed_mm * mm, 4 * mm, 1 * mm
    xs = sorted({x + b for x, _ in cells} | {x + b + 63 * mm for x, _ in cells})
    ys = sorted({y + b for _, y in cells} | {y + b + 88 * mm for _, y in cells})
    top, bot = max(ys) + b + off, min(ys) - b - off
    left, right = min(xs) - b - off, max(xs) + b + off
    c.setLineWidth(0.3); c.setStrokeColorRGB(0, 0, 0)
    for x in xs:
        c.line(x, top, x, top + L); c.line(x, bot, x, bot - L)
    for y in ys:
        c.line(left, y, left - L, y); c.line(right, y, right + L, y)


def _qline(e: tuple, tag: str = "") -> str:
    return f"{e[1]} {e[0].name}{tag}"


def image_notes(d: Deck, lang: str = "en", imgs: dict | None = None, min_dpi: float = 200) -> dict[str, str]:
    """Fetch every image of the deck once (into `imgs`) and return name -> cover annotation (quality warnings, printed names, fallbacks)."""
    imgs = {} if imgs is None else imgs
    notes: dict[str, str] = {}
    for card in ([d.commander] if d.commander else []) + [c for c, _ in d.main + d.lands]:
        if card.key not in imgs:
            imgs[card.key] = images.fetch(card, lang, min_dpi)
        path, note = imgs[card.key], ""
        if path is None:
            print(f"warning: no image for {card.name}: placeholder printed", file=sys.stderr)
            note = "  (no image)"
        elif q := {"ok": "", "warn": "  (warn: <200 dpi)", "low": "  (LOW quality <150 dpi)"}[images.quality(images.dpi(path))]:
            print(f"warning: {card.name}{q.strip()}", file=sys.stderr)
            note = q
        if lang != "en" and path is not None:
            if card.image_lang == lang:
                shown = f": {card.printed_name}" if card.printed_name and card.printed_name != card.name else ""
                note += f"  [{lang}{shown}{', from Gatherer' if card.image_source == 'gatherer' else ''}]"
            else:
                note += f"  [no {lang} print good enough: English card]"
        if path is not None and card.image_quality == "low":
            note += "  (LOW source quality: no sharp image found)"
        if note:
            notes[card.name] = note
    return notes


def cover_lines(d: Deck, tags: dict[str, str]) -> list[str]:
    n_main, n_land = sum(q for _, q in d.main), sum(q for _, q in d.lands)
    lines = [f"Source: {d.source}" + (f" | seed {d.seed}" if d.seed is not None else "")]
    if "id" in d.meta:
        lines.append(f"Deck ID: {d.meta['id']}")
    if d.meta.get("rating"):
        lines.append(f"Rating: {d.meta['rating']}")
    lines += ["", "## Commander", f"1 {d.commander.name}  ({d.commander.mana_cost or 'no mana cost'}, {d.commander.type_line.split(' // ')[0]}){tags.get(d.commander.name, '')}" if d.commander else "(none)"]
    qty, done = {c.name: q for c, q in d.main}, set()
    lines += ["", f"## Main deck ({n_main})"]
    for house, names in d.meta.get("houses", {}).items():
        lines += ["", f"## House: {house}"] + [f"{qty[n]} {n}{tags.get(n, '')}" for n in names if n in qty and n not in done]
        done |= set(names)
    rest = [e for e in d.main if e[0].name not in done]
    if rest:
        lines += ["", "## Generic (draw, removal, land search, protection)" if done else ""] + [_qline((c, q), tags.get(c.name, "")) for c, q in rest]
    lines += ["", f"## Land deck ({n_land})"] + [_qline((c, q), tags.get(c.name, "")) for c, q in sorted(d.lands, key=lambda e: (e[0].is_basic, e[0].name))]
    if d.meta.get("synergy"):
        lines += ["", "## Synergy"] + list(d.meta["synergy"])
    if d.meta.get("estimator"):
        lines += ["", "## Estimator"] + list(d.meta["estimator"])
    if d.meta.get("flags"):
        lines += ["", "## Flags"] + list(d.meta["flags"])
    return lines + ["", ATTRIBUTION]


def render(decks: list[Deck], out: Path, *, paper: str = "a4", bleed_mm: float = 0, gap_mm: float = 0, once: bool = False,
           cfg: dict | None = None, lang: str = "en", card_lang: str = "en", min_dpi: float = 200) -> None:
    cfg = cfg or fmt.load()
    cells = grid(paper, bleed_mm, gap_mm)
    pw, ph = PAPER[paper]
    c = Canvas(str(out), pagesize=PAPER[paper])
    b = bleed_mm * mm
    imgs: dict = {}
    label = ""

    def end_page():
        c.setFont("Helvetica", 7); c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(10 * mm, 4 * mm, NOTICE)
        if label:
            c.drawRightString(pw - 10 * mm, 4 * mm, label)
        c.setFillColorRGB(0, 0, 0)
        c.showPage()

    def text_page(lines: list[str], title: str):
        y, w = ph - 20 * mm, pw - 30 * mm
        c.setFont("Helvetica-Bold", 16); c.drawString(15 * mm, y, title); y -= 9 * mm
        for ln in lines:
            bold = ln.startswith("## ")
            ind = len(ln) - len(ln.lstrip(" "))
            txt = ln.strip().removeprefix("## ")
            font = "Helvetica-Bold" if bold else "Helvetica"
            for part in simpleSplit(txt, font, 9, w - ind * 2 * mm) or [""]:
                if y < 18 * mm:
                    end_page(); y = ph - 20 * mm
                c.setFont(font, 9); c.drawString(15 * mm + ind * 2 * mm, y, part); y -= 4.2 * mm

    def proxies(name: str, section: str, entries: list[tuple]):
        nonlocal label
        pages = [(card, imgs[card.key]) for card, q in entries for _ in range(1 if once else q)]
        for i in range(0, len(pages), 9):
            label = f"{name} | {section} | page {i // 9 + 1}/{-(-len(pages) // 9)}"
            for (card, path), (x, y) in zip(pages[i:i + 9], cells):
                c.setFillColor(HexColor(FRAME))
                c.rect(x, y, 63 * mm + 2 * b, 88 * mm + 2 * b, stroke=0, fill=1)
                if path:
                    c.drawImage(str(path), x + b, y + b, 63 * mm, 88 * mm, preserveAspectRatio=True, anchor="c")
                else:
                    c.setFillColorRGB(0.1, 0.1, 0.1); c.setFont("Helvetica-Bold", 11)
                    c.drawCentredString(x + b + 31.5 * mm, y + b + 46 * mm, card.name)
                    c.setFont("Helvetica", 8)
                    c.drawCentredString(x + b + 31.5 * mm, y + b + 40 * mm, card.type_line.split(" // ")[0])
            _marks(c, cells, bleed_mm)
            end_page()
        label = ""

    for d in decks:
        tags = image_notes(d, card_lang, imgs, min_dpi)  # fetch once; quality, language and fallback notes go on the cover
        sections = ([("Commander", [(d.commander, 1)])] if d.commander else []) + [("Main deck", d.main), ("Land deck", d.lands)]
        text_page(cover_lines(d, tags), d.name)
        end_page()
        for s, e in sections:
            proxies(d.name, s, e)
    title, lines = rules.sheet(cfg, lang)
    text_page(lines, title)
    end_page()
    c.save()
