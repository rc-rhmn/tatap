"""
tests/test_screen_lock.py - Test suite for ExoPlayer Touch Screen Lock feature.
Verifies layout definitions, vector drawables, key guards, and TV isolation.
"""

import os
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res")
JAVA_FILE = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "PlayerActivity.java")
LAYOUT_FILE = os.path.join(RES_DIR, "layout", "activity_player.xml")


def test_screen_lock_vector_drawables():
    """Memverifikasi bahwa ic_lock.xml dan ic_lock_open.xml ada dan valid."""
    drawable_dir = os.path.join(RES_DIR, "drawable")
    android_ns = "{http://schemas.android.com/apk/res/android}"

    for icon in ["ic_lock.xml", "ic_lock_open.xml"]:
        icon_path = os.path.join(drawable_dir, icon)
        assert os.path.exists(icon_path), f"File {icon} tidak ditemukan!"
        tree = ET.parse(icon_path)
        root = tree.getroot()
        assert root.tag == "vector", f"{icon} root element harus 'vector'"
        width = root.attrib.get(f"{android_ns}width")
        height = root.attrib.get(f"{android_ns}height")
        assert width in ["14dp", "15dp", "16dp"], f"{icon} width {width} tidak proporsional"
        assert height in ["14dp", "15dp", "16dp"], f"{icon} height {height} tidak proporsional"

    # Periksa bg_screen_lock_button.xml
    bg_path = os.path.join(drawable_dir, "bg_screen_lock_button.xml")
    assert os.path.exists(bg_path), "bg_screen_lock_button.xml tidak ditemukan!"
    tree = ET.parse(bg_path)
    root = tree.getroot()
    assert root.tag == "shape", "bg_screen_lock_button.xml harus berupa shape drawable"


def test_screen_lock_layout_elements():
    """Memverifikasi elemen btn_screen_lock dan btn_screen_unlock pada activity_player.xml."""
    assert os.path.exists(LAYOUT_FILE), "activity_player.xml tidak ditemukan!"
    with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert '@+id/btn_screen_lock' in content, "activity_player.xml harus memuat btn_screen_lock"
    assert '@+id/btn_screen_unlock' in content, "activity_player.xml harus memuat btn_screen_unlock"
    assert 'android:visibility="gone"' in content, "Tombol lock/unlock harus memiliki default visibility gone"


def test_player_activity_screen_lock_logic():
    """Memverifikasi logika screen lock, isolasi TV, dan proteksi sentuhan di PlayerActivity.java."""
    assert os.path.exists(JAVA_FILE), "PlayerActivity.java tidak ditemukan!"
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    # Variabel status
    assert "private boolean isScreenLocked = false;" in code
    assert "btnScreenLock = findViewById(R.id.btn_screen_lock);" in code
    assert "btnScreenUnlock = findViewById(R.id.btn_screen_unlock);" in code

    # Metode kontrol
    assert "private void lockScreen()" in code
    assert "private void unlockScreen()" in code
    assert "private void showUnlockButtonBriefly()" in code
    assert "private final Runnable hideUnlockButtonRunnable" in code

    # Isolasi Android TV
    assert "TvFocusHelper.isTv(this)" in code
    assert "if (TvFocusHelper.isTv(this)) return;" in code

    # Pencegatan sentuhan (touch interception) saat terkunci
    assert "if (isScreenLocked) {" in code
    assert "return true;" in code

    # Proteksi tombol Back
    assert "onBackPressed" in code
    assert "KEYCODE_BACK" in code
