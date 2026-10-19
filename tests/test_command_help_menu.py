import os
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_dialog_command_help_cleaned_up_items():
    """Memverifikasi bahwa 6 item perintah yang sudah dimuat di tab menu telah dihapus dari dialog_command_help.xml."""
    xml_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "layout", "dialog_command_help.xml")
    assert os.path.exists(xml_path), f"File {xml_path} tidak ditemukan"

    with open(xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    removed_ids = [
        "cmd_item_musim",
        "cmd_item_airing",
        "cmd_item_riwayat",
        "cmd_item_favorit",
        "cmd_item_katalog",
        "cmd_item_genre",
    ]

    for item_id in removed_ids:
        assert item_id not in content, f"ID redundan {item_id} masih ditemukan di dialog_command_help.xml"

def test_dialog_command_help_retained_items():
    """Memverifikasi bahwa 12 item perintah utilitas/sistem/AI tetap dipertahankan di dialog_command_help.xml."""
    xml_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "layout", "dialog_command_help.xml")
    with open(xml_path, "r", encoding="utf-8") as f:
        content = f.read()

    retained_ids = [
        "cmd_item_season",
        "cmd_item_source",
        "cmd_item_ping",
        "cmd_item_ai",
        "cmd_item_apikey",
        "cmd_item_gemini",
        "cmd_item_groq",
        "cmd_item_ollama",
        "cmd_item_model",
        "cmd_item_logs",
        "cmd_item_update",
        "cmd_item_clear",
        "cmd_item_haptic",
    ]

    for item_id in retained_ids:
        assert item_id in content, f"Item utilitas {item_id} tidak ditemukan di dialog_command_help.xml"

def test_main_activity_show_command_help_dialog_sync():
    """Memverifikasi bahwa MainActivity.java tidak mereferensikan ID yang dihapus dan cmdItemIds sinkron."""
    java_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "MainActivity.java")
    assert os.path.exists(java_path)

    with open(java_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ekstrak fungsi showCommandHelpDialog
    start_marker = "private void showCommandHelpDialog() {"
    end_marker = "dialog.show();"
    assert start_marker in content
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx)
    dialog_fn = content[start_idx:end_idx]

    removed_ids = [
        "cmd_item_musim",
        "cmd_item_airing",
        "cmd_item_riwayat",
        "cmd_item_favorit",
        "cmd_item_katalog",
        "cmd_item_genre",
    ]

    for item_id in removed_ids:
        assert item_id not in dialog_fn, f"ID {item_id} masih direferensikan dalam showCommandHelpDialog()"

    # Pastikan cmdItemIds memuat item yang tersisa
    retained_ids = [
        "cmd_item_season",
        "cmd_item_source",
        "cmd_item_ping",
        "cmd_item_ai",
        "cmd_item_apikey",
        "cmd_item_gemini",
        "cmd_item_groq",
        "cmd_item_ollama",
        "cmd_item_model",
        "cmd_item_logs",
        "cmd_item_update",
        "cmd_item_clear",
        "cmd_item_haptic",
    ]
    for item_id in retained_ids:
        assert item_id in dialog_fn, f"ID {item_id} tidak ditemukan dalam showCommandHelpDialog()"

def test_terminal_commands_still_supported_in_main_activity():
    """Memverifikasi bahwa pengetikan perintah di search bar tetap mendukung seluruh perintah tab."""
    java_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "MainActivity.java")
    with open(java_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'case "musim":' in content
    assert 'case "airing":' in content
    assert 'case "katalog":' in content
    assert 'case "genre":' in content
    assert 'case "riwayat":' in content
    assert 'case "favorit":' in content
    assert 'case "haptic":' in content
    assert 'case "getar":' in content
