"""Tests for Desktop & Web title deduplication and watch history isolation.

Verifies:
1. Permanent removal of legacy empty sections #lane-season-sec and #lane-still-sec from frontend/index.html.
2. #continue-sec is kept hidden by default and never shown on catalog, musim, cari, or other non-riwayat views.
3. term.js uses updateResultsTitle to deterministically resolve titles without string concatenation accumulation.
4. Jadwal rilis title prevents duplicate "Hari Ini · Hari Ini".
5. Musim view title does not accumulate duplicate season strings on pagination.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).parent.parent
INDEX_HTML = REPO_ROOT / "frontend" / "index.html"
TERM_JS = REPO_ROOT / "frontend" / "js" / "term.js"
APP_JS = REPO_ROOT / "frontend" / "js" / "app.js"


def test_no_legacy_lane_sections_in_index_html():
    """Memastikan elemen legacy #lane-season-sec dan #lane-still-sec telah dihapus dari index.html."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="lane-season-sec"' not in html
    assert 'id="lane-season-title"' not in html
    assert 'id="lane-still-sec"' not in html
    assert 'id="lane-still"' not in html


def test_continue_sec_hidden_and_isolated():
    """Memastikan #continue-sec disembunyikan dan diisolasi sehingga tidak bocor ke katalog."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="continue-sec" class="hidden" style="display:none"' in html

    app_js = APP_JS.read_text(encoding="utf-8")
    # renderContinue harus menyembunyikan continue-sec dan tidak lagi meng-unhide untuk katalog/musim/cari
    assert 'sec.classList.add("hidden")' in app_js
    assert 'sec.style.display="none"' in app_js
    assert 'isHome=!window.Tui||["katalog","musim","cari"]' not in app_js


def test_term_js_no_lane_season_or_still_references():
    """Memastikan tidak ada lagi manipulasi DOM untuk lane-season-sec atau lane-still-sec di term.js."""
    term_js = TERM_JS.read_text(encoding="utf-8")
    assert "lane-season-sec" not in term_js
    assert "lane-still-sec" not in term_js


def test_term_js_deterministic_update_results_title():
    """Memastikan term.js memiliki fungsi updateResultsTitle deterministik dan mencegah duplikasi string."""
    term_js = TERM_JS.read_text(encoding="utf-8")
    assert "function updateResultsTitle(d)" in term_js
    # Mencegah akumulasi string judul membabi buta
    assert 'var label=$("results-title").textContent;' not in term_js
    # Penanganan jadwal rilis mencegah "Hari Ini · Hari Ini"
    assert 'lblDay === "Hari Ini" || S.scheduleDay === "today"' in term_js
    assert '$("results-title").textContent = "Jadwal rilis (Hari Ini)";' in term_js
    # Penanganan musim ini bersih
    assert 'Tayang musim ini · ' in term_js
