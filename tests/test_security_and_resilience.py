"""Unit test untuk verifikasi keamanan (SSRF mitigation), resiliensi TLS desync,
dan proteksi rate limit AniList.
"""
import os
import sys
import pytest
import asyncio
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
import main
from main import app, _validate_external_proxy_url
from api import anilist as al
from api import desync

@pytest.mark.asyncio
async def test_ssrf_validator_blocks_internal_and_private_targets():
    """Memverifikasi bahwa _validate_external_proxy_url memblokir seluruh target lokal, loopback, dan privat."""
    bad_targets = [
        "http://127.0.0.1:8767/api/settings",
        "http://127.0.1.1/test",
        "http://localhost:8080/admin",
        "http://0.0.0.0:8767/api/ping",
        "http://[::1]:8767/",
        "http://10.0.0.1/router",
        "http://172.16.0.5/internal",
        "http://192.168.1.1/setup",
        "http://169.254.169.254/latest/meta-data/",
        "http://router.local/",
        "http://server.internal/",
    ]
    for url in bad_targets:
        with pytest.raises(HTTPException) as exc_info:
            _validate_external_proxy_url(url)
        assert exc_info.value.status_code == 403, f"URL {url} harus ditolak dengan 403!"


@pytest.mark.asyncio
async def test_ssrf_validator_blocks_invalid_schemes():
    """Memverifikasi penolakan skema non-HTTP/HTTPS."""
    invalid_schemes = [
        "file:///etc/passwd",
        "gopher://127.0.0.1:8767/",
        "ftp://example.com/movie.mp4",
        "javascript:alert(1)",
        "",
        None,
    ]
    for url in invalid_schemes:
        with pytest.raises(HTTPException) as exc_info:
            _validate_external_proxy_url(url)
        assert exc_info.value.status_code == 400, f"URL {url} harus ditolak dengan 400!"


@pytest.mark.asyncio
async def test_ssrf_validator_allows_legitimate_external_urls():
    """Memverifikasi bahwa URL publik CDN streaming diperbolehkan."""
    valid_urls = [
        "https://hls.dramahot.top/video/1080p.m3u8",
        "https://megacloud.tv/embed-2/v.mp4",
        "https://googleapis.com/v1beta/models",
        "http://example.com/subs/en.vtt",
    ]
    for url in valid_urls:
        # Tidak melempar exception
        _validate_external_proxy_url(url)


@pytest.mark.asyncio
async def test_proxy_endpoints_enforce_ssrf_rejection():
    """Memverifikasi penolakan SSRF langsung melalui endpoint /api/player/video dan /api/player/sub."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Video proxy
        r_vid = await client.get("/api/player/video", params={"url": "http://127.0.0.1:8767/api/settings"})
        assert r_vid.status_code == 403
        assert "SSRF" in r_vid.text or "dilarang" in r_vid.text

        # 2. Subtitle proxy
        r_sub = await client.get("/api/player/sub", params={"url": "http://192.168.1.1/admin.html"})
        assert r_sub.status_code == 403
        assert "SSRF" in r_sub.text or "dilarang" in r_sub.text

        # 3. Custom subtitle get proxy
        r_csub = await client.get("/api/player/sub_custom", params={"url": "http://localhost:8767/api/history"})
        assert r_csub.status_code == 403


@pytest.mark.asyncio
async def test_anilist_rate_limit_backoff_handling(monkeypatch):
    """Memverifikasi bahwa status 429 dari AniList memicu cooldown dan mencegah network hammering."""
    class Mock429Response:
        status_code = 429
        headers = {"Retry-After": "10"}
        def json(self):
            return {"errors": [{"message": "Too Many Requests"}]}

    # Reset cooldown
    al._al_rate_limit_until = 0.0
    assert al._is_rate_limited() is False

    # Simulasikan penerimaan 429
    al._record_rate_limit(Mock429Response())
    assert al._is_rate_limited() is True

    # Panggilan season_page dan anime_relations saat rate limited harus langsung mengembalikan data kosong
    res_page = al.season_page("spring", 2026)
    assert res_page.get("media") == []

    res_rel = al.anime_relations("Naruto")
    assert res_rel == []

    # Reset cooldown kembali
    al._al_rate_limit_until = 0.0
    assert al._is_rate_limited() is False


@pytest.mark.asyncio
async def test_desync_stream_socket_cleanup(monkeypatch):
    """Memverifikasi bahwa raw_sock pada tls_desync_stream selalu ditutup saat stream dihentikan (GeneratorExit)."""
    closed = False

    class FakeSocket:
        def settimeout(self, t): pass
        def sendall(self, b): pass
        def recv(self, n): return b""
        def close(self):
            nonlocal closed
            closed = True

    class FakeSSL:
        def write(self, b): pass
        def read(self, n): return b""

    class FakeBIO:
        def read(self): return b""

    def fake_connect(host, port, timeout=10.0):
        return FakeSocket(), FakeSSL(), FakeBIO(), FakeBIO()

    monkeypatch.setattr(desync, "tls_desync_connect", fake_connect)

    gen = desync.tls_desync_stream("https://example.com/video.ts")
    # Mulai generator lalu tutup secara paksa (simulasi pemutar video seek / pause)
    try:
        await gen.asend(None)
    except (StopAsyncIteration, Exception):
        pass
    finally:
        await gen.aclose()

    assert closed is True, "Socket harus ditutup secara otomatis saat generator ditutup!"
