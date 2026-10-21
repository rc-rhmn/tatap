"""Test suite untuk verifikasi desktop styling, default katalog anime homescreen,
serta penanganan error handshake startup backend pada desktop launcher dan web frontend.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO_ROOT / "frontend" / "index.html"
STYLE_CSS = REPO_ROOT / "frontend" / "css" / "style.css"
APP_JS = REPO_ROOT / "frontend" / "js" / "app.js"
TERM_JS = REPO_ROOT / "frontend" / "js" / "term.js"
API_JS = REPO_ROOT / "frontend" / "js" / "api.js"
APPRUN = REPO_ROOT / "linux" / "AppRun"


def test_desktop_container_and_grid_styling():
    """Memastikan main container memiliki max-width 1560px terpusat dan media query grid desktop."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    # Max-width 1560px & centering di layar >= 1024px
    assert "max-width:1560px" in css or "max-width: 1560px" in css
    assert "margin:0 auto" in css or "margin: 0 auto" in css

    # Grid desktop breakpoints
    assert "@media (min-width: 769px)" in css or "@media (min-width:769px)" in css
    assert "minmax(165px, 1fr)" in css or "minmax(165px,1fr)" in css
    assert "minmax(182px, 1fr)" in css or "minmax(182px,1fr)" in css

    # Card elevation dan typography di layar desktop
    assert "translate3d(0, -4px, 0)" in css or "translate3d(0,-4px,0)" in css
    assert "font-size: 13.5px" in css or "font-size:13.5px" in css


def test_homescreen_default_is_anime_catalog():
    """Memastikan homescreen default saat buka adalah katalog anime."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    term = TERM_JS.read_text(encoding="utf-8")

    # tab-nav-katalog memiliki class active
    assert 'class="nav-tab-btn active" data-view="katalog"' in html or 'data-view="katalog" id="tab-nav-katalog"' in html
    assert 'data-view="katalog"' in html

    # S.view di term.js berstatus "katalog"
    assert 'view:"katalog"' in term or 'view: "katalog"' in term

    # boot() memicu setView("katalog")
    assert 'setView("katalog")' in term


def test_backend_startup_error_overlay_structure():
    """Memastikan overlay backend-error-overlay ada di index.html, style.css, dan term.js."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    css = STYLE_CSS.read_text(encoding="utf-8")
    term = TERM_JS.read_text(encoding="utf-8")

    assert 'id="backend-error-overlay"' in html
    assert 'id="be-retry-btn"' in html
    assert 'id="be-copy-debug-btn"' in html
    assert 'id="icon-server-alert"' in html

    assert ".backend-error-sheet" in css
    assert ".be-alert-icon" in css

    # isModalOpen() mengenali backend-error-overlay
    assert "backend-error-overlay" in term


def test_frontend_handshake_and_ping():
    """Memastikan checkBackendStartup dan Tatap.ping terpasang di JS."""
    api = API_JS.read_text(encoding="utf-8")
    app = APP_JS.read_text(encoding="utf-8")

    assert 'ping:function(){return jget("/api/ping");}' in api or 'ping:' in api
    assert "checkBackendStartup" in app
    assert "startAutoReconnect" in app
    assert "manualRetryBackend" in app
    assert "copyBackendDebugInfo" in app


def test_linux_apprun_startup_hardening():
    """Memastikan linux/AppRun mencatat log server.log, cek port cerdas, dan error GUI."""
    apprun = APPRUN.read_text(encoding="utf-8")

    assert 'SERVER_LOG="${DATA_DIR}/server.log"' in apprun
    assert 'ALREADY_RUNNING' in apprun
    assert 'for i in {1..75}' in apprun
    assert 'zenity' in apprun
    assert 'kdialog' in apprun
