"""Test suite untuk verifikasi fitur skip opening dan ending anime."""
import pytest
import os
import sys
import tempfile
import asyncio
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api import aniskip
from backend.api import hianime as hi
from backend.database import init_db, get_episode_cache, set_episode_cache


def test_aniskip_empty_or_invalid():
    """AniSkip harus mengembalikan {start: 0, end: 0} jika parameter tidak valid."""
    res1 = aniskip.get_skip_times(None, 1)
    assert res1["intro"] == {"start": 0, "end": 0}
    assert res1["outro"] == {"start": 0, "end": 0}

    res2 = aniskip.get_skip_times("abc", 0)
    assert res2["intro"] == {"start": 0, "end": 0}
    assert res2["outro"] == {"start": 0, "end": 0}


def test_aniskip_parsing_success():
    """AniSkip harus berhasil mem-parsing response yang berisi OP dan ED."""
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
