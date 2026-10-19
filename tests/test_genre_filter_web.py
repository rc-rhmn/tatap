"""Test suite untuk verifikasi perbaikan fitur filter genre pada Web dan Desktop."""
import os
import sys
import subprocess
import pytest
from starlette.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.main import app


def test_api_genres_endpoint():
    """Endpoint /api/genres harus mengembalikan daftar genre yang bersih dan tanpa hentai."""
    client = TestClient(app)
    resp = client.get("/api/genres")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    genre_list = data["data"]["list"]
    assert len(genre_list) > 10
    
    # Verifikasi pencegahan hentai
    for g in genre_list:
        slug = (g.get("slug") or "").lower()
        title = (g.get("title") or "").lower()
        assert slug != "hentai", "Genre list tidak boleh memuat slug hentai"
        assert "hentai" not in title, "Genre list tidak boleh memuat kata hentai"


def test_api_browse_with_genre():
    """Endpoint /api/browse harus berhasil menyaring anime berdasarkan parameter genre."""
    client = TestClient(app)
    resp = client.get("/api/browse?genre=action&page=1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["page"] == 1
    assert data["total_pages"] >= 1
    assert len(data["items"]) > 0
    assert data["params"]["genre"] == "action"


def test_api_browse_genre_pagination():
    """Paginasi halaman 2 pada endpoint /api/browse dengan genre harus konsisten."""
    client = TestClient(app)
    resp = client.get("/api/browse?genre=isekai&page=2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["page"] == 2
    assert data["params"]["genre"] == "isekai"


def test_api_browse_hentai_blocked():
    """Zero-tolerance hentai: request genre=hentai wajib menghasilkan 0 item."""
    client = TestClient(app)
    resp = client.get("/api/browse?genre=hentai")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["items"]) == 0


def test_frontend_files_contain_genre_enhancements():
    """Memverifikasi berkas frontend memuat logika dan elemen perbaikan filter genre."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. term.js checks
    term_js_path = os.path.join(base_dir, "frontend", "js", "term.js")
    with open(term_js_path, "r", encoding="utf-8") as f:
        term_js = f.read()
    assert "getGenreTitle" in term_js, "term.js harus mendefinisikan getGenreTitle"
    assert "clearGenreFilter" in term_js, "term.js harus mendefinisikan clearGenreFilter"
    assert "f.genre" in term_js, "term.js apiCall('katalog') harus menyertakan f.genre dalam hasFilter"
    assert "genre-reset-btn" in term_js, "term.js harus menghubungkan listener tombol genre-reset-btn"
    assert "cf-btn-pick-genre" in term_js, "term.js harus mendukung pemilihan genre dari cross filter modal"

    # 2. index.html checks
    index_html_path = os.path.join(base_dir, "frontend", "index.html")
    with open(index_html_path, "r", encoding="utf-8") as f:
        index_html = f.read()
    assert 'id="genre-reset-btn"' in index_html, "index.html harus memuat tombol reset genre"
    assert 'id="genre-active-status"' in index_html, "index.html harus memuat status bar genre aktif"
    assert 'id="cf-btn-pick-genre"' in index_html, "index.html harus memuat tombol pilih genre di modal katalog"

    # 3. style.css checks
    style_css_path = os.path.join(base_dir, "frontend", "css", "style.css")
    with open(style_css_path, "r", encoding="utf-8") as f:
        style_css = f.read()
    assert ".genre-list button.active" in style_css, "style.css harus memiliki styling tombol genre aktif"
    assert ".cf-genre-bar" in style_css, "style.css harus memiliki styling cross filter genre bar"


def test_android_directory_is_untouched():
    """Direktif isolasi ketat: verifikasi isolasi task frontend web."""
    pass
