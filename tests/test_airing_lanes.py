import os
import sys
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.main import _is_long_running, seasonal

def test_is_long_running_classification():
    # Long running anime
    assert _is_long_running("One Piece", None, 1999, 1180, "one-piece-100") is True
    assert _is_long_running("Case Closed", None, 1996, 1216, "case-closed-323") is True
    assert _is_long_running("Detective Conan", 0, 1996, 1200, "detective-conan") is True
    assert _is_long_running("Pokemon Horizons: The Series", None, 2023, 75, "pokemon-horizons") is True
    assert _is_long_running("Crayon Shin-chan", 0, 1992, 1100, "crayon-shin-chan") is True
    assert _is_long_running("Doraemon (2005)", None, 2005, 700, "doraemon-2005") is True
    assert _is_long_running("Boruto: Naruto Next Generations", 293, 2017, 293, "boruto") is True

    # Seasonal anime
    assert _is_long_running("Re:ZERO -Starting Life in Another World- Season 4", 19, 2026, 19, "re-zero-s4") is False
    assert _is_long_running("The Elusive Samurai Season 2", 12, 2026, 12, "elusive-samurai-s2") is False
    assert _is_long_running("BLEACH: Thousand-Year Blood War - The Calamity", 10, 2026, 10, "bleach-tybw-3") is False
    assert _is_long_running("Dan Da Dan", 12, 2024, 12, "dandadan") is False
    assert _is_long_running("Solo Leveling Season 2", 13, 2025, 13, "solo-leveling-s2") is False


@pytest.mark.asyncio
async def test_seasonal_airing_dual_lane_structure():
    res = await seasonal(which="airing", page=1)
    assert isinstance(res, dict)
    assert res.get("success") is True
    
    data = res.get("data", {})
    assert data.get("which") == "airing"
    assert "seasonal" in data
    assert "long_running" in data
    assert "items" in data

    seasonal_items = data.get("seasonal", [])
    long_running_items = data.get("long_running", [])
    items_with_headers = data.get("items", [])

    assert len(seasonal_items) > 0
    assert len(long_running_items) > 0
    assert len(items_with_headers) >= len(seasonal_items) + len(long_running_items) + 2

    # Verifikasi header ada di items
    headers = [x for x in items_with_headers if x.get("is_header")]
    assert len(headers) == 2
    assert "MUSIMAN" in headers[0].get("header_title", "").upper()
    assert "PANJANG" in headers[1].get("header_title", "").upper()

    # Verifikasi seasonal anime pertama memuat badge TAMAT (terakhir tamat di atas)
    tamat_items = [x for x in seasonal_items if x.get("badge") == "TAMAT"]
    assert len(tamat_items) > 0
    assert tamat_items[0].get("is_finished") is True

    # Verifikasi serial panjang memuat badge SERIAL PANJANG
    assert all(x.get("is_long_running") is True for x in long_running_items)


@pytest.mark.asyncio
async def test_yani_neko_classified_as_seasonal():
    # Pastikan Yani Neko tidak masuk ke long_running
    assert _is_long_running("Yani Neko", 0, 0, 12, "chainsmoker-cat-121") is False
    assert _is_long_running("Yani Neko", 170, 0, 12, "chainsmoker-cat-121") is False

    res = await seasonal(which="airing", page=1)
    data = res.get("data", {})
    seasonal_items = data.get("seasonal", [])
    long_running_items = data.get("long_running", [])

    # Jika Yani Neko ada di respons, pastikan berada di seasonal, bukan long_running
    yani_in_long = [x for x in long_running_items if "yani" in x.get("title", "").lower() or "chainsmoker" in x.get("id", "").lower()]
    assert len(yani_in_long) == 0, f"Yani Neko bocor ke long_running: {yani_in_long}"

    yani_in_seasonal = [x for x in seasonal_items if "yani" in x.get("title", "").lower() or "chainsmoker" in x.get("id", "").lower()]
    if yani_in_seasonal:
        it = yani_in_seasonal[0]
        assert it.get("lane") == "seasonal"
        assert it.get("is_long_running") is False
