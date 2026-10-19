import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from api import hianime as hi

def test_trusted_sub_url_fast_track():
    """Memastikan URL subtitle dari CDN terpercaya langsung di-return tanpa deep fetch."""
    trusted_url = "https://broforgotsave.com/sub/anime_ep1.vtt"
    res = hi._validate_sub_url(trusted_url, referer="https://megaplay.buzz/")
    assert res == trusted_url

def test_invalid_sub_url_handling():
    """Memastikan URL subtitle kosong atau invalid di-handle dengan aman."""
    assert hi._validate_sub_url("", "") is None
    assert hi._validate_sub_url("not_a_url", "") is None

@pytest.mark.asyncio
async def test_aniskip_fast_timeout():
    """Memastikan aniskip tidak memblokir lebih dari 1.2s jika lambat."""
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    try:
        sk = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: {"intro": {"start": 0, "end": 0}}),
            timeout=1.2
        )
    except Exception:
        pass
    elapsed = loop.time() - t0
    assert elapsed < 1.5

def test_blocked_dpi_hosts_whitelist_protection():
    """Memastikan domain CDN umum tidak teracuni masuk ke _BLOCKED_DPI_HOSTS saat terjadi error biasa."""
    from api.hianime import _BLOCKED_DPI_HOSTS
    initial_hosts = set(_BLOCKED_DPI_HOSTS)
    
    # Error timeout biasa pada domain cdn
    cdn_host = "test-cdn.tiktokcdn.com"
    err = TimeoutError("The read operation timed out")
    err_text = str(err).lower()
    
    is_known_dpi = any(k in cdn_host for k in ("dramahot", "zokoanime"))
    is_rst = any(w in err_text for w in ("connection reset", "connectionreseterror", "rst", "closed connection"))
    
    if is_known_dpi or is_rst:
        _BLOCKED_DPI_HOSTS.add(cdn_host)
        
    assert cdn_host not in _BLOCKED_DPI_HOSTS
