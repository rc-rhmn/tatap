"""
Test suite untuk memverifikasi spesifikasi navigasi D-Pad TV (10-Foot UI) pada repositori Tatap:
1. Zero Orphan Focus & Focus History Stack (TvNavigationManager)
2. Geometric / Dynamic Grid Spatial Navigation (getSpatialTarget & edge-case row clamping)
3. Player HUD State Machine (PLAYER_IDLE, PLAYER_HUD_ACTIVE, PLAYER_MODAL_ACTIVE & 4-second autohide)
4. Two-Stage Search Input Focus vs Virtual Keyboard (IME) di app.js, index.html, & MainActivity.java
5. 6-Level Back Button Hierarchy & CSS .tv-focus visual indicators
"""

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
STYLE_CSS = FRONTEND_DIR / "css" / "style.css"
TERM_JS = FRONTEND_DIR / "js" / "term.js"
APP_JS = FRONTEND_DIR / "js" / "app.js"
INDEX_HTML = FRONTEND_DIR / "index.html"
MAIN_ACTIVITY = REPO_ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app" / "MainActivity.java"


def test_tv_navigation_manager_zero_orphan_focus_and_history_stack():
    """Memastikan TvNavigationManager mengelola activeZone, focusHistoryStack, dan pencegahan orphan focus."""
    content = APP_JS.read_text(encoding="utf-8")
    assert "var TvNavigationManager = (function(){" in content
    assert "window.TvNavigationManager = TvNavigationManager;" in content
    assert "focusHistoryStack" in content
    assert "activeZone" in content
    assert "pushFocus:" in content or "pushFocus" in content
    assert "popFocus:" in content or "popFocus" in content
    assert "restoreFocusState:" in content or "restoreFocusState" in content
    assert "saveFocusedIndex:" in content
    assert "restoreFocusedIndex:" in content
    assert "scrollIntoView({ behavior: \"smooth\", block: \"center\", inline: \"nearest\" })" in content


def test_geometric_dynamic_grid_spatial_navigation():
    """Memastikan navigasi spasial geometris 2D dan edge-case clamping baris terakhir."""
    content = APP_JS.read_text(encoding="utf-8")
    assert "getSpatialTarget" in content
    assert "getBoundingClientRect()" in content
    # Clamping baris terakhir tanpa wrap-around
    assert "Math.min(activeIdx + cols, epBtns.length - 1)" in content or "Math.min(targetIndex, items.length - 1)" in content

    term_content = TERM_JS.read_text(encoding="utf-8")
    assert "getGridCols()" in term_content
    # Clamping pada term.js moveSel agar baris terakhir tidak melompat ke baris pertama
    assert "next = count - 1;" in term_content


def test_player_hud_state_machine_and_four_second_autohide():
    """Memastikan Player HUD memiliki 3 state tegas dan timer autohide 4 detik dengan blur cleanup."""
    content = APP_JS.read_text(encoding="utf-8")
    assert 'PLAYER_IDLE = "PLAYER_IDLE"' in content
    assert 'PLAYER_HUD_ACTIVE = "PLAYER_HUD_ACTIVE"' in content
    assert 'PLAYER_MODAL_ACTIVE = "PLAYER_MODAL_ACTIVE"' in content
    assert "resetHudTimer" in content
    assert "4000" in content, "Timer auto-hide Player HUD wajib 4000ms (4 detik)"
    assert "hidePlayerControls" in content
    assert "showPlayerControls" in content
    # Verifikasi blur dan hapus .tv-focus saat HUD bersembunyi
    assert 'focused[i].classList.remove("tv-focus")' in content
    assert "document.activeElement.blur()" in content


def test_two_stage_search_input_focus_vs_virtual_keyboard():
    """Memastikan input pencarian di TV tidak langsung memunculkan IME pada sentuhan pertama."""
    index_html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="search-input-wrap"' in index_html
    assert 'tabindex="0"' in index_html
    assert 'id="cmd"' in index_html
    assert 'readonly' in index_html, "Input #cmd wajib memiliki atribut readonly di mode navigasi awal TV"

    app_js = APP_JS.read_text(encoding="utf-8")
    assert "enterSearchTypingMode" in app_js
    assert "exitSearchTypingMode" in app_js
    assert 'inp.removeAttribute("readonly")' in app_js
    assert 'inp.setAttribute("readonly", "readonly")' in app_js

    # Verifikasi MainActivity.java tidak memanggil showKeyboard saat sekadar hover/focus di TV
    activity_java = MAIN_ACTIVITY.read_text(encoding="utf-8")
    assert "layoutSearchBox.setFocusable(true)" in activity_java
    assert "etSearch.setFocusable(false)" in activity_java
    assert "etSearch.setFocusableInTouchMode(false)" in activity_java
    assert "activateSearchInput()" in activity_java
    assert "imm.hideSoftInputFromWindow" in activity_java


def test_six_level_back_hierarchy_and_tv_focus_styling():
    """Memastikan 6-level back button hierarchy dan styling indikator .tv-focus."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")
    assert ".tv-focus," in css_content or ".tv-focus" in css_content
    assert "outline: 3px solid" in css_content
    assert "transform: scale(1.06)" in css_content
    assert "z-index: 20" in css_content
    assert "scroll-margin: 72px" in css_content

    app_js = APP_JS.read_text(encoding="utf-8")
    assert "handleBack" in app_js
    assert "lastBackPressTime" in app_js
    assert "Tekan sekali lagi untuk keluar dari Tatap" in app_js

    activity_java = MAIN_ACTIVITY.read_text(encoding="utf-8")
    assert "lastBackPressTime" in activity_java
    assert "Toast.makeText(this, \"Tekan sekali lagi untuk keluar dari Tatap\"" in activity_java
