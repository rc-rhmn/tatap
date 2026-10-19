#!/usr/bin/env python3
"""
Tatap Windows Portable App Builder
----------------------------------
Script ini mengotomatiskan pembuatan bundle portable Windows untuk Tatap:
1. Mengunduh official Python 3.11 Embeddable x64 (python.org)
2. Mengunduh wheel packages Windows x64 (curl_cffi, fastapi, uvicorn, dll.)
3. Mengekstrak dan mengonfigurasi embedded runtime (python311._pth)
4. Mengompilasi launcher native Windows Tatap.exe menggunakan Go
5. Menyalin aset backend dan frontend
6. Membungkus hasil build ke dalam zip: dist/tatap-windows-x64-portable.zip
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess
import glob

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(ROOT_DIR, "dist")
OUTPUT_FOLDER = os.path.join(DIST_DIR, "tatap-windows-portable")
CACHE_DOWNLOADS = os.path.join(ROOT_DIR, ".build_cache")

PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
PYTHON_ZIP_NAME = "python-3.11.9-embed-amd64.zip"

def log(msg):
    print(f"\n[BUILD] {msg}")

def download_file(url, target_path, retries=3):
    if os.path.exists(target_path):
        log(f"Menggunakan file cache: {os.path.basename(target_path)}")
        return
    log(f"Mengunduh {url} ...")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    
    # Coba gunakan curl jika ada
    if shutil.which("curl"):
        for attempt in range(1, retries + 1):
            try:
                subprocess.run(["curl", "-sSL", "--retry", "3", "--retry-connrefused", "-o", target_path, url], check=True)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                    log(f"Selesai mengunduh {os.path.basename(target_path)} via curl")
                    return
            except subprocess.CalledProcessError:
                if attempt == retries:
                    raise
                import time
                time.sleep(2)

    # Fallback urllib
    import time
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as response, open(target_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            log(f"Selesai mengunduh {os.path.basename(target_path)}")
            return
        except Exception as e:
            if attempt == retries:
                raise
            log(f"Percobaan download {attempt} gagal ({e}). Mencoba lagi...")
            time.sleep(2)

def extract_zip(zip_path, target_dir):
    log(f"Mengekstrak {os.path.basename(zip_path)} ke {target_dir} ...")
    os.makedirs(target_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)

def setup_runtime(runtime_dir):
    log("Menyiapkan runtime Python 3.11 Embeddable...")
    embed_zip = os.path.join(CACHE_DOWNLOADS, PYTHON_ZIP_NAME)
    download_file(PYTHON_EMBED_URL, embed_zip)
    extract_zip(embed_zip, runtime_dir)

    # Konfigurasi python311._pth
    pth_file = os.path.join(runtime_dir, "python311._pth")
    if os.path.exists(pth_file):
        log("Mengonfigurasi python311._pth ...")
        content = """python311.zip
.
site-packages
..\\backend
..
import site
"""
        with open(pth_file, "w") as f:
            f.write(content)

def install_windows_dependencies(site_packages_dir):
    log("Memasang dependencies Python untuk Windows x64 via pip...")
    if os.path.exists(site_packages_dir):
        shutil.rmtree(site_packages_dir)
    os.makedirs(site_packages_dir, exist_ok=True)

    # uvicorn[standard] menyertakan uvloop yang hanya ada di unix/posix.
    # Di Windows, uvicorn berjalan dengan asyncio default + h11.
    win_packages = [
        "fastapi==0.115.6",
        "uvicorn==0.34.0",
        "aiosqlite==0.22.1",
        "httpx>=0.27",
        "curl_cffi>=0.7.0",
        "python-dotenv==1.0.1",
        "cryptography>=41.0.0",
    ]

    cmd = [
        sys.executable, "-m", "pip", "install",
        "--target", site_packages_dir,
        "--only-binary=:all:",
        "--platform", "win_amd64",
        "--python-version", "311",
        "--no-warn-script-location"
    ] + win_packages

    subprocess.run(cmd, check=True)
    log(f"Dependencies Windows x64 berhasil dipasang ke {site_packages_dir}")

def build_launcher(target_exe):
    log("Mengompilasi launcher native Windows Tatap.exe dengan Go...")
    launcher_dir = os.path.join(ROOT_DIR, "launcher")
    launcher_src = os.path.join(launcher_dir, "main.go")
    if not os.path.exists(launcher_src):
        raise FileNotFoundError(f"Source launcher tidak ditemukan: {launcher_src}")

    # Resource Windows (icon + manifest ter-embed di exe) memakai file
    # rsrc_windows_amd64.syso yang sudah ter-commit. Regenerasi via go-winres
    # hanya bila file hilang, karena output go-winres versi lama tidak
    # kompatibel dengan toolchain Go baru (unknown relocation type).
    # Regenerasi manual: cd launcher && go-winres make
    winres_dir = os.path.join(launcher_dir, "winres")
    syso_file = os.path.join(launcher_dir, "rsrc_windows_amd64.syso")
    if not os.path.exists(syso_file):
        gowinres = shutil.which("go-winres") or os.path.expanduser("~/go/bin/go-winres")
        if os.path.isdir(winres_dir) and (shutil.which("go-winres") or os.path.isfile(gowinres)):
            log("Resource .syso hilang, membangun ulang (icon + manifest)...")
            subprocess.run([gowinres, "make"],
                           check=True, cwd=launcher_dir)
        if not os.path.exists(syso_file):
            raise FileNotFoundError(
                "Resource launcher tidak ditemukan: rsrc_windows_amd64.syso "
                "(dan go-winres tidak tersedia untuk membuatnya)")

    env = os.environ.copy()
    env["GOOS"] = "windows"
    env["GOARCH"] = "amd64"

    cmd = [
        "go", "build",
        "-ldflags", "-H=windowsgui -w",
        "-o", target_exe,
        "."
    ]
    subprocess.run(cmd, env=env, check=True, cwd=launcher_dir)
    log(f"Berhasil membuat: {target_exe} ({os.path.getsize(target_exe):,} bytes)")

def copy_project_files(target_dir):
    log("Menyalin kode aplikasi dan aset frontend...")
    # Copy backend
    backend_dest = os.path.join(target_dir, "backend")
    if os.path.exists(backend_dest):
        shutil.rmtree(backend_dest)
    shutil.copytree(
        os.path.join(ROOT_DIR, "backend"),
        backend_dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "anime.db*")
    )

    # Copy frontend
    frontend_dest = os.path.join(target_dir, "frontend")
    if os.path.exists(frontend_dest):
        shutil.rmtree(frontend_dest)
    shutil.copytree(
        os.path.join(ROOT_DIR, "frontend"),
        frontend_dest
    )

    # Buat direktori bin/ dan cache/
    os.makedirs(os.path.join(target_dir, "bin"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "cache"), exist_ok=True)

    # Salin README dan script bantuan
    shutil.copy2(os.path.join(ROOT_DIR, "windows", "README.txt"), os.path.join(target_dir, "README.txt"))
    shutil.copy2(os.path.join(ROOT_DIR, "windows", "run-console.bat"), os.path.join(target_dir, "run-console.bat"))
    shutil.copy2(os.path.join(ROOT_DIR, "windows", "Stop-Tatap.bat"), os.path.join(target_dir, "Stop-Tatap.bat"))
    # logic-guide.md opsional (tidak ada di repo publik).
    guide_src = os.path.join(ROOT_DIR, "logic-guide.md")
    if os.path.exists(guide_src):
        shutil.copy2(guide_src, os.path.join(target_dir, "logic-guide.md"))
    # Salin icon launcher untuk referensi/packaging berikutnya.
    icon_src = os.path.join(ROOT_DIR, "launcher", "icon.ico")
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, os.path.join(target_dir, "icon.ico"))

def create_portable_zip(source_dir, output_zip):
    log(f"Membuat arsip zip portable: {output_zip} ...")
    base_name = output_zip.replace(".zip", "")
    shutil.make_archive(base_name, 'zip', root_dir=os.path.dirname(source_dir), base_dir=os.path.basename(source_dir))
    zip_size = os.path.getsize(output_zip)
    log(f"Paket portable selesai: {output_zip} ({zip_size / (1024 * 1024):.2f} MB)")

def main():
    log("=== Memulai Build Tatap Windows Portable ===")
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    runtime_dir = os.path.join(OUTPUT_FOLDER, "runtime")
    site_packages_dir = os.path.join(runtime_dir, "site-packages")
    target_exe = os.path.join(OUTPUT_FOLDER, "Tatap.exe")
    output_zip = os.path.join(DIST_DIR, "tatap-windows-x64-portable.zip")

    # 1. Setup embedded python runtime
    setup_runtime(runtime_dir)

    # 2. Download dan pasang dependensi Windows
    install_windows_dependencies(site_packages_dir)

    # 3. Compile Tatap.exe
    build_launcher(target_exe)

    # 4. Copy project files
    copy_project_files(OUTPUT_FOLDER)

    # 5. Pack zip
    create_portable_zip(OUTPUT_FOLDER, output_zip)

    log("=== Build Selesai dengan Sukses! ===")
    print(f"""
Lokasi File Output:
1. Folder Portable: {OUTPUT_FOLDER}
2. File Executable: {target_exe}
3. File Zip Rilis : {output_zip}
""")

if __name__ == "__main__":
    main()
