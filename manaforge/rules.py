"""Rules sheet text: rules/regolamento(.en).md with {placeholders} filled from format.yaml."""
import re
from pathlib import Path

RULES = Path(__file__).parent.parent / "rules"
FILES = {"en": "regolamento.en.md", "it": "regolamento.md"}
_ENTERS = {"en": {"untapped": "untapped", "tapped": "tapped"}, "it": {"untapped": "stappata", "tapped": "tappata"}}
_ABILITY = {
    "en": ("put the top card of the land deck onto the battlefield, {e}.",
           "look at the top {n} cards of the land deck and put one of them onto the battlefield, {e}; the others stay on top of the land deck in their order."),
    "it": ("metti in gioco la prima carta del mazzo terre, {e}.",
           "guarda le prime {n} carte del mazzo terre e metti in gioco una di esse, {e}; le altre restano in cima al mazzo terre nello stesso ordine."),
}
_NOTE = {"en": "Active settings (format.yaml v{version}): life {life}, hand {hand}, land enters {enters}, look at the top {look}, MDFC lands in the main deck: {mdfc}.",
         "it": "Impostazioni attive (format.yaml v{version}): vita {life}, mano {hand}, terra {enters}, guarda le prime {look}, MDFC terra nel mazzo principale: {mdfc}."}


def params(cfg: dict, lang: str) -> dict:
    a, m, L = cfg["commander_ability"], cfg["main_deck"], cfg["land_deck"]
    e = _ENTERS[lang][a["land_enters"]]
    one, many = _ABILITY[lang]
    return {"version": cfg["version"], "life": cfg["start"]["life"], "hand": cfg["start"]["hand"], "main_min": m["min"], "main_max": m["max"],
            "land_min": L["min"], "land_max": L["max"], "enters": e,
            "ability": (one if a["look_at_top"] == 1 else many).format(e=e, n=a["look_at_top"]), "look": a["look_at_top"],
            "mdfc": "yes" if m["allow_mdfc_lands"] else "no"}


def sheet(cfg: dict, lang: str = "en") -> tuple[str, list[str]]:
    """(title, lines). Lines keep a tiny markdown: '## ' bold heading, '- ' bullet, '  - ' nested, '' gap."""
    p = params(cfg, lang)
    text = re.sub(r"\{(?!T\})(\w+)\}", lambda m: str(p[m[1]]), (RULES / FILES[lang]).read_text())  # {T} is the tap symbol
    text = text.replace("**", "").replace("`", "")
    lines = text.splitlines()
    title = lines[0].removeprefix("# ")
    body = [l.replace("### ", "## ", 1) if l.startswith("### ") else l for l in lines[1:]]
    return title, body + ["", "## " + _NOTE[lang].format(**p)]
