import os
import re
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_activity_detail_folded_synopsis_xml():
    layout_path = os.path.join(ROOT_DIR, "android/app/src/main/res/layout/activity_detail.xml")
    assert os.path.exists(layout_path), f"Layout tidak ditemukan: {layout_path}"
    with open(layout_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pastikan kontainer sinopsis ada dengan ID yang tepat
    assert "android:id=\"@+id/layout_detail_synopsis\"" in content
    assert "android:id=\"@+id/tv_detail_synopsis\"" in content
    assert "android:id=\"@+id/btn_toggle_synopsis\"" in content

    # Pastikan default maxLines adalah 2 untuk mode folded ringkas
    assert "android:maxLines=\"2\"" in content
    assert "android:ellipsize=\"end\"" in content

    # Pastikan layout menganimasikan perubahan ukuran (smooth transition)
    assert "android:animateLayoutChanges=\"true\"" in content

    # Pastikan juga layout-land (Android TV) memiliki kontainer sinopsis yang valid
    land_path = os.path.join(ROOT_DIR, "android/app/src/main/res/layout-land/activity_detail.xml")
    assert os.path.exists(land_path), f"Layout landscape tidak ditemukan: {land_path}"
    with open(land_path, "r", encoding="utf-8") as f:
        land_content = f.read()

    assert "android:id=\"@+id/layout_detail_synopsis\"" in land_content
    assert "android:id=\"@+id/tv_detail_synopsis\"" in land_content
    assert "android:id=\"@+id/btn_toggle_synopsis\"" in land_content



def test_detail_activity_logic_and_tv_isolation():
    java_path = os.path.join(ROOT_DIR, "android/app/src/main/java/id/tatap/app/DetailActivity.java")
    assert os.path.exists(java_path), f"DetailActivity.java tidak ditemukan: {java_path}"
    with open(java_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Pastikan Intent extra synopsis dibaca
    assert "getIntent().getStringExtra(\"synopsis\")" in code

    # Pastikan view sinopsis diikat di onCreate
    assert "R.id.layout_detail_synopsis" in code
    assert "R.id.tv_detail_synopsis" in code
    assert "R.id.btn_toggle_synopsis" in code
    assert "setupSynopsis(" in code

    # Pastikan isolasi 100% Android TV di mana layout_detail_synopsis di-hide (View.GONE)
    assert "TvFocusHelper.isTv(this)" in code

    # Pastikan mekanisme 2-state toggle (Selengkapnya vs Lipat ke Judul)
    assert "Selengkapnya ▼" in code
    assert "Lipat ke Judul ▲" in code
    assert "tvSynopsis.setMaxLines(defaultLines)" in code
    assert "tvSynopsis.setMaxLines(Integer.MAX_VALUE)" in code


def test_anime_adapter_propagates_synopsis():
    adapter_path = os.path.join(ROOT_DIR, "android/app/src/main/java/id/tatap/app/AnimeAdapter.java")
    assert os.path.exists(adapter_path), f"AnimeAdapter.java tidak ditemukan: {adapter_path}"
    with open(adapter_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Pastikan AnimeAdapter mengambil field synopsis dari JSONObject item dan menyematkannya ke Intent
    assert "item.optString(\"synopsis\"" in code
    assert "intent.putExtra(\"synopsis\", synopsis)" in code


def test_backend_synopsis_support():
    hi_path = os.path.join(ROOT_DIR, "backend/api/hianime.py")
    assert os.path.exists(hi_path)
    with open(hi_path, "r", encoding="utf-8") as f:
        hi_code = f.read()
    assert "def hianime_synopsis(" in hi_code

    main_path = os.path.join(ROOT_DIR, "backend/main.py")
    assert os.path.exists(main_path)
    with open(main_path, "r", encoding="utf-8") as f:
        main_code = f.read()
    assert "hianime_synopsis" in main_code
    assert "\"synopsis\"" in main_code
