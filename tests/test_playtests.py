import pytest
from manaforge import cli, playtests

GAME = """id: {id}
date: 2026-11-20
format_version: "0.1"
variant: {{life: {life}, land_enters: {enters}, look_at_top: 1}}
decks: [aaaa1111, bbbb2222]
first_player: {first}
winner: {winner}
turns: {turns}
notes: ""
"""


def write(d, n, **kw):
    d.mkdir(exist_ok=True)
    (d / f"{n}.yaml").write_text(GAME.format(**{"id": n, "life": 30, "enters": "untapped", "first": "aaaa1111", "winner": "aaaa1111", "turns": 8, **kw}))


def test_aggregates_by_variant(tmp_path):
    write(tmp_path, "g1"); write(tmp_path, "g2", winner="bbbb2222", turns=10); write(tmp_path, "g3", winner="draw", turns=12)
    write(tmp_path, "g4", life=25, winner="bbbb2222", first="bbbb2222", turns=6)
    (tmp_path / "_template.yaml").write_text("not: a game")  # underscore files are ignored
    rows = {r["variant"]: r for r in playtests.aggregate(playtests.load(tmp_path))}
    a = rows["v0.1 land_enters=untapped life=30 look_at_top=1"]
    assert (a["games"], a["draws"], a["avg_turns"], a["first_player_wins"], a["first_player_games"]) == (3, 1, 10.0, 1, 3)
    assert a["wins"] == {"aaaa1111": 1, "bbbb2222": 1}
    b = rows["v0.1 land_enters=untapped life=25 look_at_top=1"]
    assert b["games"] == 1 and b["first_player_wins"] == 1 and b["wins"] == {"bbbb2222": 1}


def test_rejects_a_winner_who_did_not_play(tmp_path):
    write(tmp_path, "bad", winner="cccc3333")
    with pytest.raises(ValueError, match="bad.yaml: winner cccc3333"):
        playtests.load(tmp_path)


def test_cli_prints_table(tmp_path, capsys):
    write(tmp_path, "g1"); write(tmp_path, "g2", winner="bbbb2222")
    cli.main(["playtests", str(tmp_path)])
    out = capsys.readouterr().out
    assert "life=30" in out and "2 games" in out and "first player won 1/2" in out


def test_empty_dir_is_not_an_error(tmp_path, capsys):
    cli.main(["playtests", str(tmp_path)])
    assert "no games" in capsys.readouterr().out
