import os
import re
import xml.etree.ElementTree as ET
import pytest
from starlette.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def test_chaquopy_parity_backend_main():
    """Memverifikasi bahwa backend/main.py dan android/app/src/main/python/backend/main.py 100% identik."""
    orig_path = os.path.join(ROOT_DIR, "backend", "main.py")
    chaquo_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "python", "backend", "main.py")
    with open(orig_path, "r", encoding="utf-8") as f1, open(chaquo_path, "r", encoding="utf-8") as f2:
        assert f1.read() == f2.read(), "backend/main.py and Chaquopy backend/main.py are not identical!"

def test_backend_update_check_contract():
    """Memverifikasi kontrak response /api/update/check mencakup field notes, body, dan 4 aset resmi."""
    from backend.main import app
    client = TestClient(app)
    resp = client.get("/api/update/check")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    res_data = data.get("data", {})
    assert "current_version" in res_data
    assert "latest_version" in res_data
    assert "tag_name" in res_data
    assert "has_update" in res_data
    assert "notes" in res_data
    assert "body" in res_data
    assert "assets" in res_data

    assets = res_data["assets"]
    assert "android" in assets
    assert "android_tv" in assets
    assert "windows" in assets
    assert "linux" in assets

def test_manifest_permissions_and_fileprovider():
    """Memverifikasi izin REQUEST_INSTALL_PACKAGES dan FileProvider pada AndroidManifest.xml."""
    manifest_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "AndroidManifest.xml")
    assert os.path.exists(manifest_path)
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "android.permission.REQUEST_INSTALL_PACKAGES" in content
    assert "androidx.core.content.FileProvider" in content
    assert "${applicationId}.fileprovider" in content
    assert "@xml/file_paths" in content

def test_file_paths_xml_configuration():
    """Memverifikasi file_paths.xml mengizinkan akses ke direktori cache dan external-files."""
    xml_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "xml", "file_paths.xml")
    assert os.path.exists(xml_path)
    tree = ET.parse(xml_path)
    root = tree.getroot()

    tags = [child.tag for child in root]
    assert "cache-path" in tags or "external-cache-path" in tags
    assert "external-files-path" in tags

def test_update_dialog_layouts():
    """Memverifikasi elemen view pada dialog_app_update.xml dan dialog_app_download.xml."""
    dialog_update = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "layout", "dialog_app_update.xml")
    dialog_dl = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "layout", "dialog_app_download.xml")

    with open(dialog_update, "r", encoding="utf-8") as f:
        u_content = f.read()

    assert "tv_update_title" in u_content
    assert "tv_update_version_badge" in u_content
    assert "tv_update_notes" in u_content
    assert "btn_update_now" in u_content
    assert "btn_update_later" in u_content
    assert "tv_update_fallback_browser" in u_content

    with open(dialog_dl, "r", encoding="utf-8") as f:
        d_content = f.read()

    assert "pb_download_horizontal" in d_content
    assert "tv_download_status" in d_content
    assert "tv_download_percent" in d_content
    assert "btn_cancel_download" in d_content

def test_app_update_manager_java_structure():
    """Memverifikasi struktur kode dan logika pada AppUpdateManager.java."""
    manager_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "AppUpdateManager.java")
    assert os.path.exists(manager_path)

    with open(manager_path, "r", encoding="utf-8") as f:
        code = f.read()

    assert "public static final int REQUEST_CODE_INSTALL_PERMISSION = 7129;" in code
    assert "public static AppUpdateManager getInstance()" in code
    assert "checkUpdate(Activity activity" in code
    assert "startDownload(Activity activity" in code
    assert "installApk(Activity activity" in code
    assert "openConnectionWithRedirects(" in code
    assert "TvFocusHelper.isTv(" in code
    assert "FileProvider.getUriForFile(" in code
    assert "package:id.tatap.app" not in code  # Dynamic package name via activity.getPackageName()
    assert "activity.getPackageName() + \".fileprovider\"" in code

def test_main_activity_update_integration():
    """Memverifikasi integrasi AppUpdateManager di MainActivity.java dan ketiadaan auto-check saat startup."""
    main_activity_path = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "MainActivity.java")
    assert os.path.exists(main_activity_path)

    with open(main_activity_path, "r", encoding="utf-8") as f:
        code = f.read()

    # Delegasi ke AppUpdateManager
    assert "AppUpdateManager.getInstance().checkUpdate" in code
    assert "AppUpdateManager.REQUEST_CODE_INSTALL_PERMISSION" in code
    assert "AppUpdateManager.getInstance().onInstallPermissionResult" in code

    # Memastikan TIDAK ADA pemanggilan otomatis update di onCreate
    on_create_idx = code.find("protected void onCreate(")
    assert on_create_idx != -1
    # Ambil blok onCreate (sekitar 300 baris berikutnya)
    on_create_block = code[on_create_idx:on_create_idx + 8000]
    assert "checkForUpdates(" not in on_create_block
    assert "checkUpdate(" not in on_create_block
