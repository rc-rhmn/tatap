"""Tests for Video Player Shell 16:9 Optimization, Watch History View, and Typography Refinement.

Verifies:
1. Global font smoothing/antialiasing in frontend/css/style.css.
2. Single hamburger menu button in header (#btn-drawer-head) and elimination of duplicate in bottom bar.
3. Top navigation tab bar includes Riwayat (data-view="riwayat") and drawer has drawer-group-nav.
4. Responsive hiding of duplicate navigation in drawer for desktop screens.
5. Video player shell utilizes dynamic aspect-ratio 16:9 and removes rigid 640px height limit.
6. Frontend term.js supports view "riwayat", commands :riwayat / :riwayat hapus, and dynamic aspect-ratio in app.js.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).parent.parent
INDEX_HTML = REPO_ROOT / "frontend" / "index.html"
STYLE_CSS = REPO_ROOT / "frontend" / "css" / "style.css"
APP_JS = REPO_ROOT / "frontend" / "js" / "app.js"
TERM_JS = REPO_ROOT / "frontend" / "js" / "term.js"


def test_typography_font_smoothing():
    """Verify font antialiasing and text rendering optimization are applied to body."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")
    assert "-webkit-font-smoothing:antialiased" in css_content or "-webkit-font-smoothing: antialiased" in css_content
    assert "-moz-osx-font-smoothing:grayscale" in css_content or "-moz-osx-font-smoothing: grayscale" in css_content
    assert "text-rendering:optimizeLegibility" in css_content or "text-rendering: optimizeLegibility" in css_content


def test_single_burger_menu_button():
    """Verify single hamburger button in header and no duplicate #btn-drawer in bottom bar."""
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="btn-drawer-head"' in html_content
    assert 'id="btn-drawer"' not in html_content


def test_riwayat_watch_history_ui_elements():
    """Verify Riwayat tab in header nav-tabs-bar and drawer menu item."""
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="tab-nav-riwayat"' in html_content
    assert 'data-view="riwayat"' in html_content
    assert "drawer-group-nav" in html_content


def test_responsive_drawer_nav_deduplication():
    """Verify duplicate navigation items in drawer are hidden on desktop screens."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")
    assert ".drawer-group-nav{display:none}" in css_content or ".drawer-group-nav { display: none; }" in css_content or ".drawer-group-nav {display:none}" in css_content


def test_videoplayer_shell_aspect_ratio_and_stage():
    """Verify player shell maximizes available space with 16:9 aspect ratio and no 640px hard cap."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")
    app_js = APP_JS.read_text(encoding="utf-8")

    # Player shell width calculation based on 16/9
    assert "16 / 9" in css_content or "16/9" in css_content
    assert "calc((94vh - 100px) * (16 / 9))" in css_content or "16 / 9" in css_content
    # No 640px limit in ambient-stage video
    assert "max-height:clamp(240px,66vh,640px)" not in css_content
    # Dynamic video aspect ratio override on loadedmetadata
    assert "aspectRatio" in app_js


def test_riwayat_view_and_command_in_term_js():
    """Verify term.js handles 'riwayat' view, pagination, and :riwayat command."""
    term_js = TERM_JS.read_text(encoding="utf-8")

    # setView and apiCall
    assert 'case "riwayat"' in term_js
    assert "window.Tatap.history()" in term_js
    # cycleView includes riwayat
    assert '"riwayat"' in term_js
    # :riwayat command
    assert 'case "riwayat":' in term_js
    assert "DELETE" in term_js
