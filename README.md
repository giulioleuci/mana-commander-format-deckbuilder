# ManaForge

Proxy printer, seeded deck forge and rules workbench for **Mana Commander**, a custom 1v1 Magic: The Gathering format
(a small commander deck plus a separate land deck that only the commander can use). A sibling of PokéForge.

The full rules are below. The Italian source is [`rules/regolamento.md`](rules/regolamento.md), the English text is [`rules/regolamento.en.md`](rules/regolamento.en.md). Every number lives in [`format.yaml`](format.yaml); the validator, the forge and the printed rules sheet all read it.

## Rules (version 0.1)

Casual 1v1 format for Magic: The Gathering. Commander in miniature, with the lands in a separate deck that is used only through the commander.

There are no open points: every rule below is final for this version.

### 1. The idea in brief

- A small main deck with no lands.
- A separate land deck, like the Will cards of Force of Will or the Energy of Pokémon Pocket.
- There is no land drop from hand: the commander taps to put one land onto the battlefield each turn.
- Anything not written here follows the normal rules of Magic and Commander.

### 2. Deck building

#### Commander

- A legendary creature or a planeswalker. It starts in the command zone.
- Color identity as in Commander.

#### Main deck

- 30 to 40 cards, commander excluded.
- No lands. Singleton: one copy per name.
- Every card must fit the commander's color identity.

#### Land deck

- 15 to 20 lands.
- Basic lands: unlimited, within the commander's color identity.
- Non-basic lands: at most 1 copy per name and, in total, at most a quarter of the land deck rounded up (4 with 15-16 cards, 5 with 17-20 cards).
- Non-basic lands must also fit the color identity.

### Banned cards

- Every card banned in Commander.
- Cards that reveal or exile cards until one with a given property is found (Cascade, Hermit Druid, Animist's Awakening and the like).
- Cards that grant extra land drops or let you play lands from zones other than your hand (Exploration, Oracle of Mul Daya, Crucible of Worlds and the like).
- Fast mana: only these four cards are banned, by name: Sol Ring, Mana Crypt, Mana Vault, Grim Monolith. No other card is banned for this reason.
- The list is final for this version and changes only with a new version of the rules.
- A card with a land face (MDFC) counts as a land: it cannot be in the main deck.

### 3. Game setup

1. Each player puts their commander in the command zone.
2. Shuffle the main deck and the land deck, each on its own.
3. Put the land deck face down next to the library. The number of cards left is public information, the contents are not.
4. Each player starts at 30 life.
5. Draw an opening hand of 5 cards from the main deck.
6. Mulligan: shuffle and draw one card fewer for each mulligan, starting from 5. For each mulligan after the first, after drawing, put one card from your hand on the bottom of the main deck (London style). The first mulligan is free.
7. The player who goes first skips their first draw.

### 4. The turn

The structure is Magic's, with these differences:

- Draw: one card from the main deck. Never from the land deck.
- Lands: there is no land drop. Lands arrive only through the commander (section 5) and card effects (section 6).
- No land is ever drawn. A searched land that the text sends to your hand (section 6) stays in your hand and cannot be played.

### 5. The commander and the land deck

**Commander ability (format rule).** Once per turn, tap your commander: put the top card of the land deck onto the battlefield, untapped.

- The ability works from the command zone and from the battlefield.
- From the command zone the commander is tapped by turning the card sideways. It untaps in your untap step like any permanent.
- On the battlefield the ability ignores summoning sickness, but a tapped commander cannot attack or use other {T} abilities. A commander with vigilance can still attack.
- If the commander leaves the battlefield and returns to the command zone, it starts untapped.
- The ability does not count as a land drop and does not use the stack.
- If the land deck is empty the ability does nothing.
- If the commander is exiled and does not return to the command zone, you have lost your only source of lands. You play on with what is already there.
- Effects that search for or put your commander into play work normally.

**Commander tax.** As in Commander: +2 for each cast from the command zone.

**Commander damage.** As in Commander: 21 damage from the same commander eliminates a player.

### 6. Rules on lands and libraries

**The land deck is not the library.**

- The land deck is a separate zone. It is not the library, not exile, not the sideboard.
- Effects that mention the "library" affect only the main deck. Mill, scry, surveil and the like hit only the main deck.
- Effects that shuffle or search the land deck must say so (see below).

**Searching for lands.** Any effect that searches your library for a land, or a land of a given type, searches the land deck instead.

- After the search, shuffle the land deck, not the library.
- Searched lands enter the zone the text names (battlefield, hand). If the text says hand, the land stays in hand and cannot be played: the card is legal but effectively useless.

**Lands that would return to hand or library.** If an effect puts a land back into a hand or library, its owner puts it on the top or the bottom of the land deck, their choice.

**Lands that trigger landfall.** Lands put onto the battlefield by the commander or by an effect trigger landfall as usual.

**Land destruction.** It is legal and has no special rules. Armageddon, Stone Rain and the like are strong because lands arrive one at a time: whoever plays them knows it. The deck forge never picks them.

**Effects that name drawn cards.** Effects that talk about drawn lands or lands in the library do nothing, because the main deck contains no lands.

### 7. How to win and lose

- Life at 0 or less.
- 21 commander damage from the same commander.
- Drawing from an empty main deck. An empty land deck does not lose the game.
- Poison and other conditions as in the normal rules.

### 8. Why these numbers (design notes)

- With an 18-card land deck, at one land per turn, 5 lands are in play by turn 5.
- Probability of having at least 1 non-basic land by turn 5 (18 cards in the land deck):
  - 2 non-basic: 49% (mean 0.6)
  - 3 non-basic: 65% (mean 0.8)
  - 4 non-basic: 77% (mean 1.1)
  - 5 non-basic: 85% (mean 1.4)
  - 6 non-basic: 91% (mean 1.7)
- With 4 non-basic there is on average about 1 special land by turn 5 without it being guaranteed, so the land deck remains a deck of basic lands. With 6 or more it becomes nearly certain.
- One land per turn gives the pace of normal Magic: there is no free ramp, but you never miss a land drop.
- The commander is always useful as a land source. The cost is that if you cast it or attack with it, you must decide whether to tap it for the land.

### 9. Final choices

1. Starting life: 30.
2. The land put onto the battlefield by the commander enters untapped.
3. The commander ability looks only at the top card of the land deck (no look-at-2 variant).
4. Ban list: the one in section 2.
5. Land destruction: legal (section 6).

## Use

```
pip install -e ".[dev]"
manaforge validate deck.txt                 # legal? plus rules-gap flags
manaforge print deck.txt -o proxies.pdf     # 63x88 mm, 3x3, cut marks; commander / main deck / land deck as labelled sections
manaforge print deck.txt --card-lang it     # Italian images when a sharp one exists, English otherwise (noted on the cover)
manaforge forge --seed 7 -o forged.pdf      # seeded deck around a commander; --commander "Name" to fix it, --power 1-5 (default 3)
manaforge calibrate                         # star cut-offs from 50 forged decks (do this once per data version)
manaforge rebalance deck.txt --write         # fewest swaps onto power 3 (same commander + land deck); --power N
manaforge estimate deck.txt                 # hypergeometric tables + synergy report (engines, dead payoffs, template gaps)
manaforge rules --lang it -o rules.pdf      # the rules sheet, filled in from format.yaml
manaforge playtests                         # win rates by rule variant
```

Decklist text: `Commander` / `Main` / `Lands` headers, lines like `1 Sol Ring` (a trailing `(SET) 123` is ignored). Without headers,
lands go to the land deck. Deck URLs are **not** supported: Moxfield's and Archidekt's API terms are not verified, so paste the text.

## How the forge builds a deck

1. **Traits** (`synergy.py`): every card *gives* and *wants* traits (tokens, fodder, counters, artifacts, enchantments, spells,
   graveyard, lifegain, landfall, blink, creatures, the commander's tribes), read from oracle text and type line. A want grows
   with the number of givers in the deck; a want with no givers is a **dead payoff** (antisynergy); wipes in a go-wide deck and
   graveyard hate in a graveyard deck are antisynergy too. The commander counts triple, since it is always available. Landfall has a
   baseline of givers because the commander drops a land every turn. Modelled on Decks of KeyForge's
   [SAS](https://decksofkeyforge.com/about/sas) (traits, synergies, antisynergies that scale with trait count) and EDHREC's
   per-commander [synergy/lift](https://edhrec.com/articles/from-synergy-to-lift-the-math-behind-edhrecs-new-era).
2. **Themes** (Houses): the commander's wants first (weight 3), then its gives. A theme needs at least 12 cards, 4 payoffs and 4 enablers,
   or it is a pile. One to three themes are chosen, as in KeyForge's three Houses and the 8x8 idea of a few packages plus staples.
3. **Objective** = synergy + role template (5-8 ramp, draw and removal, 0-2 wipes, 2-4 protection, 3-6 win conditions, 4-7 land search, 10-22
   creatures: the 10/10/10-per-99 template scaled to 36 cards) + curve target (4/9/9/7/4/3 by mana value).
4. **Power held fixed**: mean card quality (from popularity rank) is pinned to the level's target, and the game-changer count
   to the level's number (`--power`: 1 = 0.35/0 GC ... 3 = 0.55/1 ... 5 = 0.75/4). Synergy is maximised *at* a power level, not
   instead of it, so decks from the same level are matched opponents (KeyForge: every deck is unique, but the field stays balanced).
5. **Search**: a seeded popularity-weighted start, then 3000 steps of simulated annealing over single-card swaps (one-deck version of
   the evolutionary deckbuilding of García-Sánchez et al., [CIG 2016](https://produccioncientifica.ugr.es/documentos/640d406a4531f424f8818a16)).
6. **Commander data** ([Playgroup.gg](https://playgroup.gg) public API, on by default, `--no-playgroup` to skip): a random
   commander is drawn weighted by (pilot fun - opponent salt)^2, and the card-quality target drops by 0.03 per 100 Elo above 1500
   (a strong commander gets a weaker 36, since it is in every game). Commanders with fewer than 50 tracked games, or no data, are
   neutral. The Elo comes from mostly multiplayer games and the 0.03 is a knob to tune from playtests, not a measured value. There is no
   per-card source: no public API publishes per-card Commander win rates (EDHTop16's GraphQL accepts persisted queries only, Playgroup's
   card pages have no win rate, 17lands covers Limited only), so card power stays the popularity proxy.
7. **Fun filter** (`generator.unfun_patterns`): land destruction, extra turns and lock pieces are legal but never forged.
   Cards that care about colors outside the identity are skipped.

**Rebalancing an existing deck** (`manaforge rebalance`) runs the same objective from the deck itself: each swap must earn 5 synergy
points on its own, but power is a wall: mean quality within 0.01 of the (Elo-adjusted) target, the exact game-changer count,
and, at power 3, a heuristic score inside the 3/5 star band. Best of 3 annealing restarts.

Same seed + same data, same deck: the Playgroup table is cached a week and is part of the deck id (rng seeded by string, pools sorted by name, trait tuples sorted). About 1-2 s per deck.

## Rating

Stars 1-5 are relative to other forged decks (quintiles of a 50-deck calibration batch), from a **heuristic**: mana curve,
tag coverage (draw, removal, land search, win conditions, protection), game changers and the bracket. `--spellbook` uses the
Commander Spellbook bracket estimate. Scorers are pluggable: `rating.SCORERS["name"] = fn(deck, cfg) -> float`.
No LLM, no simulator.

## Flags

`manaforge validate` prints these as `!` lines and the forge puts them on the cover. They are warnings about judgement calls, not rule questions:

- **MDFC lands** in the main deck: they count as lands, so they are illegal (unless `main_deck.allow_mdfc_lands`).
- **No land search** in the main deck: if the commander is exiled early you have no land source.
- **Commander-tutor effects**: allowed, flagged.
- **Fast mana candidates**: only the four named cards are banned; other cheap mana rocks are flagged for review.

## Playtesting

Log each game as `playtests/<date>-<n>.yaml` (copy `playtests/_template.yaml`), then run `manaforge playtests` to compare win rates by rule variant. Tag rule versions as `v0.1`, `v0.2`, ... and bump `version` in `format.yaml` to match.

## Card images and print quality

`--card-lang` picks the language (Scryfall codes; English is the default and the fallback). For each card the tool tries, in order,
and takes the first image whose **real** pixel width gives at least `--min-dpi` (default 200) at 63 mm:

1. Scryfall, a printing in the requested language flagged `highres_scan`.
2. [Gatherer](https://gatherer.wizards.com) (official Wizards scans, about 650 px wide = 240-260 dpi), for the same printings.
3. The same two sources in English.
4. Last resort: the best blurry image, printed anyway and marked `LOW source quality` on the cover.

Why not just check pixels on Scryfall images: their PNGs are always 745x1040, even when the underlying scan is `lowres`, and some
printings are `placeholder` ("image not available") graphics; those are skipped. Nothing is ever drawn on a card: no watermark, no
badge. A fallback is only noted on the cover page (`[no it print good enough: English card]`).

## Data and attribution

Card data and images come from [Scryfall](https://scryfall.com) (`oracle_cards` bulk file, downloaded once and cached; images and
non-English printings on demand, cached) and, for sharper non-English scans, from Gatherer (on demand, cached, 1 request/s). Requests carry a clear User-Agent and respect Scryfall's rate limits (search: 2/s).
Nothing is mirrored in bulk. Combo and bracket data come from the [Commander Spellbook](https://commanderspellbook.com) API,
cached. Commander Elo, win rate, fun and salt come from the [Playgroup.gg](https://playgroup.gg) public API (CC BY 4.0,
[terms](https://playgroup.gg/legal); ~55 requests at 1/s, cached a week); every cover that uses them links the commander's Playgroup page. Card text and images are property of Wizards of the Coast; ManaForge is unofficial.

**Unofficial proxies for personal playtesting, not for sale.** The notice is printed on every page.

## Tests

`pytest`. The validator has a legal and illegal fixture for every rule (`tests/fixtures/decks/`, `tests/test_decks.py`); the forge
tests check determinism (including across `PYTHONHASHSEED`), legality, no dead cards, no piles and clone rejection on real data.
