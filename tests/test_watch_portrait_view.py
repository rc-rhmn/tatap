"""
tests/test_watch_portrait_view.py - Test suite for Mobile Android Watch Portrait View.
Verifies Manifest configuration, layout hierarchy, PlayerActivity orientation logic,
and strict Android TV landscape isolation.
"""

import os
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res")
JAVA_FILE = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "PlayerActivity.java")
MANIFEST_FILE = os.path.join(ROOT_DIR, "android", "app", "src", "main", "AndroidManifest.xml")
LAYOUT_FILE = os.path.join(RES_DIR, "layout", "activity_player.xml")


def test_android_manifest_player_activity_config():
    """Memverifikasi bahwa PlayerActivity di AndroidManifest mendukung orientasi user dan configChanges."""
    assert os.path.exists(MANIFEST_FILE), "AndroidManifest.xml tidak ditemukan!"
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'android:name=".PlayerActivity"' in content
    assert 'android:screenOrientation="user"' in content
    assert 'android:configChanges="orientation|screenSize|screenLayout|smallestScreenSize|keyboardHidden"' in content


def test_activity_player_layout_structure():
    """Memverifikasi tata letak panggung video atas dan panel episode portrait bawah."""
    assert os.path.exists(LAYOUT_FILE), "activity_player.xml tidak ditemukan!"
    with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Panggung video
    assert '@+id/fl_player_wrapper' in content
    assert '@+id/player_view' in content

    # Panel episode portrait bawah
    assert '@+id/layout_portrait_bottom' in content
    assert '@+id/tv_portrait_anime_title' in content
    assert '@+id/tv_portrait_current_ep' in content
    assert '@+id/btn_portrait_sub' in content
    assert '@+id/btn_portrait_quality' in content
    assert '@+id/btn_portrait_speed' in content
    assert '@+id/btn_portrait_fullscreen' in content
    assert '@+id/tv_portrait_ep_count' in content
    assert '@+id/btn_portrait_sort' in content
    assert '@+id/rv_portrait_ranges' in content
    assert '@+id/rv_portrait_episodes' in content


def test_player_activity_tv_isolation():
    """Memverifikasi bahwa Android TV dikunci 100% pada orientasi landscape sensor."""
    assert os.path.exists(JAVA_FILE), "PlayerActivity.java tidak ditemukan!"
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    # TV isolation pada onCreate
    assert "if (TvFocusHelper.isTv(this)) {" in code
    assert "setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);" in code

    # TV check pada updateLayoutForOrientation
    assert "boolean isTv = TvFocusHelper.isTv(this);" in code
    assert "if (isTv || orientation == Configuration.ORIENTATION_LANDSCAPE) {" in code


def test_player_activity_orientation_transition():
    """Memverifikasi metode transisi orientasi mulus (onConfigurationChanged & updateLayoutForOrientation)."""
    assert os.path.exists(JAVA_FILE), "PlayerActivity.java tidak ditemukan!"
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    assert "private void updateLayoutForOrientation(int orientation)" in code
    assert "public void onConfigurationChanged(@NonNull Configuration newConfig)" in code
    assert "private void showSystemUiForPortrait()" in code
    assert "private void exitLandscapeFullscreen()" in code


def test_player_activity_portrait_episode_adapter():
    """Memverifikasi adapter episode portrait dan range selector."""
    assert os.path.exists(JAVA_FILE), "PlayerActivity.java tidak ditemukan!"
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    assert "class PortraitEpisodeAdapter extends RecyclerView.Adapter<PortraitEpisodeAdapter.EpViewHolder>" in code
    assert "class PortraitRangeAdapter extends RecyclerView.Adapter<PortraitRangeAdapter.RangeViewHolder>" in code
    assert "private void updatePortraitEpisodeDisplay()" in code
    assert "switchEpisode(itemEp);" in code

    # Highlight episode aktif (#38BDF8 cyan)
    assert "0xFF38BDF8" in code
    assert "MEMUTAR" in code


def test_player_activity_back_press_behavior():
    """Memverifikasi penanganan tombol back pada mobile landscape yang kembali ke portrait terlebih dahulu."""
    assert os.path.exists(JAVA_FILE), "PlayerActivity.java tidak ditemukan!"
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    assert "if (!TvFocusHelper.isTv(this) && getResources().getConfiguration().orientation == Configuration.ORIENTATION_LANDSCAPE) {" in code
    assert "exitLandscapeFullscreen();" in code


def test_portrait_header_decluttering():
    """Memverifikasi bahwa header ExoPlayer dalam mode portrait dideclutter:
    5 tombol aksi berjejal disembunyikan (karena ada di panel bawah), padding kompak,
    dan tombol kembali menggunakan ic_arrow_back."""
    icon_file = os.path.join(RES_DIR, "drawable", "ic_arrow_back.xml")
    assert os.path.exists(icon_file), "ic_arrow_back.xml tidak ditemukan!"

    with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
        layout_code = f.read()
    assert '@drawable/ic_arrow_back' in layout_code

    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    # Memastikan tombol berjejal disembunyikan di portrait
    assert "btnAspect.setVisibility(View.GONE);" in code
    assert "btnQuality.setVisibility(View.GONE);" in code
    assert "btnSpeed.setVisibility(View.GONE);" in code
    assert "btnSubStyle.setVisibility(View.GONE);" in code
    assert "btnSubSelector.setVisibility(View.GONE);" in code
    assert "tvSubStatus.setVisibility(View.GONE);" in code
    assert "btnScreenLock.setVisibility(View.GONE);" in code
    assert "layoutTopBar.setPadding(dpToPx(12), dpToPx(8), dpToPx(12), dpToPx(8));" in code

    # Memastikan tombol berjejal dipulihkan saat landscape atau Android TV
    assert "btnAspect.setVisibility(View.VISIBLE);" in code
    assert "btnQuality.setVisibility(View.VISIBLE);" in code
    assert "btnSpeed.setVisibility(View.VISIBLE);" in code
    assert "btnSubStyle.setVisibility(View.VISIBLE);" in code
    assert "btnSubSelector.setVisibility(View.VISIBLE);" in code
    assert "tvSubStatus.setVisibility(View.VISIBLE);" in code

    # Memastikan layoutTopBar diisolasi total (GONE di portrait) dan tombol kembali portrait tersedia di panel bawah
    assert "btn_portrait_back" in layout_code, "Layout harus memuat tombol btn_portrait_back"
    assert "btnPortraitBack.setOnClickListener(v -> handleBackAction());" in code, "btnPortraitBack harus terhubung ke handleBackAction"
    assert "layoutTopBar.setVisibility(isLandscape ? visibility : View.GONE);" in code, "layoutTopBar harus GONE di portrait"
    assert 'android:id="@+id/layout_top_bar"' in layout_code
    assert 'android:visibility="gone"' in layout_code, "layout_top_bar harus berstatus gone di XML agar tidak berkedip saat inisialisasi"
    assert "layoutTopBar.setVisibility(isLandscape ? View.VISIBLE : View.GONE);" in code, "layoutTopBar harus langsung diset ke GONE saat orientasi portrait"


def test_portrait_edge_swipe_and_back_invoked():
    """Memverifikasi bahwa sistem edge swipe gesture back berjalan responsif:
    tidak terjebak immersive sticky pada portrait (clearFlags FLAG_FULLSCREEN, BEHAVIOR_DEFAULT),
    serta integrasi OnBackInvokedCallback (API 33+) dan unregister di onDestroy."""
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        code = f.read()

    # Clear FLAG_FULLSCREEN dan BEHAVIOR_DEFAULT pada portrait
    assert "getWindow().clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);" in code
    assert "controller.setSystemBarsBehavior(android.view.WindowInsetsController.BEHAVIOR_DEFAULT);" in code

    # OnBackInvokedCallback API 33+ registration & unregistration
    assert "getOnBackInvokedDispatcher().registerOnBackInvokedCallback(" in code
    assert "getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(" in code

    # handleBackAction hook
    assert "btnPlayerBack.setOnClickListener(v -> handleBackAction());" in code
    assert "private void handleBackAction()" in code
    assert "applySystemUiVisibility();" in code

