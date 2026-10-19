"""Test suite untuk verifikasi optimasi kinerja dan reduksi penggunaan CPU pada platform Linux AppImage."""
import os
import subprocess
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPRUN_PATH = os.path.join(REPO_ROOT, "linux", "AppRun")
BACKEND_MAIN = os.path.join(REPO_ROOT, "backend", "main.py")
ANDROID_BACKEND_MAIN = os.path.join(REPO_ROOT, "android", "app", "src", "main", "python", "backend", "main.py")
APP_JS = os.path.join(REPO_ROOT, "frontend", "js", "app.js")
STYLE_CSS = os.path.join(REPO_ROOT, "frontend", "css", "style.css")


def test_apprun_hardware_acceleration_and_cpu_flags():
    """Memastikan AppRun Linux memuat flag akselerasi hardware GPU, VA-API, dan Wayland native."""
    with open(APPRUN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Hardware acceleration & GPU decoding (VA-API / NVDEC)
    assert "--enable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL,CanvasOopRasterization" in content
    assert "--enable-gpu-rasterization" in content
    assert "--enable-zero-copy" in content
    assert "--ignore-gpu-blocklist" in content

    # Wayland native integration (hindari Xwayland translation overhead)
    assert "--ozone-platform-hint=auto" in content

    # Reduksi background services yang menyerap CPU
    assert "--disable-background-networking" in content
    assert "--disable-component-update" in content
    assert "--disable-sync" in content
    assert "--disable-default-apps" in content
    assert "--no-default-browser-check" in content
    assert "--no-first-run" in content
    assert "--disable-breakpad" in content
    assert "--disable-features=Translate,OptimizationHints,MediaRouter" in content


def test_backend_main_uvloop_httptools_and_no_access_log():
    """Memastikan backend/main.py memanfaatkan uvloop, httptools, dan menonaktifkan access_log."""
    with open(BACKEND_MAIN, "r", encoding="utf-8") as f:
        content = f.read()

    assert "import uvloop" in content, "uvloop auto-detection wajib ada di backend/main.py"
    assert "import httptools" in content, "httptools auto-detection wajib ada di backend/main.py"
    assert "access_log=False" in content, "access_log=False wajib ada untuk mengeliminasi logging segmen video"
    assert 'log_level="warning"' in content, "log_level warning wajib disetel untuk menekan CPU I/O overhead"

    # Verifikasi paritas Android Chaquopy
    with open(ANDROID_BACKEND_MAIN, "r", encoding="utf-8") as f:
        android_content = f.read()

    assert "import uvloop" in android_content, "Paritas Android Chaquopy harus identik"
    assert "import httptools" in android_content, "Paritas Android Chaquopy harus identik"
    assert "access_log=False" in android_content, "Paritas Android Chaquopy harus identik"


def test_frontend_ambient_canvas_throttling_and_guards():
    """Memastikan startAmbient di frontend/js/app.js menerapkan guards dan interval ter-throttle."""
    # Validasi sintaksis JS
    res = subprocess.run(["node", "--check", APP_JS], capture_output=True, text=True)
    assert res.returncode == 0, f"Sintaksis app.js gagal: {res.stderr}"

    with open(APP_JS, "r", encoding="utf-8") as f:
        js = f.read()

    # Guards untuk hemat daya dan CPU
    assert "if(document.hidden)return;" in js, "Bypass saat window/tab diminimalkan wajib ada"
    assert "if(isVideoFullscreen())return;" in js, "Bypass saat native fullscreen wajib ada"
    assert "},1200);" in js, "Interval sampling wajib disetel ke 1200ms (menyesuaikan durasi transisi CSS 1.2s)"

    # CSS strict containment
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        css = f.read()
    assert "contain:strict" in css, "contain:strict pada layer ambient wajib ada untuk isolasi GPU compositing"
