from manaforge import http


def test_http_cache_and_rate_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("MANAFORGE_CACHE", str(tmp_path))
    calls, waits, seen = [], [], []

    class Resp:
        def read(self): return b'{"a": 1}'
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_urlopen(req, *a, **k):
        calls.append(req.full_url); seen.append((req.get_header("User-agent"), req.get_header("Accept"))); return Resp()

    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(http.time, "sleep", waits.append)
    monkeypatch.setattr(http.time, "monotonic", lambda: 100.0)
    http._last.clear()
    assert http.get("http://h/a") == b'{"a": 1}' and http.get("http://h/a") == b'{"a": 1}'
    assert len(calls) == 1
    http.get("http://h/b")
    assert max(waits) >= 1.0  # unknown hosts: 1 s
    waits.clear()
    http.get("https://api.scryfall.com/x"); http.get("https://api.scryfall.com/y")
    assert 0 < max(waits) <= 0.1  # Scryfall: 100 ms
    assert http.post_json("http://h/p", {"k": 1}) == {"a": 1} and http.post_json("http://h/p", {"k": 1}) == {"a": 1}
    assert calls.count("http://h/p") == 1  # POST cached by body
    assert {u for u, _ in seen} == {"ManaForge/0.1 (personal proxy tool)"} and all(a for _, a in seen)  # Accept always set
