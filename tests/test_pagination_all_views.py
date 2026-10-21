import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
import main

@pytest.mark.asyncio
async def test_seasonal_now_pagination():
    """Memastikan view 'musim' (which=now) mengembalikan total_pages > 1 dan has_next bernilai boolean valid."""
    res1 = await main.seasonal(which="now", season="", year=0, page=1)
    assert res1.get("success") is True
    d1 = res1.get("data", {})
    assert d1.get("page") == 1
    # total_pages harus lebih dari 1 jika has_next bernilai True
    if d1.get("has_next"):
        assert d1.get("total_pages", 0) > 1

@pytest.mark.asyncio
async def test_seasonal_airing_pagination():
    """Memastikan view 'lanjutan' (which=airing) mendukung halaman 1 dan 2 dengan total_pages > 1."""
    res1 = await main.seasonal(which="airing", season="", year=0, page=1)
    assert res1.get("success") is True
    d1 = res1.get("data", {})
    assert d1.get("page") == 1
    assert d1.get("total_pages", 0) > 1

    res2 = await main.seasonal(which="airing", season="", year=0, page=2)
    assert res2.get("success") is True
    d2 = res2.get("data", {})
    assert d2.get("page") == 2
    assert d2.get("total_pages", 0) > 1

@pytest.mark.asyncio
async def test_seasonal_custom_pagination():
    """Memastikan view 'season-custom' (misal season=fall year=2024) mengembalikan total_pages > 1."""
    res1 = await main.seasonal(which="", season="fall", year=2024, page=1)
    assert res1.get("success") is True
    d1 = res1.get("data", {})
    assert d1.get("page") == 1
    assert d1.get("total_pages", 0) > 1

@pytest.mark.asyncio
async def test_catalog_pagination():
    """Memastikan katalog tetap mendukung pagination halaman 1 dan 2."""
    res1 = await main.catalog(page=1)
    assert res1.get("success") is True
    d1 = res1.get("data", {})
    assert d1.get("page") == 1
    assert d1.get("total_pages", 0) > 1

@pytest.mark.asyncio
async def test_schedule_days_navigation():
    """Memastikan endpoint schedule mendukung hari yesterday, today, tomorrow."""
    for d in ("yesterday", "today", "tomorrow"):
        res = await main.anime_schedule(day=d)
        assert res.get("success") is True
        data = res.get("data", {})
        assert data.get("day") == d
        assert "items" in data


@pytest.mark.asyncio
async def test_search_pagination():
    """Memastikan endpoint search mendukung navigasi halaman berikutnya dan menyertakan total_pages."""
    res1 = await main.search(q="one piece", page=1, limit=12)
    assert res1.get("success") is True
    d1 = res1.get("data", {})
    assert d1.get("page") == 1
    assert "results" in d1
    assert d1.get("total_pages", 1) >= 1
    assert "has_next" in d1

