"""Test suite untuk verifikasi manajemen proses Linux, signal traps, dan isolasi multi-user."""
import os
import subprocess
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPRUN_PATH = os.path.join(REPO_ROOT, "linux", "AppRun")
MANAGE_PATH = os.path.join(REPO_ROOT, "manage.sh")
RUN_PATH = os.path.join(REPO_ROOT, "run.sh")


def test_apprun_signal_trap_and_cleanup_logic():
    """Memastikan AppRun Linux memasang trap cleanup untuk sinyal EXIT, INT, TERM, dan HUP serta graceful shutdown."""
    with open(APPRUN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert "trap cleanup EXIT INT TERM HUP" in content, "Trap wajib menyertakan sinyal HUP untuk terminal hangup"
    assert 'kill -TERM "$SERVER_PID"' in content, "Cleanup wajib mengirim sinyal TERM terlebih dahulu"
    assert 'kill -KILL "$SERVER_PID"' in content, "Cleanup wajib memiliki fallback KILL jika proses backend menggantung"
    assert "sleep 0.1" in content, "Cleanup wajib memiliki loop tunggu hingga 2 detik sebelum memaksa kill"


def test_apprun_browser_isolation_and_wait():
    """Memastikan AppRun mengisolasi profile browser dan mengaitkan lifecycle ke BROWSER_PID."""
    with open(APPRUN_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert '--user-data-dir="$CHROME_DATA_DIR"' in content, "Browser wajib menggunakan user-data-dir terisolasi"
    assert "--class=Tatap" in content, "Browser window wajib menyetel class Tatap"
    assert "--ozone-platform-hint=auto" in content, "Wayland integration flag wajib ada"
    assert 'wait "$BROWSER_PID"' in content, "AppRun wajib me-wait BROWSER_PID jendela aplikasi"
    # Memastikan tidak ada lagi indefinite hang pada fail-safe usang
    assert 'wait "$SERVER_PID"' not in content.split('if [ -n "$BROWSER_CMD" ]; then')[1].split('else')[0], \
        "Branch browser Chromium tidak boleh menggantung di wait SERVER_PID"


def test_manage_sh_multi_user_log_path():
    """Memastikan manage.sh tidak meng-hardcode /tmp/tatap.log dan menggunakan direktori aman per-user."""
    with open(MANAGE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'LOG="/tmp/tatap.log"' not in content, "manage.sh dilarang meng-hardcode /tmp/tatap.log"
    assert "XDG_STATE_HOME" in content, "manage.sh wajib memprioritaskan XDG_STATE_HOME per-user"
    assert "LOG=" in content


def test_manage_sh_safe_process_verification():
    """Memastikan manage.sh memverifikasi kepemilikan proses (UID & args) sebelum mengirimkan kill."""
    with open(MANAGE_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'ps -u "$UID"' in content or 'ps -p "$pid"' in content, "manage.sh wajib memeriksa detail proses ps"
    assert "python.*backend/main" in content, "manage.sh wajib memvalidasi argumen proses Tatap"
    assert 'pkill -u "$UID"' in content, "pkill wajib dibatasi hanya pada proses milik user aktif (-u $UID)"


def test_scripts_syntax_validation():
    """Validasi sintaksis bash murni untuk seluruh skrip Linux."""
    for script_path in [APPRUN_PATH, MANAGE_PATH, RUN_PATH]:
        res = subprocess.run(["bash", "-n", script_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Sintaksis {os.path.basename(script_path)} gagal: {res.stderr}"
