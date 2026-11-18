from manaforge import forge as F, http, playgroup, synergy as S


def row(name, games, elo=1500, fun="4.0", salt="1.5"):
    return {"name": name, "game_played_count": games, "game_win_count": games // 4, "global_elo": elo, "average_fun_rating": fun,
            "average_salt_rating": salt, "playgroup_url": f"https://playgroup.gg/commanders/{name}"}


def test_stats_pages_filter_and_offline(monkeypatch):
    pages = {1: [row("A", 100), row("Tiny", 3)], 2: [row("B // B2", 60)], 3: []}
    monkeypatch.setattr(http, "get_json", lambda url, age: pages[int(url.rsplit("=", 1)[1])])
    monkeypatch.setattr(playgroup, "_STATS", None)
    t = playgroup.stats()
    assert set(t) == {"A", "B // B2"} and t["A"]["win_rate"] == 0.25 and t["A"]["fun"] == 4.0  # < MIN_GAMES dropped
    assert playgroup.of("A", t) and not playgroup.of("Tiny", t)

    def boom(url, age):
        if url.endswith("=2"):
            raise OSError("offline")
        return pages[1]
    monkeypatch.setattr(http, "get_json", boom)
    monkeypatch.setattr(playgroup, "_STATS", None)
    assert playgroup.stats() == {}  # never a partial table


def test_strong_commander_gets_a_weaker_deck(real_db):
    cmd = "Krenko, Mob Boss"
    q = lambda d: sum(S.quality(c) for c, _ in d.main) / len(d.main)
    base = F.forge(1, real_db, commander=cmd)
    stat = {"elo": 1800, "win_rate": 0.4, "games": 500, "fun": 4.0, "salt": 1.5, "url": "u"}
    strong = F.forge(1, real_db, commander=cmd, commander_stats={cmd: stat})  # Elo 1800: target 0.55 - 0.09
    assert q(strong) < q(base) - 0.05 and "Playgroup.gg" in strong.meta["synergy"][-1] and strong.meta["id"] != base.meta["id"]
