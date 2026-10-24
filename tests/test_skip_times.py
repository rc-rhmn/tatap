"""Test suite untuk verifikasi fitur skip opening dan ending anime."""
import pytest
import os
import sys
import tempfile
import asyncio
from unittest.mock import patch, MagicMock
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api import aniskip
from backend.api import hianime as hi
from backend.database import init_db, get_episode_cache, set_episode_cache


def test_is_valid_interval():
    """Validasi interval waktu OP/ED: end > start, end > 0, dan durasi >= 5 detik."""
    assert aniskip.is_valid_interval(10.0, 100.0) is True
    assert aniskip.is_valid_interval(0.5, 90.5) is True
    assert aniskip.is_valid_interval(10.0, 15.0) is True

    # Tidak valid: durasi < 5.0 detik
    assert aniskip.is_valid_interval(10.0, 14.9) is False
    # Tidak valid: end <= start
    assert aniskip.is_valid_interval(100.0, 10.0) is False
    assert aniskip.is_valid_interval(50.0, 50.0) is False
    # Tidak valid: start/end 0 atau negatif
    assert aniskip.is_valid_interval(0, 0) is False
    assert aniskip.is_valid_interval(-10, 0) is False
    # Tidak valid: bukan angka
    assert aniskip.is_valid_interval("invalid", 100) is False
    assert aniskip.is_valid_interval(None, None) is False


def test_aniskip_empty_or_invalid():
    """AniSkip harus mengembalikan {start: 0, end: 0} jika parameter tidak valid."""
    res1 = aniskip.get_skip_times(None, 1)
    assert res1["intro"] == {"start": 0, "end": 0}
    assert res1["outro"] == {"start": 0, "end": 0}

    res2 = aniskip.get_skip_times("abc", 0)
    assert res2["intro"] == {"start": 0, "end": 0}
    assert res2["outro"] == {"start": 0, "end": 0}


def test_aniskip_query_without_hardcoded_episode_length():
    """URL query AniSkip tidak boleh menyertakan episodeLength jika nilainya 0, dan hanya menyertakan jika > 0."""
    captured_urls = []

    def mock_get(url, **kwargs):
        captured_urls.append(url)
        resp = MagicMock()
        resp.status_code = 404
        return resp

    aniskip._CACHE.clear()
    with patch("httpx.Client.get", side_effect=mock_get):
        aniskip.get_skip_times(11111, 1, episode_length=0)
        assert len(captured_urls) == 1
        assert "episodeLength" not in captured_urls[0]

        aniskip.get_skip_times(22222, 2, episode_length=1420.5)
        assert len(captured_urls) == 2
        assert "episodeLength=1420.5" in captured_urls[1]


def test_aniskip_caching_error_no_cache():
    """Error jaringan (timeout/exception) atau HTTP >= 500 / 429 tidak boleh disimpan ke cache."""
    aniskip._CACHE.clear()

    # Skenario 1: TimeoutException
    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Timeout connecting to aniskip")):
        res = aniskip.get_skip_times(33333, 1)
        assert res["intro"] == {"start": 0, "end": 0}
        assert (33333, 1) not in aniskip._CACHE
        assert ("mal", 33333, 1) not in aniskip._CACHE

    # Skenario 2: HTTP 500 Server Error
    mock_500 = MagicMock()
    mock_500.status_code = 500
    with patch("httpx.Client.get", return_value=mock_500):
        res = aniskip.get_skip_times(44444, 1)
        assert res["intro"] == {"start": 0, "end": 0}
        assert (44444, 1) not in aniskip._CACHE
        assert ("mal", 44444, 1) not in aniskip._CACHE


def test_aniskip_negative_cache_on_404():
    """HTTP 404 harus disimpan ke cache dengan TTL 900 detik (15 menit)."""
    aniskip._CACHE.clear()
    mock_404 = MagicMock()
    mock_404.status_code = 404

    with patch("httpx.Client.get", return_value=mock_404):
        res = aniskip.get_skip_times(55555, 1)
        assert res["intro"] == {"start": 0, "end": 0}
        assert ("mal", 55555, 1) in aniskip._CACHE
        entry, ts, ttl = aniskip._CACHE[("mal", 55555, 1)]
        assert ttl == 900


def test_cross_provider_skip_cache():
    """Timestamp OP/ED dari HiAnime/AniSkip dapat dibaca oleh Otakudesu via title/mal_id."""
    aniskip._CACHE.clear()
    mal_id = 52991
    title = "Sousou no Frieren"
    ep = 5
    intro = {"start": 85.0, "end": 175.0}
    outro = {"start": 1250.0, "end": 1340.0}

    # Simpan dari provider pertama (misal HiAnime)
    aniskip.store_skip_times(mal_id=mal_id, title=title, ep=ep, intro=intro, outro=outro)

    # Ambil via variasi slug Otakudesu
    cached_by_otaku_slug = aniskip.get_cached_skip_times(title="otakudesu:sousou-no-frieren-sub-indo", ep=ep)
    assert cached_by_otaku_slug is not None
    assert cached_by_otaku_slug["intro"] == {"start": 85.0, "end": 175.0}
    assert cached_by_otaku_slug["outro"] == {"start": 1250.0, "end": 1340.0}

    # Ambil via mal_id
    cached_by_mal = aniskip.get_cached_skip_times(mal_id=mal_id, ep=ep)
    assert cached_by_mal is not None
    assert cached_by_mal["intro"] == {"start": 85.0, "end": 175.0}


def test_aniskip_parsing_success():
    """AniSkip harus berhasil mem-parsing response yang berisi OP dan ED."""
    aniskip._CACHE.clear()
    mock_payload = {
        "found": True,
        "results": [
            {
                "skipType": "op",
                "interval": {"startTime": 12.5, "endTime": 102.5}
            },
            {
                "skipType": "ed",
                "interval": {"startTime": 1300.0, "endTime": 1390.0}
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch("httpx.Client.get", return_value=mock_resp):
        res = aniskip.get_skip_times(99999, 1)
        assert res["intro"] == {"start": 12.5, "end": 102.5}
        assert res["outro"] == {"start": 1300.0, "end": 1390.0}
        # Verifikasi TTL 86400 (24 jam)
        assert ("mal", 99999, 1) in aniskip._CACHE
        entry, ts, ttl = aniskip._CACHE[("mal", 99999, 1)]
        assert ttl == 86400


@pytest.mark.asyncio
async def test_database_episode_cache_intro_outro():
    """Database episode_cache harus menyimpan dan memulihkan intro & outro secara utuh."""
    await init_db()
    slug = "test-skip-anime-cache"
    ep = 1
    mode = "sub"
    master = "https://example.com/master.m3u8"
    variants = [{"q": "1080p", "url": "https://example.com/1080.m3u8"}]
    intro = {"start": 85.0, "end": 175.0}
    outro = {"start": 1250.0, "end": 1340.0}

    await set_episode_cache(slug, ep, mode, master, variants,
                            "https://example.com/sub.vtt", "Indonesian",
                            "https://example.com/", "HD-1",
                            subtitles=[{"label": "Indonesian", "url": "https://example.com/sub.vtt", "default": True}],
                            intro=intro, outro=outro)

    cached = await get_episode_cache(slug, ep, mode)
    assert cached is not None
    assert cached["intro"] == {"start": 85.0, "end": 175.0}
    assert cached["outro"] == {"start": 1250.0, "end": 1340.0}
