"""
tests/test_player_gestures.py - Test suite for Android PlayerActivity gesture controls.
Verifies top/bottom exclusion zones, horizontal edge zoning, neutral central deadzone,
and sensitivity dampening.
"""

import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JAVA_FILE = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "PlayerActivity.java")


def test_player_activity_gesture_fields_and_methods():
    """Memverifikasi bahwa field activeGestureZone dan handler gesture dideklarasikan."""
    assert os.path.exists(JAVA_FILE), "PlayerActivity.java tidak ditemukan!"
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    assert "private int activeGestureZone = 0;" in code
    assert "private float currentVolumeFraction = -1f;" in code


def test_player_activity_top_bottom_exclusion_zones():
    """Memverifikasi bahwa exclusion zone atas (notifikasi/jam) dan bawah (navigasi) terpasang."""
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    # Top exclusion zone untuk bilah status / notifikasi (minimal 56dp atau 16% tinggi)
    assert "float topExclusion = Math.max(dpToPx(56), viewHeight * 0.16f);" in code
    # Bottom exclusion zone untuk bilah navigasi
    assert "float bottomExclusion = viewHeight - Math.max(dpToPx(44), viewHeight * 0.12f);" in code
    # Pengecekan koordinat sentuhan awal
    assert "if (e1.getY() < topExclusion || e1.getY() > bottomExclusion)" in code


def test_player_activity_horizontal_edge_zoning_and_deadzone():
    """Memverifikasi pembagian zona: Kiri 35% (kecerahan), Kanan 35% (volume), dan Tengah 30% (deadzone)."""
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    # Kiri <= 35% lebar layar untuk brightness
    assert "e1.getX() <= viewWidth * 0.35f" in code
    # Kanan >= 65% lebar layar untuk volume
    assert "e1.getX() >= viewWidth * 0.65f" in code
    # Sisa di antara 35% s/d 65% adalah deadzone yang mengembalikan false
    assert "activeGestureZone == 0" in code


def test_player_activity_gesture_sensitivity_and_slop():
    """Memverifikasi peredaman sensitivitas (0.85x) dan ambang batas pergeseran awal (slop >= 14dp)."""
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    # Ambang batas awal (slop 14dp dan dominan vertikal 1.25x)
    assert "totalDeltaY < dpToPx(14) || totalDeltaY <= totalDeltaX * 1.25f" in code

    # Multiplier sensitivitas 0.85f (bukan 1.2f yang terlalu melompat)
    assert "percent * 0.85f" in code
    assert "percent * 1.2f" not in code

    # Android TV guard
    assert "if (TvFocusHelper.isTv(PlayerActivity.this)) return false;" in code
