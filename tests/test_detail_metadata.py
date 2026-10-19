"""
Unit tests untuk verifikasi linked genre buttons dan akurasi status anime tamat vs sedang tayang.
"""
import pytest
from backend.api.hianime import _parse_browse_cards


def test_parse_browse_cards_finished_vs_ongoing():
    # Simulasi HTML kartu anime tamat (12/12)
    html_finished = '''
    <div class="flw-item">
        <div class="film-name"><a href="/watch/frieren-18888" title="Sousou no Frieren">Sousou no Frieren</a></div>
        <div class="tick-sub">12</div>
        <div class="tick-eps">12</div>
        <div class="fdi-item">TV</div>
        <div class="fdi-duration">24m</div>
        <div class="description">Petualangan Frieren setelah mengalahkan raja iblis.</div>
        <div class="clearfix"></div>
    </div>
    '''
    items_fin = _parse_browse_cards(html_finished)
    assert len(items_fin) == 1
    assert items_fin[0]["eps_counter"] == "12/12"
    assert items_fin[0]["is_finished"] is True
    assert items_fin[0]["status"] == "finished"
    assert items_fin[0]["badge"] == "TAMAT"

    # Simulasi HTML kartu anime ongoing (8/12)
    html_ongoing = '''
    <div class="flw-item">
        <div class="film-name"><a href="/watch/re-zero-3-19999" title="Re:Zero Season 3">Re:Zero Season 3</a></div>
        <div class="tick-sub">8</div>
        <div class="tick-eps">12</div>
        <div class="fdi-item">TV</div>
        <div class="fdi-duration">24m</div>
        <div class="description">Subaru melanjutkan perjuangan.</div>
        <div class="clearfix"></div>
    </div>
    '''
    items_on = _parse_browse_cards(html_ongoing)
    assert len(items_on) == 1
    assert items_on[0]["eps_counter"] == "8/12"
    assert items_on[0]["is_finished"] is False
    assert items_on[0]["status"] == "releasing"
    assert items_on[0]["badge"] == "ONGOING"


def test_detail_activity_status_and_linked_genre():
    with open("android/app/src/main/java/id/tatap/app/DetailActivity.java", "r", encoding="utf-8") as f:
        src = f.read()

    # Verifikasi keberadaan teks tamat & ongoing
    assert "Episode (Tamat)" in src
    assert "Episode Rilis (Sedang Tayang)" in src

    # Verifikasi linked genre intent ke MainActivity
    assert "Intent(DetailActivity.this, MainActivity.class)" in src
    assert 'intent.putExtra("genre", genreName);' in src
    assert "FLAG_ACTIVITY_CLEAR_TOP" in src
    assert "TvFocusHelper.attachFocusScale(chip, 1.08f, 4f);" in src


def test_main_activity_incoming_genre_intent():
    with open("android/app/src/main/java/id/tatap/app/MainActivity.java", "r", encoding="utf-8") as f:
        src = f.read()

    assert "protected void onNewIntent(Intent intent)" in src
    assert "handleIncomingIntent(getIntent());" in src
    assert 'intent.hasExtra("genre")' in src
    assert "setGenreFilter(targetGenre.trim());" in src


def test_anime_adapter_finished_inference():
    with open("android/app/src/main/java/id/tatap/app/AnimeAdapter.java", "r", encoding="utf-8") as f:
        src = f.read()

    assert "cur >= tot" in src
    assert "final String status =" in src
    assert '"finished"' in src


def test_web_desktop_linked_genre_and_status():
    with open("frontend/js/term.js", "r", encoding="utf-8") as f:
        term_src = f.read()
    assert "applyGenreFilter:" in term_src
    assert "slugifyGenre:" in term_src

    with open("frontend/js/app.js", "r", encoding="utf-8") as f:
        app_src = f.read()
    assert 'genre-pill interactive' in app_src
    assert "window.Tui.applyGenreFilter(g)" in app_src
    assert "closeTitle()" in app_src

    with open("frontend/css/style.css", "r", encoding="utf-8") as f:
        css_src = f.read()
    assert ".genre-pill.interactive" in css_src
