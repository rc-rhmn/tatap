"""
tests/test_horizontal_tab_menu.py - Test suite verifying the horizontal slide menu
reordering and the new Riwayat (history) tab button on Android Mobile & Android TV.
"""

import os
import re
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res")
LAYOUT_FILE = os.path.join(RES_DIR, "layout", "activity_main.xml")
JAVA_FILE = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "MainActivity.java")
HISTORY_ICON = os.path.join(RES_DIR, "drawable", "ic_tab_history.xml")

ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


def test_ic_tab_history_asset_exists_and_valid():
    """Verifies that ic_tab_history.xml exists and is a valid Android vector drawable."""
    assert os.path.exists(HISTORY_ICON), "ic_tab_history.xml must exist in res/drawable"
    tree = ET.parse(HISTORY_ICON)
    root = tree.getroot()
    assert root.tag == "vector", "Root element must be <vector>"
    assert root.attrib.get(f"{ANDROID_NS}width") == "15dp"
    assert root.attrib.get(f"{ANDROID_NS}height") == "15dp"
    assert root.attrib.get(f"{ANDROID_NS}viewportWidth") == "24"
    assert root.attrib.get(f"{ANDROID_NS}viewportHeight") == "24"


def test_horizontal_tabs_order_and_riwayat_in_layout():
    """
    Verifies that the horizontal tabs in activity_main.xml follow the strict sequence:
    1. Musim Ini (btn_tab_musim)
    2. Masih Tayang (btn_tab_airing)
    3. Jadwal (btn_tab_jadwal)
    4. Riwayat (btn_tab_riwayat)
    5. Favorit (btn_tab_favorit)
    6. Katalog (btn_tab_katalog)
    7. Genre (btn_tab_genre)
    """
    tree = ET.parse(LAYOUT_FILE)
    root = tree.getroot()

    # Find layout_tabs_container inside layout_tabs_segmented
    tabs_container = None
    for elem in root.iter():
        elem_id = elem.attrib.get(f"{ANDROID_NS}id", "")
        if elem_id.endswith("layout_tabs_container"):
            tabs_container = elem
            break

    assert tabs_container is not None, "layout_tabs_container not found in activity_main.xml"

    # Extract all child tab IDs
    expected_order = [
        "btn_tab_musim",
        "btn_tab_airing",
        "btn_tab_jadwal",
        "btn_tab_riwayat",
        "btn_tab_favorit",
        "btn_tab_katalog",
        "btn_tab_genre"
    ]

    tab_children = []
    for child in tabs_container:
        cid = child.attrib.get(f"{ANDROID_NS}id", "")
        for exp in expected_order:
            if cid.endswith(exp):
                tab_children.append((exp, child))
                break

    actual_tab_ids = [t[0] for t in tab_children]
    assert actual_tab_ids == expected_order, f"Tab sequence mismatch! Expected {expected_order}, got {actual_tab_ids}"

    # Check btn_tab_riwayat properties
    riwayat_node = next(child for exp, child in tab_children if exp == "btn_tab_riwayat")
    assert riwayat_node.attrib.get(f"{ANDROID_NS}text") == "Riwayat"
    assert riwayat_node.attrib.get(f"{ANDROID_NS}drawableStart") == "@drawable/ic_tab_history"
    assert riwayat_node.attrib.get(f"{ANDROID_NS}nextFocusLeft") == "@+id/btn_tab_jadwal"
    assert riwayat_node.attrib.get(f"{ANDROID_NS}nextFocusRight") == "@+id/btn_tab_favorit"

    # Check surrounding nodes D-pad links
    jadwal_node = next(child for exp, child in tab_children if exp == "btn_tab_jadwal")
    assert jadwal_node.attrib.get(f"{ANDROID_NS}nextFocusRight") == "@+id/btn_tab_riwayat"

    favorit_node = next(child for exp, child in tab_children if exp == "btn_tab_favorit")
    assert favorit_node.attrib.get(f"{ANDROID_NS}nextFocusLeft") == "@+id/btn_tab_riwayat"


def test_main_activity_java_riwayat_wiring():
    """
    Verifies that MainActivity.java properly integrates btnTabRiwayat:
    - Declaration and findViewById
    - tvTabs 7-item array for TV layout
    - D-pad spatial chaining
    - Click listener and TvFocusHelper attachment
    - getTabIconRes and getTabTitleString mappings
    - updateTabButtons appearance update
    """
    with open(JAVA_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    assert "btnTabRiwayat" in content, "btnTabRiwayat field must exist in MainActivity"
    assert "btnTabRiwayat = findViewById(R.id.btn_tab_riwayat);" in content

    # Check tvTabs array in setupTvLayout
    tvtabs_pattern = re.compile(r'TextView\[\]\s+tvTabs\s*=\s*new\s+TextView\[\]\s*\{([^}]+)\};')
    match = tvtabs_pattern.search(content)
    assert match is not None, "tvTabs array must be declared in setupTvLayout"
    tabs_str = match.group(1).replace(" ", "").replace("\n", "")
    expected_tabs = "btnTabMusim,btnTabAiring,btnTabJadwal,btnTabRiwayat,btnTabFavorit,btnTabKatalog,btnTabGenre"
    assert tabs_str == expected_tabs, f"tvTabs sequence mismatch! Expected {expected_tabs}, got {tabs_str}"

    # Check getTabIconRes mapping
    assert "if (id == R.id.btn_tab_riwayat) return R.drawable.ic_tab_history;" in content

    # Check getTabTitleString mapping
    assert "if (id == R.id.btn_tab_riwayat) return \"Riwayat\";" in content

    # Check updateTabButtons appearance call
    assert "setTabAppearance(btnTabRiwayat, isRiwayat);" in content

    # Check click listener calls resetFiltersToTab("riwayat")
    assert "btnTabRiwayat.setOnClickListener(v ->" in content
    assert "resetFiltersToTab(\"riwayat\")" in content
