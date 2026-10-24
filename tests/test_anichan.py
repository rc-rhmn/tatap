import pytest
import asyncio
import os
import sys
import base64
import json
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from api import anichan
from api import hianime as hi
from api import otakudesu as otaku
from database import init_db, get_setting
import main


def test_clean_title_for_search():
    assert anichan.clean_title_for_search("eyeshield-21-7505") == "eyeshield 21"
    assert anichan.clean_title_for_search("one-piece-100") == "one piece"
    assert anichan.clean_title_for_search("attack-on-titan-112") == "attack on titan"
    assert anichan.clean_title_for_search("dandadan-171018-sub-indo") == "dandadan"


def test_hentai_blacklist_rejection():
    with pytest.raises(RuntimeError, match="Konten genre Hentai diblokir"):
        anichan.resolve_anilist_id("overflow-hentai-series")

    with pytest.raises(RuntimeError, match="Konten genre Hentai diblokir"):
        anichan.resolve_stream("overflow-hentai-123", 1)


def test_anichan_decrypt_payload():
    # Buat dummy payload AES-GCM dengan token n dummy
    token_n = "test_session_token_12345"
    raw_O = base64.b64decode(anichan.STATIC_O)
    raw_b = base64.b64decode(anichan.STATIC_B)
    hmac_key = bytes([x ^ y for x, y in zip(raw_O, raw_b)])
    aes_key = hmac.new(hmac_key, token_n.encode("utf-8"), hashlib.sha256).digest()

    sample_data = {
        "servers": [
            {
                "name": "anikoto",
                "type": "hls",
                "stream": "https://c.toroplay.cymru/api/watch/m3u8?url=https%3A%2F%2Fcdn.example.com%2Fmaster.m3u8&ref=https%3A%2F%2Fmegaplay.buzz%2F",
                "subtitles": [{"lang": "English", "url": "/subs/en.vtt", "default": True}],
                "intro": {"start": 10, "end": 90},
                "outro": {"start": 1200, "end": 1280},
            },
            {
                "name": "vidhawk",
                "type": "embed",
                "embed": "https://vidhawk.buzz/embed/ani/15/1/sub",
            },
        ]
    }
    plaintext = json.dumps(sample_data).encode("utf-8")
    iv = os.urandom(12)
    aesgcm = AESGCM(aes_key)
    ciphertext = aesgcm.encrypt(iv, plaintext, None)

    encrypted_payload = {
        "v": 1,
        "i": base64.b64encode(iv).decode("utf-8"),
        "d": base64.b64encode(ciphertext).decode("utf-8"),
    }

    decrypted = anichan._decrypt_payload(encrypted_payload, token_n)
    assert "servers" in decrypted
    assert len(decrypted["servers"]) == 2
    assert decrypted["servers"][0]["name"] == "anikoto"
    assert decrypted["servers"][0]["type"] == "hls"


def test_direct_hls_m3u8_unwrapping():
    wrapped_url = "https://c.toroplay.cymru/api/watch/m3u8?url=https%3A%2F%2Ffetch.nexabloom.top%2Fanime%2Ftest%2Fmaster.m3u8%3Ftoken%3D123&ref=https%3A%2F%2Fmegaplay.buzz%2F&s=abc"
    direct_url, ref = anichan._unwrap_direct_m3u8(wrapped_url)
    assert direct_url == "https://fetch.nexabloom.top/anime/test/master.m3u8?token=123"
    assert ref == "https://megaplay.buzz/"

    raw_m3u8 = "https://example.com/stream/master.m3u8"
    direct_url2, ref2 = anichan._unwrap_direct_m3u8(raw_m3u8)
    assert direct_url2 == raw_m3u8
    assert ref2 == "https://anichan.to/"


def test_parse_m3u8_variants():
    sample_master = """#EXTM3U
#EXT-X-VERSION:4
#EXT-X-STREAM-INF:BANDWIDTH=5300000,RESOLUTION=1920x1080
1080/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720
720/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=900000,RESOLUTION=640x360
360/index.m3u8
"""
    variants = anichan._parse_m3u8_variants("https://cdn.example.com/master.m3u8", sample_master)
    assert len(variants) == 3
    assert variants[0]["q"] == "1080p"
    assert variants[0]["url"] == "https://cdn.example.com/1080/index.m3u8"
    assert variants[1]["q"] == "720p"
    assert variants[2]["q"] == "360p"


@pytest.mark.asyncio
async def test_per_title_failover_cascade(monkeypatch):
    """Memverifikasi bahwa ketika HiAnime dan Otakudesu gagal karena CDN mati/404,
    failover otomatis terjadi ke AniChan HLS M3U8, flag is_failover aktif,
    dan preferensi global pengguna TIDAK diubah.
    """
    await init_db()
    slug = "eyeshield-21-7505"
    ep = 1

    # Bersihkan failover cache untuk test ini
    main._ANIME_FAILOVER_CACHE.pop(slug, None)

    # Mock HiAnime agar gagal (simulasi CDN mati / 404)
    def fake_hianime_episodes(s):
        return [{"ep": 1, "ep_id": "105993"}]

    def fake_hianime_m3u8(maps, ep_no, m, s):
        raise RuntimeError("HiAnime CDN 404: server Zoko / Megaplay master dead")

    monkeypatch.setattr(hi, "hianime_episodes", fake_hianime_episodes)
    monkeypatch.setattr(hi, "hianime_m3u8", fake_hianime_m3u8)

    # Mock Otakudesu agar juga gagal
    def fake_otaku_resolve(s, e):
        raise RuntimeError("Otakudesu episode not found")

    monkeypatch.setattr(otaku, "resolve_stream", fake_otaku_resolve)

    # Mock AniChan agar berhasil mengembalikan direct HLS M3U8
    def fake_anichan_resolve(s, e, mode="sub", q="best"):
        return {
            "master": "https://fetch.nexabloom.top/anime/eyeshield21/master.m3u8",
            "variants": [{"q": "480p", "url": "https://fetch.nexabloom.top/anime/eyeshield21/480.m3u8"}],
            "sub": "https://c.toroplay.cymru/sub/en.vtt",
            "sub_lang": "English",
            "subtitles": [{"label": "English", "lang": "en", "url": "https://c.toroplay.cymru/sub/en.vtt", "default": True}],
            "referer": "https://megaplay.buzz/",
            "server": "anichan:anikoto",
            "mode": mode,
            "intro": {"start": 132, "end": 213},
            "outro": {"start": 1221, "end": 1295},
            "source": "anichan",
            "is_failover": True,
            "cached": False,
        }

    monkeypatch.setattr(anichan, "resolve_stream", fake_anichan_resolve)

    # Panggil endpoint resolve
    res = await main.resolve(slug=slug, ep=ep, mode="sub", q="best", source="", force=True)

    assert res["success"] is True
    data = res["data"]
    assert data["source"] == "anichan"
    assert data["server"] == "anichan:anikoto"
    assert data.get("is_failover") is True
    assert data.get("failover_from") == "hianime"
    assert data["master"] == "https://fetch.nexabloom.top/anime/eyeshield21/master.m3u8"
    assert data["intro"]["start"] == 132

    # Verifikasi failover tercatat di cache memori per-judul
    assert main._ANIME_FAILOVER_CACHE.get(slug) == "anichan"

    # Verifikasi pengaturan global TIDAK terpolusi/tidak berubah
    global_pref = await get_setting("preferred_source", "hianime")
    assert global_pref.lower() == "hianime"

    # Panggilan episode berikutnya (ep 2) otomatis memakai failover anichan tanpa timeout
    res_ep2 = await main.resolve(slug=slug, ep=2, mode="sub", q="best", source="", force=True)
    assert res_ep2["success"] is True
    assert res_ep2["data"]["source"] == "anichan"
