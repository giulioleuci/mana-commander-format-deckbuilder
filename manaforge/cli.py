import argparse
import sys
from pathlib import Path

LANGS = ["en", "es", "fr", "de", "it", "pt", "ja", "ko", "ru", "zhs", "zht"]  # Scryfall language codes


def _read(f: str, lookup):
    from . import decks
    if f.startswith("http"):
        raise ValueError(f"{f}: deck URLs are not supported (Moxfield/Archidekt API terms not verified): paste the decklist text instead")
    d = decks.parse_text(sys.stdin.read() if f == "-" else Path(f).read_text(), lookup)
    d.name, d.source = (Path(f).stem, f) if f != "-" else ("Pasted deck", "pasted list")
    return d


def _load():
    from . import cards
    db = cards.load()
    return db, cards.lookup(db)


def cmd_validate(a):
    from . import decks
    _, lk = _load()
    bad = 0
    for f in a.inputs:
        d = _read(f, lk)
        errs = decks.validate(d)
        print(f"{d.name}: " + ("legal" if not errs else f"{len(errs)} problem(s)"))
        for m in errs:
            print(f"  - {m}")
        for m in decks.flags(d):
            print(f"  ! {m}")
        bad += bool(errs)
    sys.exit(1 if bad else 0)


def cmd_print(a):
    from . import decks, estimate, fmt, pdf
    _, lk = _load()
    cfg, ds = fmt.load(), [_read(f, lk) for f in a.inputs]
    for d in ds:
        if bad := decks.validate(d, cfg):
            print(f"warning: {d.name}: {'; '.join(bad)}", file=sys.stderr)
        d.meta |= {"estimator": estimate.estimate(d, cfg), "flags": decks.flags(d, cfg)}
        if a.rate:
            from . import rating
            d.meta["rating"] = rating.rate(d, use_spellbook=a.spellbook)
    out = Path(a.out)
    jobs = [(out.with_name(f"{out.stem}-{i}{out.suffix}"), [d]) for i, d in enumerate(ds, 1)] if a.split else [(out, ds)]
    for path, group in jobs:
        pdf.render(group, path, paper=a.paper, bleed_mm=a.bleed, gap_mm=a.gap, once=a.once, cfg=cfg, lang=a.lang, card_lang=a.card_lang, min_dpi=a.min_dpi)
        print(f"wrote {path}")


def cmd_forge(a):
    import random
    from . import forge, pdf, rating
    db, _ = _load()
    seeds = [a.seed] if a.seed is not None else [random.SystemRandom().randrange(10**6) for _ in range(a.count)]
    stats = None
    if not a.no_playgroup:
        from . import playgroup
        print("Playgroup.gg commander stats (first run of the week: ~1 min)...", file=sys.stderr)
        if not (stats := playgroup.stats()):
            print("  offline: forging without them", file=sys.stderr)
    ds = forge.forge_batch(seeds, db, commander=a.commander, power=a.power, commander_stats=stats)
    for d in ds:
        if not a.no_rate:
            d.meta["rating"] = rating.rate(d, use_spellbook=a.spellbook)
        print(f"{d.meta['id']}  seed {d.seed}  {d.name}  [{d.commander.name}]  {d.meta.get('rating', '')}")
        for h, names in d.meta["houses"].items():
            print(f"    {h}: {len(names)} cards")
    pdf.render(ds, Path(a.out), paper=a.paper, lang=a.lang, card_lang=a.card_lang, min_dpi=a.min_dpi)
    print(f"wrote {a.out}")


def cmd_rebalance(a):
    from . import decks, forge, playgroup
    db, lk = _load()
    stats = None if a.no_playgroup else playgroup.stats()
    for f in a.inputs:
        r = forge.rebalance(_read(f, lk), db, power=a.power, commander_stats=stats)
        sw = r.meta["swaps"]
        print(f"== {f}: {len(sw['out'])} swap(s)" + "".join(f"\n  - {o}\n  + {i}" for o, i in zip(sw["out"], sw["in"])))
        print("\n".join(f"  {x}" for x in r.meta["synergy"]))
        if a.write:
            Path(f).write_text(decks.to_text(r))


def cmd_estimate(a):
    from . import estimate, fmt
    _, lk = _load()
    cfg = fmt.load()
    for f in a.inputs:
        d = _read(f, lk)
        print(f"== {d.name}")
        print("\n".join(estimate.estimate(d, cfg)))
        if d.commander and d.main:
            from . import synergy
            print("\n".join(synergy.report([c for c, _ in d.main], d.commander)))
            from . import playgroup
            if s := playgroup.of(d.commander.name, playgroup.stats()):
                print(playgroup.line(d.commander.name, s))
    print(f"\nNon-basic lands in an {a.land_size}-card land deck, P(>=1 in the first 5 draws):")
    print("\n".join(estimate.nonbasic_table(a.land_size)))


def cmd_calibrate(a):
    from . import rating
    db, _ = _load()
    print("cut-offs:", [round(x, 1) for x in rating.calibrate(db, n=a.n, use_spellbook=a.spellbook)])


def cmd_rules(a):
    from . import fmt, pdf
    pdf.render([], Path(a.out), paper=a.paper, cfg=fmt.load(), lang=a.lang)
    print(f"wrote {a.out}")


def cmd_playtests(a):
    from . import playtests
    print(playtests.report(Path(a.dir) if a.dir else None))


def cmd_update(a):
    from . import cards
    print(f"new data version {cards.update_data()}: recalibrate with 'manaforge calibrate'")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="manaforge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    paper = lambda p: p.add_argument("--paper", choices=["a4", "letter"], default="a4")
    lang = lambda p: p.add_argument("--lang", choices=["en", "it"], default="en", help="rules sheet language")
    card_lang = lambda p: p.add_argument("--card-lang", choices=LANGS, default="en", help="card image language (Scryfall code); English is the default and the fallback")
    min_dpi = lambda p: p.add_argument("--min-dpi", type=float, default=200, help="minimum real image resolution at 63 mm; below it the next source, then English (default 200)")
    p = sub.add_parser("validate", help="check decklists against format.yaml (exit 1 if illegal)")
    p.add_argument("inputs", nargs="+")
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("print", help="decklist files / '-' for stdin -> proxy PDF")
    p.add_argument("inputs", nargs="+")
    p.add_argument("-o", "--out", default="proxies.pdf")
    paper(p); lang(p); card_lang(p); min_dpi(p)
    p.add_argument("--bleed", type=float, default=0, help="mm")
    p.add_argument("--gap", type=float, default=0, help="mm")
    p.add_argument("--split", action="store_true", help="one PDF per deck")
    p.add_argument("--once", action="store_true", help="print each card once")
    p.add_argument("--rate", action="store_true", help="put the heuristic rating on the cover")
    p.add_argument("--spellbook", action="store_true", help="use the Commander Spellbook bracket estimate")
    p.set_defaults(fn=cmd_print)
    p = sub.add_parser("forge", help="forge seeded decks around a commander -> PDF")
    p.add_argument("--seed", type=int)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--commander", help="fix the commander by name")
    p.add_argument("--no-playgroup", action="store_true", help="skip Playgroup.gg commander stats (fun/salt weighting, Elo-adjusted power)")
    p.add_argument("--power", type=int, default=3, choices=range(1, 6), help="target power level 1-5 (mean card quality + game-changer cap); same level = balanced decks")
    p.add_argument("--no-rate", action="store_true")
    p.add_argument("--spellbook", action="store_true")
    paper(p); lang(p); card_lang(p); min_dpi(p)
    p.add_argument("-o", "--out", default="forged.pdf")
    p.set_defaults(fn=cmd_forge)
    p = sub.add_parser("rebalance", help="fewest swaps that put decklists on a power level (same commander and land deck)")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--power", type=int, default=3, choices=range(1, 6))
    p.add_argument("--no-playgroup", action="store_true")
    p.add_argument("--write", action="store_true", help="overwrite the decklist files")
    p.set_defaults(fn=cmd_rebalance)
    p = sub.add_parser("estimate", help="hypergeometric tables for decklists")
    p.add_argument("inputs", nargs="*", default=[])
    p.add_argument("--land-size", type=int, default=18)
    p.set_defaults(fn=cmd_estimate)
    p = sub.add_parser("calibrate", help="recompute the star cut-offs from 50 forged decks")
    p.add_argument("-n", type=int, default=50)
    p.add_argument("--spellbook", action="store_true")
    p.set_defaults(fn=cmd_calibrate)
    p = sub.add_parser("rules", help="rules reference sheet PDF from rules/regolamento*.md + format.yaml")
    p.add_argument("-o", "--out", default="rules.pdf")
    paper(p); lang(p)
    p.set_defaults(fn=cmd_rules)
    p = sub.add_parser("playtests", help="win rates by rule variant from playtests/*.yaml")
    p.add_argument("dir", nargs="?")
    p.set_defaults(fn=cmd_playtests)
    sub.add_parser("update-data", help="point the cache at the newest Scryfall oracle_cards bulk file").set_defaults(fn=cmd_update)
    a = ap.parse_args(argv)
    try:
        a.fn(a)
    except (ValueError, KeyError) as e:
        sys.exit(f"error: {e}")
