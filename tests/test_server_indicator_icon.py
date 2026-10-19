"""
tests/test_server_indicator_icon.py - Test suite for Backend Server Indicator Icon.
Verifies ic_server.xml exists, is valid vector, ic_power.xml is removed,
and activity_main.xml uses ic_server with correct accessibility description.
"""

import os
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res")
DRAWABLE_DIR = os.path.join(RES_DIR, "drawable")
LAYOUT_FILE = os.path.join(RES_DIR, "layout", "activity_main.xml")


def test_ic_server_vector_drawable():
    """Memverifikasi bahwa ic_server.xml ada, valid vector drawable, dan berdimensi 20dp."""
    server_icon_path = os.path.join(DRAWABLE_DIR, "ic_server.xml")
    assert os.path.exists(server_icon_path), "ic_server.xml harus ada di folder drawable!"

    tree = ET.parse(server_icon_path)
    root = tree.getroot()
    android_ns = "{http://schemas.android.com/apk/res/android}"

    assert root.tag == "vector", "ic_server.xml root element harus 'vector'"
    width = root.attrib.get(f"{android_ns}width")
    height = root.attrib.get(f"{android_ns}height")
    assert width == "20dp", f"ic_server.xml width harus 20dp, didapat {width}"
    assert height == "20dp", f"ic_server.xml height harus 20dp, didapat {height}"


def test_ic_power_is_removed():
    """Memverifikasi bahwa file lama ic_power.xml telah dihapus tuntas."""
    power_icon_path = os.path.join(DRAWABLE_DIR, "ic_power.xml")
    assert not os.path.exists(power_icon_path), "ic_power.xml seharusnya sudah dihapus!"


def test_activity_main_uses_ic_server():
    """Memverifikasi activity_main.xml mengikat @drawable/ic_server dan deskripsi yang benar."""
    assert os.path.exists(LAYOUT_FILE), "activity_main.xml tidak ditemukan!"
    with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert '@drawable/ic_server' in content, "activity_main.xml harus menggunakan @drawable/ic_server"
    assert '@drawable/ic_power' not in content, "activity_main.xml tidak boleh lagi memuat @drawable/ic_power"
    assert 'android:contentDescription="Status Backend Server"' in content
