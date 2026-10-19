"""
Unit tests for Android Hold to Speed Up (Fast-Forward 2.0x) and Rewind feature.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_activity_player_xml_has_hold_hud():
    xml_path = ROOT / "android/app/src/main/res/layout/activity_player.xml"
    assert xml_path.exists(), "activity_player.xml harus ada"
    content = xml_path.read_text(encoding="utf-8")

    assert 'android:id="@+id/hud_hold_speed"' in content, "Elemen #hud_hold_speed harus ada di activity_player.xml"
    assert 'android:id="@+id/tv_hold_speed_icon"' in content, "Elemen #tv_hold_speed_icon harus ada"
    assert 'android:id="@+id/tv_hold_speed_text"' in content, "Elemen #tv_hold_speed_text harus ada"


def test_player_activity_java_has_hold_handlers():
    java_path = ROOT / "android/app/src/main/java/id/tatap/app/PlayerActivity.java"
    assert java_path.exists(), "PlayerActivity.java harus ada"
    content = java_path.read_text(encoding="utf-8")

    # onLongPress method
    assert "public void onLongPress(MotionEvent e)" in content, "onLongPress harus dioverride di GestureDetector"

    # Start and stop methods
    assert "startHoldingSpeed()" in content
    assert "stopHoldingSpeed()" in content
    assert "startHoldingRewind()" in content
    assert "stopHoldingRewind()" in content
    assert "holdRewindRunnable" in content

    # Cleanup in touch listener and onPause
    assert "if (isHoldingSpeed) {" in content
    assert "if (isHoldingRewind) {" in content
    assert "isHoldingSpeed || isHoldingRewind" in content
