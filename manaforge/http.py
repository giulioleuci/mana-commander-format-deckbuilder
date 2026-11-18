"""Cached, rate-limited GET/POST (per-host gap, disk cache, fixed User-Agent + Accept)."""
import hashlib, json, os, time, urllib.parse, urllib.request
from pathlib import Path

UA = "ManaForge/0.1 (personal proxy tool)"
GAP = {"api.scryfall.com": 0.1, "cards.scryfall.io": 0.1, "data.scryfall.io": 0.1}  # Scryfall asks for 50-100 ms; search is 500 ms
DEFAULT_GAP = 1.0
_last: dict[str, float] = {}


def cache_dir() -> Path:
    return Path(os.environ.get("MANAFORGE_CACHE") or Path.home() / ".cache" / "manaforge")


def _fetch(req: urllib.request.Request, key: str, max_age: float | None) -> bytes:
    f = cache_dir() / "http" / hashlib.sha256(key.encode()).hexdigest()
    if f.exists() and (max_age is None or time.time() - f.stat().st_mtime <= max_age):
        return f.read_bytes()
    host = urllib.parse.urlsplit(req.full_url).netloc
    if host in _last and (wait := (0.5 if "/cards/search" in req.full_url else GAP.get(host, DEFAULT_GAP)) - (time.monotonic() - _last[host])) > 0:
        time.sleep(wait)
    _last[host] = time.monotonic()
    with urllib.request.urlopen(req) as r:
        data = r.read()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data)
    return data


def get(url: str, max_age: float | None = None) -> bytes:
    return _fetch(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"}), url, max_age)


def get_json(url: str, max_age: float | None = None):
    return json.loads(get(url, max_age))


def post_json(url: str, body, max_age: float | None = None):
    data = json.dumps(body, sort_keys=True).encode()
    req = urllib.request.Request(url, data, {"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"})
    return json.loads(_fetch(req, url + "|" + data.decode(), max_age))
