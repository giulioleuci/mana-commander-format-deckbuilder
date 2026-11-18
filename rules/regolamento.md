# Mana Commander – Regolamento (versione {version})

Formato casual 1v1 per Magic: The Gathering. Commander in miniatura, con le terre in un mazzo separato che si usa solo tramite il comandante.

Fonte originale in italiano. Il testo tra graffe, come `{life}`, viene riempito da `format.yaml`. Specchio inglese: `regolamento.en.md`. Non ci sono punti aperti: ogni regola qui sotto è definitiva per questa versione.

## 1. Idea in breve

- Mazzo principale piccolo, senza terre.
- Mazzo terre separato, come le Volontà di Force of Will o le energie di Pokémon Pocket.
- Non esiste la giocata di terra dalla mano: il comandante tappandosi mette in gioco una terra a turno.
- Per tutto ciò che non è scritto qui valgono le regole normali di Magic e di Commander.

## 2. Costruzione dei mazzi

### Comandante

- Una creatura leggendaria o un planeswalker. Sta nella zona di comando.
- Identità di colore come in Commander.

### Mazzo principale

- Da {main_min} a {main_max} carte, comandante escluso.
- Nessuna terra. Singleton: una sola copia per nome.
- Tutte le carte devono rispettare l'identità di colore del comandante.

### Mazzo terre

- Da {land_min} a {land_max} terre.
- Terre base: illimitate, entro l'identità di colore del comandante.
- Terre non base: massimo 1 copia per nome e, in totale, al massimo un quarto del mazzo terre arrotondato per eccesso (4 con 15-16 carte, 5 con 17-20 carte).
- Anche le terre non base devono rispettare l'identità di colore.

### Carte vietate

- Tutte le carte vietate in Commander.
- Le carte che rivelano o esiliano carte finché non se ne trova una con una certa caratteristica (Cascade, Hermit Druid, Animist's Awakening e simili).
- Le carte che concedono giocate di terra aggiuntive o permettono di giocare terre da zone diverse dalla mano (Exploration, Oracle of Mul Daya, Crucible of Worlds e simili).
- Il mana veloce: sono vietate solo queste quattro carte per nome: Sol Ring, Mana Crypt, Mana Vault, Grim Monolith. Nessun'altra carta è vietata per questo motivo.
- La lista è definitiva per questa versione e cambia solo con una nuova versione del regolamento.
- Una carta con una faccia terra (MDFC) conta come terra: non può stare nel mazzo principale.

## 3. Preparazione della partita

1. Ogni giocatore mette il comandante nella zona di comando.
2. Si mescola il mazzo principale e il mazzo terre, ciascuno separatamente.
3. Si mette il mazzo terre a faccia in giù accanto alla libreria. Il numero di carte rimaste è informazione pubblica, il contenuto no.
4. Ogni giocatore parte con {life} vita.
5. Si pesca una mano di {hand} carte dal mazzo principale.
6. Mulligan: si mescola e si pesca una carta in meno a ogni mulligan, partendo da {hand}. A ogni mulligan oltre il primo, dopo aver pescato si mette una carta della mano in fondo al mazzo principale (stile London). Il primo mulligan è gratuito.
7. Il giocatore che inizia salta la prima pesca.

## 4. Il turno

La struttura è quella di Magic, con queste differenze:

- Pesca: una carta dal mazzo principale. Mai dal mazzo terre.
- Terre: non c'è la giocata di terra. Le terre arrivano solo tramite il comandante (sezione 5) e gli effetti delle carte (sezione 6).
- Nessuna terra viene mai pescata. Una terra cercata che il testo manda in mano (sezione 6) resta in mano e non può essere giocata.

## 5. Il comandante e il mazzo terre

**Abilità del comandante (regola del formato).** Una volta per turno, tappa il tuo comandante: {ability}

- L'abilità funziona sia dalla zona di comando sia sul campo di battaglia.
- Dalla zona di comando il comandante si tappa girando la carta di lato. Si stappa nel tuo passo di stap come ogni permanente.
- Sul campo di battaglia l'abilità ignora la summoning sickness, ma il comandante tappato non può attaccare né usare altre abilità con {T}. Se il comandante ha vigilanza può attaccare comunque.
- Se il comandante lascia il campo e torna nella zona di comando, ricomincia stappato.
- L'abilità non conta come giocata di terra e non usa lo stack.
- Se il mazzo terre è vuoto l'abilità non fa nulla.
- Se il comandante è esiliato senza tornare nella zona di comando, hai perso la tua unica fonte di terre. Si gioca con quello che c'è già.
- Gli effetti che cercano o rimettono in gioco il comandante funzionano normalmente.

**Commander tax.** Resta come in Commander: +2 a ogni lancio dalla zona di comando.

**Danno da comandante.** Come in Commander: 21 danni dallo stesso comandante eliminano il giocatore.

## 6. Regole sulle terre e sulle librerie

**Il mazzo terre non è la libreria.**

- Il mazzo terre è una zona separata. Non è la libreria, non è l'esilio, non è il sideboard.
- Gli effetti che parlano di "libreria" riguardano solo il mazzo principale. Mill, scry, sorveglia e simili colpiscono solo il mazzo principale.
- Gli effetti che mescolano o cercano nel mazzo terre devono dirlo (vedi sotto).

**Cercare terre.** Qualunque effetto che cerca una terra, o una terra di un certo tipo, nella tua libreria cerca invece nel mazzo terre.

- Dopo la ricerca si mescola il mazzo terre, non la libreria.
- Le terre cercate entrano nella zona indicata dal testo (campo, mano). Se il testo dice mano, la terra resta in mano e non può essere giocata: la carta è legale ma di fatto inutile.

**Terre che dovrebbero tornare in mano o in libreria.** Se un effetto rimette una terra in mano o in libreria, il proprietario la mette in cima o in fondo al mazzo terre, a sua scelta.

**Terre che attivano il landfall.** Le terre messe in gioco dal comandante o da un effetto attivano il landfall come sempre.

**Distruzione di terre.** È legale e non ha regole speciali. Armageddon, Stone Rain e simili sono forti perché le terre arrivano una per volta: chi li gioca lo sa. Il generatore di mazzi non li sceglie mai.

**Effetti che nominano le carte pescate.** Gli effetti che parlano di terre pescate o di terre nella libreria non fanno nulla, perché il mazzo principale non contiene terre.

## 7. Come si vince e si perde

- Vita a 0 o meno.
- 21 danni da comandante dallo stesso comandante.
- Pescare da un mazzo principale vuoto. Il mazzo terre vuoto non fa perdere.
- Veleno e altre condizioni come nelle regole normali.

## 8. Perché questi numeri (note di design)

- Con un mazzo terre da 18 carte, a ritmo di una terra a turno, entro il turno 5 si mettono in gioco 5 terre.
- Probabilità di avere almeno 1 terra non base entro il turno 5 (18 carte nel mazzo terre):
  - 2 non base: 49% (media 0,6)
  - 3 non base: 65% (media 0,8)
  - 4 non base: 77% (media 1,1)
  - 5 non base: 85% (media 1,4)
  - 6 non base: 91% (media 1,7)
- Con 4 non base c'è in media circa 1 terra speciale entro il turno 5 senza che sia garantita, quindi il mazzo terre resta un mazzo di terre base. Con 6 o più diventa quasi certa.
- Una terra a turno dà il ritmo di un Magic normale: non c'è ramp gratis, ma non si salta mai una terra.
- Il comandante resta sempre utile come fonte di terre. Il costo è che, se lo si lancia o lo si fa attaccare, bisogna decidere se tapparlo per la terra.

## 9. Scelte definitive

1. Vita iniziale: {life}.
2. La terra messa in gioco dal comandante entra {enters}.
3. L'abilità del comandante guarda solo la prima carta del mazzo terre (nessuna variante con le prime 2).
4. Lista dei divieti: quella della sezione 2.
5. Distruzione di terre: legale (sezione 6).
