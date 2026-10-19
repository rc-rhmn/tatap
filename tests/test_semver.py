import os
import sys
import re
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
VERSION_FILE = os.path.join(ROOT_DIR, "VERSION")
BACKEND_VER_FILE = os.path.join(ROOT_DIR, "backend", "version.py")
ANDROID_VER_FILE = os.path.join(ROOT_DIR, "android", "app", "src", "main", "python", "backend", "version.py")
WINRES_FILE = os.path.join(ROOT_DIR, "launcher", "winres", "winres.json")
MANIFEST_FILE = os.path.join(ROOT_DIR, "launcher", "winres", "tatap.manifest")
FRONTEND_HTML = os.path.join(ROOT_DIR, "frontend", "index.html")

SEMVER_REGEX = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def get_root_version():
    assert os.path.exists(VERSION_FILE), "File VERSION di root repositori tidak ditemukan!"
    with open(VERSION_FILE, "r", encoding="utf-8") as f:
        v = f.read().strip()
    return v


def test_semver_format_validity():
    version = get_root_version()
    match = SEMVER_REGEX.match(version)
    assert match is not None, f"Versi '{version}' tidak mematuhi kaidah resmi SemVer 2.0.0!"
    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    assert major >= 0
    assert minor >= 0
    assert patch >= 0


def test_version_files_synchronized():
    root_v = get_root_version()

    # 1. backend/version.py
    with open(BACKEND_VER_FILE, "r", encoding="utf-8") as f:
        c = f.read()
    m = re.search(r'__version__\s*=\s*"([^"]+)"', c)
    assert m is not None, "backend/version.py tidak memiliki variabel __version__!"
    assert m.group(1) == root_v, f"backend/version.py ({m.group(1)}) != VERSION ({root_v})"

    # 2. Chaquopy backend/version.py
    with open(ANDROID_VER_FILE, "r", encoding="utf-8") as f:
        c = f.read()
    m2 = re.search(r'__version__\s*=\s*"([^"]+)"', c)
    assert m2 is not None, "Chaquopy backend/version.py tidak memiliki variabel __version__!"
    assert m2.group(1) == root_v, f"Chaquopy backend/version.py ({m2.group(1)}) != VERSION ({root_v})"

    # 3. launcher winres.json & manifest (Format X.Y.Z.0)
    win_v = f"{root_v}.0"
    with open(WINRES_FILE, "r", encoding="utf-8") as f:
        c = f.read()
    assert f'"{win_v}"' in c, f"winres.json tidak memuat versi {win_v}"

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        c = f.read()
    assert f'version="{win_v}"' in c, f"tatap.manifest tidak memuat versi {win_v}"

    # 4. frontend/index.html (Badge)
    with open(FRONTEND_HTML, "r", encoding="utf-8") as f:
        c = f.read()
    assert f"v{root_v}" in c, f"frontend/index.html tidak memuat tag versi v{root_v}"

    # 5. README.md (Download links must point to valid SemVer release <= root_v, targetting public release)
    README_FILE = os.path.join(ROOT_DIR, "README.md")
    with open(README_FILE, "r", encoding="utf-8") as f:
        c = f.read()
    m1 = re.search(r'tatap-release-v([0-9.]+)\.apk', c)
    m2 = re.search(r'tatap-tv-release-v([0-9.]+)\.apk', c)
    assert m1 is not None, "README.md tidak memuat tautan tatap-release-v*.apk"
    assert m2 is not None, "README.md tidak memuat tautan tatap-tv-release-v*.apk"
    assert m1.group(1) == m2.group(1), f"Versi APK mobile ({m1.group(1)}) dan TV ({m2.group(1)}) di README.md tidak sama!"
    from tools.bump_version import parse_semver, calculate_version_code
    parse_semver(m1.group(1))
    assert calculate_version_code(m1.group(1)) <= calculate_version_code(root_v), (
        f"Versi README.md (v{m1.group(1)}) tidak boleh melebihi VERSION root (v{root_v})"
    )


def test_sync_readme_version_utility(tmp_path, monkeypatch):
    from tools.bump_version import sync_readme_version
    import tools.bump_version as bv

    test_readme = tmp_path / "README.md"
    test_readme.write_text(
        "Download https://github.com/asfaraguest/tatap/releases/latest/download/tatap-release-v2.8.3.apk\n"
        "TV https://github.com/asfaraguest/tatap/releases/latest/download/tatap-tv-release-v2.8.3.apk"
    )
    monkeypatch.setattr(bv, "README_FILE", str(test_readme))
    sync_readme_version("2.9.0")
    content = test_readme.read_text()
    assert "tatap-release-v2.9.0.apk" in content
    assert "tatap-tv-release-v2.9.0.apk" in content


def test_version_code_calculation():
    from tools.bump_version import calculate_version_code
    assert calculate_version_code("2.3.0") == 20300
    assert calculate_version_code("2.3.1") == 20301
    assert calculate_version_code("2.10.0") == 21000
    assert calculate_version_code("3.0.0") == 30000


def test_update_checker_assets_filtering():
    # Simulasi filtering 4 aset resmi Tatap
    dummy_assets = [
        {"name": "tatap-release-v2.3.0.apk", "browser_download_url": "https://.../mobile.apk"},
        {"name": "tatap-tv-release-v2.3.0.apk", "browser_download_url": "https://.../tv.apk"},
        {"name": "tatap-windows-x64-portable.zip", "browser_download_url": "https://.../win.zip"},
        {"name": "Tatap-x86_64.AppImage", "browser_download_url": "https://.../linux.appimage"},
        {"name": "app-release.apk", "browser_download_url": "https://.../raw.apk"}, # Dilarang
    ]

    assets_out = {
        "android": "",
        "android_tv": "",
        "windows": "",
        "linux": ""
    }
    for a in dummy_assets:
        fname = a["name"].lower()
        dl_url = a["browser_download_url"]
        if "tatap-tv-release-" in fname and fname.endswith(".apk") and not fname.endswith(".idsig"):
            assets_out["android_tv"] = dl_url
        elif "tatap-release-" in fname and fname.endswith(".apk") and not fname.endswith(".idsig"):
            assets_out["android"] = dl_url
        elif "windows" in fname and fname.endswith(".zip"):
            assets_out["windows"] = dl_url
        elif fname.endswith(".appimage"):
            assets_out["linux"] = dl_url

    assert assets_out["android"] == "https://.../mobile.apk"
    assert assets_out["android_tv"] == "https://.../tv.apk"
    assert assets_out["windows"] == "https://.../win.zip"
    assert assets_out["linux"] == "https://.../linux.appimage"
