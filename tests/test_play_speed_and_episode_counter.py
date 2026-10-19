import os
import re
import pytest
from backend.api import anilist as al
from backend.api import hianime as ha

def test_anilist_compute_episode_counts():
    # Ongoing with next airing episode (e.g. ep 9 airs next, so 8 are released out of 12)
    m1 = {
        "status": "RELEASING",
        "episodes": 12,
        "nextAiringEpisode": {"episode": 9}
    }
    rel1, tot1 = al.compute_episode_counts(m1)
    assert rel1 == 8
    assert tot1 == 12

    # Finished anime
    m2 = {
        "status": "FINISHED",
        "episodes": 24,
        "nextAiringEpisode": None
    }
    rel2, tot2 = al.compute_episode_counts(m2)
    assert rel2 == 24
    assert tot2 == 24

    # Ongoing without announced total episodes
    m3 = {
        "status": "RELEASING",
        "episodes": None,
        "nextAiringEpisode": {"episode": 5}
    }
    rel3, tot3 = al.compute_episode_counts(m3)
    assert rel3 == 4
    assert tot3 == 0

    # No info
    m4 = {
        "status": "NOT_YET_RELEASED",
        "episodes": 0,
        "nextAiringEpisode": None
    }
    rel4, tot4 = al.compute_episode_counts(m4)
    assert rel4 == 0
    assert tot4 == 0

def test_hianime_parse_browse_cards_counter():
    mock_html = """
    <div class="flw-item">
        <a href="/watch/sousou-no-frieren-18456" class="film-poster-ahref">
            <img src="https://img.hianime.to/poster.jpg" alt="Sousou no Frieren"/>
        </a>
        <div class="film-detail">
            <h3 class="film-name"><a href="/watch/sousou-no-frieren-18456" title="Sousou no Frieren">Sousou no Frieren</a></h3>
            <div class="fd-infor">
                <span class="fdi-item">TV</span>
                <span class="fdi-duration">24m</span>
            </div>
            <div class="tick-item tick-sub">18</div>
            <div class="tick-item tick-dub">12</div>
            <div class="tick-item tick-eps">28</div>
            <div class="description">Frieren the mage...</div>
        </div>
    </div>
    """
    cards = ha._parse_browse_cards(mock_html)
    assert len(cards) == 1
    card = cards[0]
    assert card["id"] == "sousou-no-frieren-18456"
    assert card["sub"] == 18
    assert card["dub"] == 12
    assert card["eps"] == 28
    assert card["eps_released"] == 18
    assert card["eps_total"] == 28
    assert card["eps_counter"] == "18/28"

def test_chaquopy_backend_parity():
    pairs = [
        ("backend/api/anilist.py", "android/app/src/main/python/backend/api/anilist.py"),
        ("backend/api/hianime.py", "android/app/src/main/python/backend/api/hianime.py"),
        ("backend/main.py", "android/app/src/main/python/backend/main.py"),
    ]
    for b_path, a_path in pairs:
        with open(b_path, "r", encoding="utf-8") as fb:
            b_content = fb.read()
        with open(a_path, "r", encoding="utf-8") as fa:
            a_content = fa.read()
        assert b_content == a_content, f"Parity mismatch between {b_path} and {a_path}"

def test_frontend_playback_speed_and_counter_integration():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert 'id="pm-speed-select"' in html
    for spd in ["0.5", "0.75", "1", "1.25", "1.5", "1.75", "2"]:
        assert f'value="{spd}"' in html

    with open("frontend/js/app.js", "r", encoding="utf-8") as f:
        app_js = f.read()
    assert "PLAYBACK_SPEEDS" in app_js
    assert "currentPlaybackSpeed" in app_js
    assert "setPlaySpeed" in app_js
    assert "adjustPlaySpeed" in app_js
    # Ensure reset to 1.0x on openTitle
    assert "setPlaySpeed(1.0, false);" in app_js
    # Ensure keyboard shortcuts [ and ]
    assert 'e.key==="["' in app_js
    assert 'e.key==="]"' in app_js

    with open("frontend/js/term.js", "r", encoding="utf-8") as f:
        term_js = f.read()
    assert "eps_counter" in term_js

def test_android_player_speed_and_counter_integration():
    with open("android/app/src/main/res/layout/activity_player.xml", "r", encoding="utf-8") as f:
        layout_xml = f.read()
    assert 'android:id="@+id/btn_speed"' in layout_xml
    assert 'android:nextFocusLeft="@+id/btn_quality"' in layout_xml
    assert 'android:nextFocusRight="@+id/btn_sub_style"' in layout_xml

    with open("android/app/src/main/java/id/tatap/app/PlayerActivity.java", "r", encoding="utf-8") as f:
        player_java = f.read()
    assert "btnSpeed" in player_java
    assert "currentPlaybackSpeed = 1.0f;" in player_java
    assert "showSpeedSelectorDialog" in player_java
    assert "PlaybackParameters" in player_java

    with open("android/app/src/main/java/id/tatap/app/AnimeAdapter.java", "r", encoding="utf-8") as f:
        adapter_java = f.read()
    assert "eps_counter" in adapter_java
    assert 'intent.putExtra("eps_counter", epsCounter);' in adapter_java

    with open("android/app/src/main/java/id/tatap/app/DetailActivity.java", "r", encoding="utf-8") as f:
        detail_java = f.read()
    assert "epsCounter" in detail_java
    assert "Episode Rilis (Sedang Tayang)" in detail_java
