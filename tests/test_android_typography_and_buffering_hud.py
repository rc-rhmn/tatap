import os
import re
import xml.etree.ElementTree as ET
import pytest

RES_DIR = os.path.join(os.path.dirname(__file__), "..", "android", "app", "src", "main", "res")


def test_dimens_typography_scale():
    dimens_path = os.path.join(RES_DIR, "values", "dimens.xml")
    assert os.path.isfile(dimens_path), f"Missing {dimens_path}"
    tree = ET.parse(dimens_path)
    root = tree.getroot()

    expected_tokens = {
        "text_display_large": "20sp",
        "text_headline": "17sp",
        "text_title_large": "15sp",
        "text_title_medium": "13sp",
        "text_body_large": "13.5sp",
        "text_body_medium": "12sp",
        "text_subhead": "12sp",
        "text_caption": "11sp",
        "text_badge": "9.5sp",
        "text_code": "11.5sp",
    }
    found = {}
    for elem in root.findall("dimen"):
        name = elem.attrib.get("name")
        if name in expected_tokens:
            found[name] = elem.text.strip()

    for token, val in expected_tokens.items():
        assert token in found, f"Missing token {token} in dimens.xml"
        assert found[token] == val, f"Token {token} has value {found[token]} != {val}"


def test_colors_typography_tokens():
    colors_path = os.path.join(RES_DIR, "values", "colors.xml")
    assert os.path.isfile(colors_path), f"Missing {colors_path}"
    tree = ET.parse(colors_path)
    root = tree.getroot()

    expected_colors = [
        "text_primary",
        "text_secondary",
        "text_muted",
        "text_dim",
        "text_accent",
        "text_success",
        "text_warning",
        "text_danger",
    ]
    found = {elem.attrib.get("name") for elem in root.findall("color")}
    for c in expected_colors:
        assert c in found, f"Missing semantic color token {c} in colors.xml"


def test_exoplayer_buffering_hud_capsule():
    # 1. bg_buffering_hud.xml shape
    bg_path = os.path.join(RES_DIR, "drawable", "bg_buffering_hud.xml")
    assert os.path.isfile(bg_path)
    with open(bg_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert 'android:shape="rectangle"' in content or 'shape="rectangle"' in content
    assert "corners" in content
    assert "stroke" in content

    # 2. activity_player.xml layout_buffering wrap_content
    player_path = os.path.join(RES_DIR, "layout", "activity_player.xml")
    with open(player_path, "r", encoding="utf-8") as f:
        player_xml = f.read()
    assert 'android:id="@+id/layout_buffering"' in player_xml
    # Make sure it uses wrap_content
    assert re.search(r'android:id="@\+id/layout_buffering"[^>]*android:layout_width="wrap_content"', player_xml)
    # Check tv_buffering_text typography
    assert 'android:id="@+id/tv_buffering_text"' in player_xml
    assert re.search(r'android:id="@\+id/tv_buffering_text"[^>]*android:textSize="@dimen/text_caption"', player_xml)
    assert re.search(r'android:id="@\+id/tv_buffering_text"[^>]*android:fontFamily="sans-serif-medium"', player_xml)


def test_no_faux_bolding_in_core_layouts():
    """Verify that TextViews do not combine sans-serif-medium with textStyle='bold'."""
    files_to_check = [
        "item_anime_card.xml",
        "item_episode.xml",
        "item_lane_header.xml",
        "item_range_chip.xml",
        "item_season_chip.xml",
        "activity_detail.xml",
        "dialog_command_help.xml",
    ]

    for fname in files_to_check:
        fpath = os.path.join(RES_DIR, "layout", fname)
        assert os.path.isfile(fpath), f"File {fname} missing"
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Split elements roughly by <TextView ... /> or <TextView ... >
        elements = re.findall(r'<TextView\b[^>]*>', content)
        for elem in elements:
            has_medium = 'fontFamily="sans-serif-medium"' in elem
            has_bold = 'textStyle="bold"' in elem
            # It's an error if both are present in the same TextView
            assert not (has_medium and has_bold), f"Faux bold found in {fname}: {elem}"


def test_dialog_command_help_descriptions_use_sans_serif():
    dialog_path = os.path.join(RES_DIR, "layout", "dialog_command_help.xml")
    with open(dialog_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Title should not be monospace
    assert 'android:text="Daftar Perintah (:command)"' in content
    # Descriptions of commands should use sans-serif and text_caption
    assert 'android:fontFamily="sans-serif"' in content
    assert 'android:textSize="@dimen/text_caption"' in content
