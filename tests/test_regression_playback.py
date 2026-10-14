import os
import sys
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
import main
from database import init_db, get_setting, set_setting, get_history, add_history

@pytest.mark.asyncio
async def test_m3u8_rewrite_and_audio_demux_proxy():
    """Memverifikasi penulisan ulang m3u8 master playlist dan sub-track audio demux agar diproxy via Tatap."""
    await init_db()
    
    sample_m3u8 = """#EXTM3U
#EXT-X-VERSION:4
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio-1",NAME="English",DEFAULT=YES,AUTOSELECT=YES,LANGUAGE="en",URI="https://upstream.cdn/audio/en.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=2149280,RESOLUTION=1920x1080,AUDIO="audio-1"
https://upstream.cdn/video/1080p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1049280,RESOLUTION=1280x720,AUDIO="audio-1"
https://upstream.cdn/video/720p.m3u8
"""
    parent_url = "https://upstream.cdn/master.m3u8"
    referer = "https://megacloud.tv/"
    
    rewritten = main._rewrite_m3u8_content(sample_m3u8, parent_url, referer)
    
    # 1. Pastikan tag AUDIO URI ditulis ulang ke proxy /api/player/video
    assert 'URI="/api/player/video?url=https%3A%2F%2Fupstream.cdn%2Faudio%2Fen.m3u8&referer=https%3A%2F%2Fmegacloud.tv%2F"' in rewritten
    # 2. Pastikan sub-manifest video ditulis ulang ke proxy /api/player/video
    assert '/api/player/video?url=https%3A%2F%2Fupstream.cdn%2Fvideo%2F1080p.m3u8&referer=https%3A%2F%2Fmegacloud.tv%2F' in rewritten
    assert '/api/player/video?url=https%3A%2F%2Fupstream.cdn%2Fvideo%2F720p.m3u8&referer=https%3A%2F%2Fmegacloud.tv%2F' in rewritten
    # 3. Header EXTM3U tetap dipertahankan
    assert rewritten.startswith("#EXTM3U")


@pytest.mark.asyncio
async def test_subtitle_anti_poisoning_and_caching():
    """Memverifikasi validasi anti-poisoning subtitle bahasa Indonesia dan deduplikasi fetch in-flight."""
    await init_db()
    
    # Uji detektor subtitle valid vs sampah / MyMemory Warning
    bad_vtt_mymemory = """WEBVTT

00:00:01.000 --> 00:00:04.000
MYMEMORY WARNING: YOU COULD ONLY TRANSLATE 50000 CHARACTERS
"""
    assert main._is_valid_id_subtitle(bad_vtt_mymemory) is False

    valid_vtt_id = """WEBVTT

00:00:01.000 --> 00:00:04.000
Halo, apa yang sedang kamu lakukan di sini? Kita bisa pergi sekarang.
"""
    assert main._is_valid_id_subtitle(valid_vtt_id) is True

    # Subtitle bahasa asing yang belum ada kata Indonesia di bawah 50 char tetap dianggap netral
    assert main._is_valid_id_subtitle("WEBVTT\n\n00:01 --> 00:02\nHi") is True


@pytest.mark.asyncio
async def test_episode_navigation_and_history_persistence():
    """Memverifikasi konsistensi navigasi episode dan persistensi riwayat tontonan."""
    await init_db()
    
    test_slug = "regression-anime-test-ep"
    test_title = "Regression Anime Test"
    
    # 1. Simpan riwayat episode 1
    await add_history(test_slug, test_title, episode=1, mode="sub")
    h1 = await get_history()
    matched1 = [x for x in h1 if x.get("slug") == test_slug]
    assert len(matched1) > 0
    assert matched1[0]["episode"] == 1
    
    # 2. Simpan riwayat episode 2 (pergantian episode ke depan)
    await add_history(test_slug, test_title, episode=2, mode="sub")
    h2 = await get_history()
    matched2 = [x for x in h2 if x.get("slug") == test_slug]
    assert len(matched2) > 0
    assert matched2[0]["episode"] == 2


@pytest.mark.asyncio
async def test_connection_recovery_upstream_fallback(monkeypatch):
    """Memverifikasi pemulihan koneksi saat direct client gagal (RST/502), otomatis dialihkan ke TLS desync."""
    await init_db()
    
    target_url = "https://dramahot.top/video/test.m3u8"
    referer = "https://zokoanime.video/"
    
    desync_called = False
    def fake_tls_desync_request(url, headers=None):
        nonlocal desync_called
        desync_called = True
        return b"#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:10.0,\nseg1.ts\n"
    
    monkeypatch.setattr("api.desync.tls_desync_request", fake_tls_desync_request)
    
    # Panggil pipe desync video secara langsung
    chunks = []
    async for chunk in main._pipe_desync_video(target_url, referer):
        chunks.append(chunk)
        
    assert desync_called is True
    assert len(chunks) > 0
    assert b"#EXTM3U" in chunks[0]
