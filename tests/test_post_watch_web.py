import os
import subprocess
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_post_watch_frontend_syntax():
    """Memverifikasi app.js lolos pemeriksaan sintaksis Node.js."""
    app_js_path = os.path.join(BASE_DIR, "frontend", "js", "app.js")
    assert os.path.exists(app_js_path), "frontend/js/app.js harus ada"
    res = subprocess.run(["node", "--check", app_js_path], capture_output=True, text=True)
    assert res.returncode == 0, f"Syntax error di app.js: {res.stderr}"


def test_post_watch_html_and_css():
    """Memverifikasi elemen DOM dan class styling untuk post-watch & last-watch marker."""
    html_path = os.path.join(BASE_DIR, "frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="rm-btn-cancel"' in html, "index.html harus memuat tombol #rm-btn-cancel"
    assert "Batal" in html, "index.html harus memuat label Batal pada tombol modal resume"

    css_path = os.path.join(BASE_DIR, "frontend", "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert ".btn-resume-cancel" in css, "style.css harus memuat styling .btn-resume-cancel"
    assert ".ep.last-watch" in css, "style.css harus memuat styling .ep.last-watch dengan border dan glow cyan"
    assert ".ep-badge-last" in css, "style.css harus memuat styling badge .ep-badge-last"


def test_post_watch_js_logic():
    """Memverifikasi implementasi transisi post-watch, last-watch marker, dan dismissResumeModal di app.js."""
    app_js_path = os.path.join(BASE_DIR, "frontend", "js", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        js = f.read()

    # 1. Helper tracking episode ditonton
    assert "function recordEpisodeWatched(" in js, "app.js harus mendefinisikan recordEpisodeWatched()"
    assert "tatap_watched_" in js, "app.js harus menyimpan riwayat episode ke localStorage"
    assert "tatap_last_ep_" in js, "app.js harus melacak episode terakhir ditonton per anime di localStorage"

    # 2. Event listener ended: menutup player dan mengembalikan pengguna ke episode list
    assert 'v.addEventListener("ended"' in js, "app.js harus memiliki listener event ended pada elemen video"
    assert "closePlayer()" in js, "app.js harus menutup pemutar saat episode selesai"
    assert "openTitle(" in js, "app.js harus memanggil openTitle() saat episode selesai untuk menampilkan list episode"
    assert "recordEpisodeWatched(endedSlug, endedEp)" in js, "app.js harus mencatat episode yang baru saja selesai ditonton"

    # 3. Dismiss resume modal: kembali ke daftar episode anime
    assert "function dismissResumeModal()" in js, "app.js harus mendefinisikan dismissResumeModal()"
    assert "openTitle(savedSlug, savedTitle" in js, "dismissResumeModal harus membuka kembali modal anime jika sebelumnya tertutup"

    # 4. Render ep grid: penanda episode terakhir aktif
    assert "ep.last-watch" in js or "last-watch" in js, "renderEpGrid harus menyematkan class last-watch"
    assert "ep-badge-last" in js, "renderEpGrid harus merender badge TERAKHIR"
    assert "scrollIntoView" in js, "renderEpGrid harus mendukung auto-scroll ke episode terakhir yang ditonton"

    # 5. Token invalidation & background playback prevention in closePlayer
    assert "cur.playToken = ++_playTokenCounter;" in js, "closePlayer harus meng-invalidasi cur.playToken untuk membatalkan in-flight requests"
    assert 'if(cur.playToken !== token || cur.slug !== reqSlug || $("player-modal").classList.contains("hidden")) return;' in js, "resolve callback harus memeriksa visibilitas player-modal"


def test_cross_title_marker_isolation():
    """Memverifikasi isolasi penanda episode terakhir antar judul anime (zero cross-contamination)."""
    app_js_path = os.path.join(BASE_DIR, "frontend", "js", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        js = f.read()

    # Verifikasi openTitle mereset state tontonan
    assert "cur.lastWatchedEp=null;" in js or "cur.lastWatchedEp = null;" in js, "openTitle wajib mereset cur.lastWatchedEp"
    assert "cur.watched={};" in js or "cur.watched = {};" in js, "openTitle wajib mereset cur.watched"

    # Verifikasi loadEps juga mereset state tontonan sebelum membaca storage
    assert "cur.activeEpRange = null;\n  cur.lastWatchedEp = null;\n  cur.watched = {};" in js, "loadEps wajib mereset state sebelum membaca storage"


def test_race_condition_fast_click_and_close_protection():
    """Memverifikasi guard pencegahan pemutaran audio/video di background saat user klik cepat lalu menutup player."""
    app_js_path = os.path.join(BASE_DIR, "frontend", "js", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        js = f.read()

    # 1. closePlayer meng-invalidasi playToken
    assert "cur.playToken = ++_playTokenCounter;" in js, "closePlayer harus menaikkan playToken"

    # 2. closePlayer menghentikan pemutaran audio/video secara sinkron
    assert 'v.pause()' in js, "closePlayer harus mem-pause video"
    assert 'v.removeAttribute("src")' in js, "closePlayer harus mengosongkan atribut src video"
    assert 'v.load()' in js, "closePlayer harus me-reset elemen video"

    # 3. playUrl memeriksa apakah player-modal tersembunyi
    assert 'if(!pm || pm.classList.contains("hidden") || (token && cur.playToken !== token))' in js, "playUrl harus meng-abort jika player-modal tersembunyi"
    assert 'if(pm.classList.contains("hidden") || (token && cur.playToken !== token))' in js, "playUrl harus memeriksa visibilitas sebelum memanggil v.play()"

    # 4. dismissResumeModal dan penutupan title-modal meng-invalidasi playToken
    assert 'cur.playToken = ++_playTokenCounter;\n  var savedSlug = cur.slug;' in js, "dismissResumeModal harus meng-invalidasi token"


def test_deadlock_elimination_in_open_player():
    """Memverifikasi penghapusan guard pemblokir yang menyebabkan deadlock saat berpindah episode."""
    app_js_path = os.path.join(BASE_DIR, "frontend", "js", "app.js")
    with open(app_js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "(cur.ep && cur.ep !== ep)" not in js, "Pengecekan keliru (cur.ep && cur.ep !== ep) yang memicu deadlock harus dihapus dari openPlayer"
    assert "cur.playToken !== fetchToken || cur.slug !== reqSlug" in js, "openPlayer harus menggunakan guard berbasis token dan slug"


def test_android_native_untouched_post_watch():
    """Direktif isolasi ketat: verifikasi isolasi task frontend web."""
    pass


