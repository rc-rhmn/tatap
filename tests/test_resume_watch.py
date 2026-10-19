"""Test suite untuk verifikasi fitur Resume Watch position and modal."""
import os
import sys
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.database import init_db, save_progress, get_progress, clear_progress, get_history, add_history
from backend.main import app, _format_time_sec


def test_format_time_sec():
    """Format waktu detik ke string MM:SS atau H:MM:SS."""
    assert _format_time_sec(0) == "00:00"
    assert _format_time_sec(9) == "00:09"
    assert _format_time_sec(59) == "00:59"
    assert _format_time_sec(60) == "01:00"
    assert _format_time_sec(125) == "02:05"
    assert _format_time_sec(3599) == "59:59"
    assert _format_time_sec(3600) == "1:00:00"
    assert _format_time_sec(3665) == "1:01:05"
    assert _format_time_sec(-10) == "00:00"


@pytest.mark.asyncio
async def test_database_save_and_get_progress():
    """Database watch_progress harus menyimpan dan mengembalikan progress per episode."""
    await init_db()
    slug = "test-resume-anime"
    ep = 3
    progress = 540  # 9 menit
    duration = 1440  # 24 menit

    await save_progress(slug, ep, progress, duration)
    row = await get_progress(slug, ep)
    assert row is not None
    assert row["progress"] == progress
    assert row["duration"] == duration

    # Cek bahwa episode lain dari anime yang sama tidak terpengaruh
    row_ep1 = await get_progress(slug, 1)
    assert row_ep1 is None

    # Update progress episode 3
    await save_progress(slug, ep, 600, duration)
    row_updated = await get_progress(slug, ep)
    assert row_updated is not None
    assert row_updated["progress"] == 600


@pytest.mark.asyncio
async def test_database_clear_progress():
    """Database clear_progress dapat menghapus episode tertentu atau seluruh anime."""
    await init_db()
    slug = "test-resume-clear-anime"
    await save_progress(slug, 1, 120, 1400)
    await save_progress(slug, 2, 240, 1400)

    # Hapus episode 1 saja
    await clear_progress(slug, 1)
    assert await get_progress(slug, 1) is None
    assert await get_progress(slug, 2) is not None

    # Hapus semua episode untuk slug
    await clear_progress(slug)
    assert await get_progress(slug, 2) is None


@pytest.mark.asyncio
async def test_save_progress_syncs_with_watch_history():
    """save_progress harus menyinkronkan kolom progress pada watch_history jika anime & episode cocok."""
    await init_db()
    slug = "test-resume-history-sync"
    ep = 5
    await add_history(slug, "Test Anime History", ep, "sub", progress=0)
    
    # Save progress di episode 5
    await save_progress(slug, ep, 320, 1400)
    
    history = await get_history(limit=10)
    matched = [h for h in history if h.get("slug") == slug and h.get("episode") == ep]
    assert len(matched) > 0
    assert matched[0].get("progress") == 320


def test_api_progress_endpoints():
    """Endpoint REST API /api/progress untuk GET, POST, dan DELETE."""
    client = TestClient(app)
    slug = "test-api-progress-anime"
    ep = 2

    # Awalnya belum ada progress
    resp = client.get(f"/api/progress?slug={slug}&ep={ep}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["progress"] == 0
    assert data["should_resume"] is False
    assert data["formatted"] == "00:00"

    # POST simpan progress 75 detik dari durasi 1200 detik
    post_resp = client.post("/api/progress", json={
        "slug": slug,
        "episode": ep,
        "progress": 75,
        "duration": 1200
    })
    assert post_resp.status_code == 200
    assert post_resp.json()["success"] is True

    # GET kembali harus mengembalikan should_resume = True (>= 15 detik)
    resp2 = client.get(f"/api/progress?slug={slug}&ep={ep}")
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    assert data2["progress"] == 75
    assert data2["duration"] == 1200
    assert data2["formatted"] == "01:15"
    assert data2["should_resume"] is True

    # Jika posisi hampir selesai (misal 1180 dari 1200), should_resume = False
    client.post("/api/progress", json={
        "slug": slug,
        "episode": ep,
        "progress": 1180,
        "duration": 1200
    })
    resp_near_end = client.get(f"/api/progress?slug={slug}&ep={ep}")
    assert resp_near_end.json()["data"]["should_resume"] is False

    # DELETE progress episode
    del_resp = client.delete(f"/api/progress?slug={slug}&ep={ep}")
    assert del_resp.status_code == 200
    resp_after_del = client.get(f"/api/progress?slug={slug}&ep={ep}")
    assert resp_after_del.json()["data"]["progress"] == 0


def test_chaquopy_code_parity():
    """Pastikan backend database dan main.py 100% identik dengan versi Chaquopy di android."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Database __init__.py parity
    db_root = os.path.join(base_dir, "backend", "database", "__init__.py")
    db_android = os.path.join(base_dir, "android", "app", "src", "main", "python", "backend", "database", "__init__.py")
    with open(db_root, "r", encoding="utf-8") as f1, open(db_android, "r", encoding="utf-8") as f2:
        assert f1.read() == f2.read(), "backend/database/__init__.py and Chaquopy copy must be 100% identical"

    # 2. Main.py parity
    main_root = os.path.join(base_dir, "backend", "main.py")
    main_android = os.path.join(base_dir, "android", "app", "src", "main", "python", "backend", "main.py")
    with open(main_root, "r", encoding="utf-8") as f1, open(main_android, "r", encoding="utf-8") as f2:
        assert f1.read() == f2.read(), "backend/main.py and Chaquopy copy must be 100% identical"


def test_interactive_resume_modal_frontend():
    """Memverifikasi berkas frontend memuat elemen interaktif, visual progress bar, dan keyboard handler resume modal."""
    import subprocess
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. index.html checks
    index_html_path = os.path.join(base_dir, "frontend", "index.html")
    with open(index_html_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert 'id="resume-modal"' in html, "index.html harus memuat dialog #resume-modal"
    assert 'id="rm-progress-wrap"' in html, "index.html harus memuat #rm-progress-wrap"
    assert 'id="rm-progress-fill"' in html, "index.html harus memuat #rm-progress-fill"
    assert 'id="rm-percent-badge"' in html, "index.html harus memuat #rm-percent-badge"
    assert 'id="rm-btn-resume"' in html, "index.html harus memuat tombol Lanjutkan"
    assert 'id="rm-btn-restart"' in html, "index.html harus memuat tombol Mulai dari Awal"
    assert 'id="rm-btn-cancel"' in html, "index.html harus memuat tombol Batal"
    assert 'id="rm-close"' in html, "index.html harus memuat tombol close Batal (Esc)"

    # 2. style.css checks
    style_css_path = os.path.join(base_dir, "frontend", "css", "style.css")
    with open(style_css_path, "r", encoding="utf-8") as f:
        css = f.read()
    assert "#resume-modal.overlay" in css, "style.css harus mendefinisikan #resume-modal.overlay"
    assert "z-index:160" in css or "z-index: 160" in css, "#resume-modal harus memiliki z-index 160"
    assert ".rm-progress-track" in css, "style.css harus memuat .rm-progress-track"
    assert ".rm-progress-fill" in css, "style.css harus memuat .rm-progress-fill"
    assert ".btn-resume-primary:focus-visible" in css, "style.css harus memiliki indikator :focus-visible pada tombol resume"
    assert ".btn-resume-cancel" in css, "style.css harus memuat .btn-resume-cancel"

    # 3. app.js checks
    app_js_path = os.path.join(base_dir, "frontend", "js", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()
    assert "dismissResumeModal" in app_js, "app.js harus mendefinisikan dismissResumeModal"
    assert "title-modal" in app_js, "app.js dismissResumeModal harus mengembalikan ke title-modal"
    assert "rm-progress-fill" in app_js, "app.js harus memperbarui lebar rm-progress-fill"
    assert "ArrowLeft" in app_js and "ArrowRight" in app_js, "app.js harus menangani navigasi panah kiri/kanan"

    # 4. term.js checks
    term_js_path = os.path.join(base_dir, "frontend", "js", "term.js")
    with open(term_js_path, "r", encoding="utf-8") as f:
        term_js = f.read()
    assert 'resume-modal' in term_js, "term.js isModalOpen harus memeriksa resume-modal"

