import os
import sys
import xml.etree.ElementTree as ET
import pytest
from fastapi.responses import JSONResponse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))
import main  # noqa: E402

@pytest.mark.asyncio
async def test_browse_cross_filter_params():
    # Test browse with sort, year, month, type
    res = await main.browse_ep(sort="score", year="2024", month="10", type="tv", page=1)
    assert isinstance(res, dict)
    assert res.get("success") is True
    data = res.get("data", {})
    assert "items" in data
    assert "page" in data
    assert data["page"] == 1
    # params dictionary harus menangkap resolusi sy/ey dan sm/em
    params = data.get("params", {})
    assert params.get("sort") == "score"
    assert params.get("sy") == "2024"
    assert params.get("ey") == "2024"
    assert params.get("sm") == "10"
    assert params.get("em") == "10"
    assert params.get("type") == "tv"

@pytest.mark.asyncio
async def test_browse_season_filter_params():
    """Memastikan parameter season (fall, spring, summer, winter) ditangkap oleh browse endpoint."""
    for s in ["fall", "spring", "summer", "winter"]:
        res = await main.browse_ep(season=s, year="2024", page=1)
        assert isinstance(res, dict)
        assert res.get("success") is True
        data = res.get("data", {})
        assert "items" in data
        params = data.get("params", {})
        assert params.get("season") == s
        assert params.get("sy") == "2024"
        assert params.get("ey") == "2024"

@pytest.mark.asyncio
async def test_browse_year_range_parsing():
    # Test range year (2015-2019)
    res = await main.browse_ep(year="2015-2019", page=1)
    assert isinstance(res, dict)
    assert res.get("success") is True
    params = res["data"].get("params", {})
    assert params.get("sy") == "2015"
    assert params.get("ey") == "2019"

    # Test classic year (<2000)
    res_classic = await main.browse_ep(year="<2000", page=1)
    assert isinstance(res_classic, dict)
    assert res_classic.get("success") is True
    params_c = res_classic["data"].get("params", {})
    assert params_c.get("ey") == "1999"

@pytest.mark.asyncio
async def test_browse_hentai_genre_blacklist():
    res = await main.browse_ep(genre="hentai", page=1)
    assert isinstance(res, dict)
    assert res.get("success") is True
    assert res["data"]["items"] == []

def test_catalog_filter_season_android_layout_and_java():
    """Memverifikasi penambahan Seksi Musim (Season) pada dialog_catalog_filter.xml dan MainActivity.java."""
    dialog_layout_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "layout", "dialog_catalog_filter.xml")
    main_java_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "MainActivity.java")

    # 1. XML check
    assert os.path.exists(dialog_layout_path)
    with open(dialog_layout_path, "r", encoding="utf-8") as f:
        xml_content = f.read()

    assert "MUSIM PENAYANGAN (SEASON)" in xml_content
    assert "group_filter_season" in xml_content
    assert "chip_season_all" in xml_content
    assert "chip_season_spring" in xml_content
    assert "chip_season_summer" in xml_content
    assert "chip_season_fall" in xml_content
    assert "chip_season_winter" in xml_content

    # 2. Java check
    assert os.path.exists(main_java_path)
    with open(main_java_path, "r", encoding="utf-8") as f:
        java_content = f.read()

    assert "private String filterCatalogSeason = \"\";" in java_content
    assert "!filterCatalogSeason.isEmpty()" in java_content
    assert "R.id.chip_season_all" in java_content
    assert "R.id.chip_season_spring" in java_content
    assert "R.id.chip_season_summer" in java_content
    assert "R.id.chip_season_fall" in java_content
    assert "R.id.chip_season_winter" in java_content
    assert "filterCatalogSeason = tempSeason[0];" in java_content
    assert "ep.append(\"&season=\")" in java_content

def test_catalog_filter_season_web_frontend():
    """Memverifikasi penambahan grup chip season pada frontend HTML dan term.js."""
    index_html_path = os.path.join(ROOT_DIR, "frontend", "index.html")
    term_js_path = os.path.join(ROOT_DIR, "frontend", "js", "term.js")

    with open(index_html_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "cf-chips-season" in html
    assert 'data-val="spring"' in html
    assert 'data-val="summer"' in html
    assert 'data-val="fall"' in html
    assert 'data-val="winter"' in html

    with open(term_js_path, "r", encoding="utf-8") as f:
        js = f.read()
    assert 'cf-chips-season' in js
    assert 'f.season' in js
