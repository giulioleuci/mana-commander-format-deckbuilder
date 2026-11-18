"""Commander stats from the Playgroup.gg public API: Elo, win rate, fun and salt from tracked games (mostly multiplayer pods).

Licence: CC BY 4.0 (https://playgroup.gg/legal): credit Playgroup.gg with a link to the commander page (printed on the cover).
Commanders only: no public source publishes per-card Commander win rates (EDHTop16's GraphQL takes persisted queries only,
Playgroup's card pages carry play data but no win rate, 17lands is Limited), so card power stays the popularity proxy."""
from . import http

URL = "https://playgroup.gg/api/public/v1/commanders.json?limit=100&page={}"  # the API caps limit at 100: ~55 pages, 1 req/s, cached a week
WEEK = 7 * 86400
MIN_GAMES = 50  # below this the numbers are noise
_STATS: dict | None = None


def stats() -> dict[str, dict]:
    """Commander name -> {elo, win_rate, games, fun, salt, url}, for commanders with >= MIN_GAMES games. {} when offline."""
    global _STATS
    if _STATS is None:
        out, page = {}, 1
        try:
            while rows := http.get_json(URL.format(page), WEEK):
                for r in rows:
                    if r["game_played_count"] >= MIN_GAMES:
                        out[r["name"]] = {"elo": r["global_elo"], "win_rate": r["game_win_count"] / r["game_played_count"],
                                          "games": r["game_played_count"], "fun": float(r["average_fun_rating"]),
                                          "salt": float(r["average_salt_rating"]), "url": r["playgroup_url"]}
                page += 1
        except Exception:  # offline / API change: a partial list would make forging depend on where it broke
            out = {}
        _STATS = out
    return _STATS


def of(name: str, table: dict[str, dict]) -> dict | None:
    return table.get(name) or table.get(name.split(" // ")[0])


def line(name: str, s: dict) -> str:
    return (f"Commander data (Playgroup.gg, CC BY 4.0): Elo {s['elo']}, win rate {100 * s['win_rate']:.0f}% over {s['games']} games "
            f"(mostly multiplayer pods), fun {s['fun']:.2f}/5, salt {s['salt']:.2f}/5. {s['url']}")
