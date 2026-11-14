"""Test regresi audit v2.12.9 — keamanan, integritas data, streaming, translate.

Setiap test di sini mengunci satu temuan audit supaya tidak kambuh.
"""

import asyncio
import os
import sqlite3
import sys

import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
for p in (ROOT_DIR, BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from starlette.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture DB terisolasi
# ---------------------------------------------------------------------------

@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    import database

    asyncio.run(database.close_db_pool())
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "audit.db"))
    asyncio.run(database.init_db())
    yield database
    asyncio.run(database.close_db_pool())


# ---------------------------------------------------------------------------
# B1 — netguard / SSRF
# ---------------------------------------------------------------------------

def test_netguard_blocks_local_and_private_hosts():
    import netguard

    for bad in (
        "http://127.0.0.1:8767/api/settings",
        "http://localhost/x",
        "http://[::1]/x",
        "http://[::ffff:127.0.0.1]/x",
        "http://10.0.0.5/x",
        "http://192.168.1.1/x",
        "http://169.254.169.254/latest/meta-data",
        "file:///etc/passwd",
        "ftp://example.com/x",
    ):
        with pytest.raises(netguard.UnsafeURL):
            netguard.assert_public_url(bad)


def test_netguard_allows_public_ip():
    import netguard

    netguard.assert_public_url("https://1.1.1.1/x")
    netguard.assert_public_url("https://example.com/x")


def test_httpx_hook_validates_every_redirect_hop(monkeypatch):
    import httpx
    import netguard

    calls = []

    def fake_assert(url):
        calls.append(url)
        if "127.0.0.1" in url:
            raise netguard.UnsafeURL("host lokal")

    monkeypatch.setattr(netguard, "assert_public_url", fake_assert)

    async def run():
        transport = httpx.MockTransport(
            lambda req: httpx.Response(302, headers={"location": "http://127.0.0.1:9/x"})
        )
        async with httpx.AsyncClient(
            transport=transport,
            follow_redirects=True,
            event_hooks={"request": [netguard.httpx_request_hook]},
        ) as client:
            with pytest.raises(netguard.UnsafeURL):
                await client.get("https://example.com/start")

    asyncio.run(run())
    assert len(calls) == 2, f"hook harus dipanggil di setiap hop, dapat: {calls}"
    assert "127.0.0.1" in calls[1]


def test_cross_origin_request_blocked():
    from backend.main import app

    client = TestClient(app, base_url="http://127.0.0.1:8767")
    r = client.get("/api/settings", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_host_header_rebinding_blocked():
    from backend.main import app

    client = TestClient(app, base_url="http://127.0.0.1:8767")
    r = client.get("/api/settings", headers={"Host": "evil.example:8767"})
    assert r.status_code == 403


def test_native_client_without_origin_allowed():
    from backend.main import app

    client = TestClient(app, base_url="http://127.0.0.1:8767")
    r = client.get("/api/ping")
    assert r.status_code == 200


def test_safe_sub_filename_cannot_escape_tempdir():
    import main

    for slug in ("../../etc/passwd", "/home/ubuntu/.config/autostart/x", "..\\..\\win"):
        name = main._safe_sub_filename(slug, 1, "https://cdn.example/sub.vtt")
        assert "/" not in name and "\\" not in name
        assert name == os.path.basename(name)


# ---------------------------------------------------------------------------
# B2 — database & endpoint
# ---------------------------------------------------------------------------

def test_failed_write_rolls_back_and_pool_stays_clean(temp_db):
    db = temp_db

    async def run():
        await db.add_history("rollback-x", "Judul Lama", 1, "sub")
        with pytest.raises(Exception):
            # title dict -> sqlite3.ProgrammingError di tengah transaksi
            await db.add_history("rollback-x", {"a": 1}, 2, "sub")
        for conn in db._pool:
            assert not conn.in_transaction, "koneksi kotor (transaksi terbuka) dikembalikan ke pool"
        # write berikutnya harus jalan, bukan 'database is locked'
        await db.add_history("rollback-y", "Judul Baru", 1, "sub")
        history = await db.get_history(limit=50)
        assert any(h["slug"] == "rollback-y" for h in history)

    asyncio.run(run())


def test_like_escape_helper():
    import database

    assert database._like_escape("%") == "\\%"
    assert database._like_escape("a_b") == "a\\_b"
    assert database._like_escape("a\\b") == "a\\\\b"


def test_wildcard_slug_does_not_wipe_episode_cache(temp_db):
    db = temp_db

    async def run():
        async with db._write_db() as conn:
            await conn.executemany(
                "INSERT INTO episode_cache(slug, ep, mode, master, variants, fetched_at) "
                "VALUES(?,?,?,?,?,?)",
                [
                    ("hianime:a", 1, "sub", "m", "[]", db._now()),
                    ("otakudesu:b", 1, "sub", "m", "[]", db._now()),
                ],
            )
            await conn.commit()
        await db.add_bookmark("%", "Wildcard")
        async with db._connect_db() as conn:
            cur = await conn.execute("SELECT COUNT(*) FROM episode_cache")
            count = (await cur.fetchone())[0]
        assert count == 2, "slug '%' tidak boleh menghapus seluruh episode_cache"

    asyncio.run(run())


def test_purge_keeps_rows_that_readers_still_use(temp_db):
    db = temp_db

    async def run():
        old = db._now() - 10 * 24 * 3600  # 10 hari: lewat TTL lama 6 jam
        async with db._write_db() as conn:
            await conn.execute(
                "INSERT INTO browse_cache(key, payload, fetched_at) VALUES(?,?,?)",
                ("audit-long-ttl", "{}", old),
            )
            await conn.commit()
        await db.purge_expired_caches()
        hit = await db.get_browse_cache("audit-long-ttl", ttl=30 * 24 * 3600)
        assert hit is not None, "baris 10 hari tidak boleh dibuang oleh sweeper"

    asyncio.run(run())


def test_seasonal_cache_id_distinguishes_default_and_now():
    import main

    assert main._seasonal_cache_id("") != main._seasonal_cache_id("now")
    assert main._seasonal_cache_id("now") == "now"
    assert main._seasonal_cache_id("prev") == "prev"


def test_bookmark_without_slug_returns_clean_error():
    from backend.main import app

    client = TestClient(app, base_url="http://127.0.0.1:8767")
    r = client.post("/api/bookmarks", json={})
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is False
    assert "Slug" in (body.get("error") or "")


# ---------------------------------------------------------------------------
# B3 — streaming, translate, parsing
# ---------------------------------------------------------------------------

def test_fmt_ts_never_emits_sixty_seconds():
    from api.translate import _fmt_ts

    assert _fmt_ts(3599.9997) == "01:00:00.000"
    assert _fmt_ts(59.9996) == "00:01:00.000"
    assert _fmt_ts(1.5) == "00:00:01.500"


def test_title_match_rejects_different_numeric_entry():
    from api.anilist import _match_title_tokens

    assert not _match_title_tokens("Jujutsu Kaisen 0", "Jujutsu Kaisen")
    assert not _match_title_tokens("Mob Psycho 100", "Mob Psycho 100 Season 2")
    assert _match_title_tokens("Attack on Titan 2nd Season", "Attack on Titan Season 2")


def test_otakudesu_desync_accepts_hex_key(monkeypatch):
    import api.otakudesu as otaku
    import api.desync as desync

    monkeypatch.setitem(sys.modules, "curl_cffi", None)  # paksa lewati jalur curl_cffi

    def boom():
        raise RuntimeError("httpx down")

    monkeypatch.setattr(otaku, "_get_otaku_client", boom)
    monkeypatch.setattr(desync, "tls_desync_request", lambda *a, **k: b"ab" * 32)

    out = otaku._fetch("https://putarin.biz/api/pk?n=abc")
    assert out == "ab" * 32


def test_translate_partial_timeout_keeps_cue_alignment():
    import api.translate as tr

    async def run():
        async def ok(value):
            return ([f"T:{value}"], True)

        async def slow():
            await asyncio.sleep(5)
            return (["slow"], True)

        tasks = [
            asyncio.ensure_future(ok("a")),
            asyncio.ensure_future(slow()),
            asyncio.ensure_future(ok("c")),
        ]
        return await tr._collect_batch_results(tasks, [["a"], ["b"], ["c"]], 0.2)

    results, timed_out = asyncio.run(run())
    assert timed_out == 1
    assert len(results) == 3, "jumlah batch tidak boleh menyusut saat timeout parsial"
    assert results[0] == (["T:a"], True)
    assert results[1] == (["b"], False), "batch timeout harus memakai teks asli di slotnya sendiri"
    assert results[2] == (["T:c"], True)


class _FakeStream:
    def __init__(self, chunks, fail_after=None, status=200, headers=None):
        self.chunks = chunks
        self.fail_after = fail_after
        self.status_code = status
        self.headers = headers or {"content-type": "video/mp2t"}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def aiter_bytes(self, n):
        for i, chunk in enumerate(self.chunks):
            if self.fail_after is not None and i >= self.fail_after:
                raise ConnectionError("upstream reset")
            yield chunk

    async def aread(self):
        return b"".join(self.chunks)


class _FakeClient:
    def __init__(self, streams):
        self.streams = list(streams)
        self.calls = 0

    def stream(self, method, url, headers=None):
        self.calls += 1
        return self.streams.pop(0)


def test_pipe_video_does_not_buffer_large_body(monkeypatch):
    import main

    chunks = [b"x" * (1024 * 1024)] * 8  # 8 MB
    fake = _FakeClient([_FakeStream(chunks)])
    monkeypatch.setattr(main, "_get_video_client", lambda url: fake)
    recorded = []
    monkeypatch.setattr(main, "_segment_cache_set", lambda url, mt, data: recorded.append(len(data)))

    async def run():
        total = 0
        async for ch in main._pipe_video("https://cdn.example/big.ts", ""):
            total += len(ch)
        return total

    total = asyncio.run(run())
    assert total == 8 * 1024 * 1024
    assert not recorded, "body > 6MB tidak boleh dikumpulkan untuk cache"


def test_pipe_video_no_retry_after_bytes_sent(monkeypatch):
    import main

    fake = _FakeClient(
        [
            _FakeStream([b"y" * (1024 * 1024), b"y" * (1024 * 1024)], fail_after=1),
            _FakeStream([b"y" * (1024 * 1024), b"y" * (1024 * 1024)], fail_after=1),
        ]
    )
    monkeypatch.setattr(main, "_get_video_client", lambda url: fake)

    async def run():
        got = 0
        with pytest.raises(Exception):
            async for ch in main._pipe_video("https://cdn.example/seg.ts", ""):
                got += len(ch)
        return got

    got = asyncio.run(run())
    assert fake.calls == 1, "tidak boleh retry setelah byte pertama terkirim"
    assert got == 1024 * 1024, "byte tidak boleh terkirim dua kali"
