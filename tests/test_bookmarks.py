import os
import sys
import pytest
import asyncio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import (
    init_db,
    add_bookmark,
    remove_bookmark,
    get_bookmarks,
    is_bookmarked,
    clear_bookmarks
)

@pytest.mark.asyncio
async def test_bookmark_lifecycle():
    await init_db()
    # Bersihkan dulu data uji
    await remove_bookmark("test-frieren-slug")
    assert await is_bookmarked("test-frieren-slug") is False

    # 1. Tambah bookmark
    await add_bookmark(
        slug="test-frieren-slug",
        title="Sousou no Frieren",
        poster="https://example.com/frieren.jpg",
        type="TV",
        sub="28",
        eps="28",
        score=9.35
    )

    # 2. Cek status
    assert await is_bookmarked("test-frieren-slug") is True
    assert await is_bookmarked("non-existent-slug") is False

    # 3. Ambil daftar dan verifikasi kompatibilitas id = slug
    bookmarks = await get_bookmarks(limit=10)
    found = [b for b in bookmarks if b.get("slug") == "test-frieren-slug"]
    assert len(found) == 1
    item = found[0]
    assert item["id"] == "test-frieren-slug"
    assert item["title"] == "Sousou no Frieren"
    assert item["score"] == 9.35

    # 4. Hapus bookmark spesifik
    await remove_bookmark("test-frieren-slug")
    assert await is_bookmarked("test-frieren-slug") is False
    bookmarks_after = await get_bookmarks(limit=10)
    assert not any(b.get("slug") == "test-frieren-slug" for b in bookmarks_after)
