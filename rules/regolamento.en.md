# Mana Commander – Rules (version {version})

Casual 1v1 format for Magic: The Gathering. Commander in miniature, with the lands in a separate deck that is used only through the commander.

English mirror of `regolamento.md`, which is the source. Text in braces, like `{life}`, is filled in from `format.yaml`. There are no open points: every rule below is final for this version.

## 1. The idea in brief

- A small main deck with no lands.
- A separate land deck, like the Will cards of Force of Will or the Energy of Pokémon Pocket.
- There is no land drop from hand: the commander taps to put one land onto the battlefield each turn.
- Anything not written here follows the normal rules of Magic and Commander.

## 2. Deck building

### Commander

- A legendary creature or a planeswalker. It starts in the command zone.
- Color identity as in Commander.

### Main deck

- {main_min} to {main_max} cards, commander excluded.
- No lands. Singleton: one copy per name.
- Every card must fit the commander's color identity.

### Land deck

- {land_min} to {land_max} lands.
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

## 3. Game setup

1. Each player puts their commander in the command zone.
2. Shuffle the main deck and the land deck, each on its own.
3. Put the land deck face down next to the library. The number of cards left is public information, the contents are not.
4. Each player starts at {life} life.
5. Draw an opening hand of {hand} cards from the main deck.
6. Mulligan: shuffle and draw one card fewer for each mulligan, starting from {hand}. For each mulligan after the first, after drawing, put one card from your hand on the bottom of the main deck (London style). The first mulligan is free.
7. The player who goes first skips their first draw.

## 4. The turn

The structure is Magic's, with these differences:

- Draw: one card from the main deck. Never from the land deck.
- Lands: there is no land drop. Lands arrive only through the commander (section 5) and card effects (section 6).
- No land is ever drawn. A searched land that the text sends to your hand (section 6) stays in your hand and cannot be played.

## 5. The commander and the land deck

**Commander ability (format rule).** Once per turn, tap your commander: {ability}

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

## 6. Rules on lands and libraries

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

## 7. How to win and lose

- Life at 0 or less.
- 21 commander damage from the same commander.
- Drawing from an empty main deck. An empty land deck does not lose the game.
- Poison and other conditions as in the normal rules.

## 8. Why these numbers (design notes)

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

## 9. Final choices

1. Starting life: {life}.
2. The land put onto the battlefield by the commander enters {enters}.
3. The commander ability looks only at the top card of the land deck (no look-at-2 variant).
4. Ban list: the one in section 2.
5. Land destruction: legal (section 6).
