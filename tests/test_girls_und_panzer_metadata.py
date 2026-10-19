"""Tests for Girls & Panzer / Girls und Panzer metadata, search, relations, and subtitle stream resolution.
Ensures zero-regression and accurate cross-platform synchronization between AniList, HiAnime, and Otakudesu.
"""

import asyncio
import os
import re
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

import api.hianime as hi
import api.otakudesu as ot
from main import (
    _clean_title_tokens,
    _extract_season_num,
    _is_title_match,
    _match_slug_one,
    anime_relations_endpoint,
)


def test_hianime_search_girls_und_panzer_and_quote_encoding():
    """Ensure search queries for Girls & Panzer (and its aliases with & or und) return the TV series #1."""
    queries = [
        "girls & panzer",
        "girls und panzer",
        "girls and panzer",
        "garupan",
    ]
    for q in queries:
        results = hi.hianime_search(q, limit=5)
        assert results, f"Query '{q}' returned no results"
        top = results[0]
        assert top["id"] == "girls-und-panzer-2670", (
            f"Expected top result for '{q}' to be 'girls-und-panzer-2670', got '{top['id']}'"
        )
        assert "Girls" in top["title"] and "Panzer" in top["title"]


def test_is_title_match_distinguishes_tv_movie_and_specials():
    """Ensure TV series, Movie/Film, and OVA/Specials never falsely match with each other."""
    # TV Series matching
    assert _is_title_match("Girls und Panzer", "Girls & Panzer") is True
    assert _is_title_match("Girls und Panzer", "Girls and Panzer") is True

    # TV vs Movie isolation
    assert _is_title_match("Girls und Panzer", "Girls und Panzer der Film") is False
    assert _is_title_match("Girls und Panzer der Film", "Girls und Panzer") is False
    assert _is_title_match("Girls und Panzer der Film", "Girls und Panzer der Film") is True

    # TV vs OVA isolation
    assert _is_title_match("Girls und Panzer", "Girls & Panzer OVAs") is False
    assert _is_title_match("Girls und Panzer OVA Series", "Girls & Panzer OVAs") is True
    assert _is_title_match("Girls und Panzer Specials", "Girls & Panzer OVAs") is True

    # Subtitle tags / distinct franchise entries
    assert _is_title_match("Girls und Panzer: This is the Real Anzio Battle!", "Girls & Panzer") is False
    assert _is_title_match(
        "Girls und Panzer: This is the Real Anzio Battle!",
        "Girls & Panzer: This is the Real Anzio Battle!"
    ) is True
    assert _is_title_match("Girls und Panzer der Film: Alice War!", "Girls und Panzer der Film") is False


def test_season_and_part_number_extraction():
    """Verify season, part, saishuushou, and finale numbers are accurately extracted."""
    assert _extract_season_num("Girls und Panzer") == 1
    assert _extract_season_num("Girls und Panzer Season 2") == 2
    assert _extract_season_num("Girls und Panzer das Finale - Part 1") == 1
    assert _extract_season_num("Girls und Panzer das Finale - Part 2") == 2
    assert _extract_season_num("Girls und Panzer: Saishuushou 2") == 2
    assert _extract_season_num("Girls und Panzer: Saishuushou Part 3") == 3
    assert _extract_season_num("Girls und Panzer das Finale - Part 4") == 4


@pytest.mark.asyncio
async def test_slug_match_girls_und_panzer_franchise():
    """Verify _match_slug_one maps each Girls und Panzer franchise title to its correct distinct slug."""
    loop = asyncio.get_running_loop()

    # 1. Main TV Series
    s_tv = await _match_slug_one(loop, "Girls und Panzer")
    assert s_tv == "girls-und-panzer-2670"

    # 2. Movie 2015
    s_film = await _match_slug_one(loop, "Girls und Panzer der Film")
    assert s_film == "girls-und-panzer-der-film-1161"

    # 3. OVA Series
    s_ova = await _match_slug_one(loop, "Girls und Panzer OVA Series", "Girls und Panzer Specials")
    assert s_ova == "girls-und-panzer-ova-6325"

    # 4. Anzio Battle OVA
    s_anzio = await _match_slug_one(loop, "Girls und Panzer: This is the Real Anzio Battle!")
    assert s_anzio == "girls-und-panzer-this-is-the-real-anzio-battle-2671"

    # 5. Finale Part 2 must NOT match Part 1
    s_part2 = await _match_slug_one(loop, "Girls und Panzer das Finale - Part 2", "Girls und Panzer: Saishuushou 2")
    assert s_part2 == "girls-und-panzer-das-finale-part-2-2601"


@pytest.mark.asyncio
async def test_anime_relations_endpoint_format_and_distinct_slugs():
    """Verify relations endpoint returns formatted labels (Movie, Special, OVA, Season 1) with valid distinct slugs."""
    # TV Series relations
    res_tv = await anime_relations_endpoint("girls-und-panzer-2670", "Girls & Panzer")
    assert res_tv.get("success") is True
    relations = res_tv.get("data", {}).get("relations", [])
    assert len(relations) >= 2

    # Check that der Film is labeled Movie
    movie_rel = next((r for r in relations if "der Film" in r["title"]), None)
    assert movie_rel is not None
    assert movie_rel["format"] == "MOVIE"
    assert movie_rel["label"] == "Movie"
    assert movie_rel["slug"] == "girls-und-panzer-der-film-1161"

    # Check relations for der Film (Movie) points back to TV series Season 1
    res_film = await anime_relations_endpoint("girls-und-panzer-der-film-1161", "Girls und Panzer der Film")
    assert res_film.get("success") is True
    film_relations = res_film.get("data", {}).get("relations", [])
    tv_rel = next((r for r in film_relations if r["title"] == "Girls und Panzer"), None)
    assert tv_rel is not None
    assert tv_rel["slug"] == "girls-und-panzer-2670"
    assert tv_rel["label"] == "Season 1"
    # Ensure der Film does not point to itself
    assert tv_rel["slug"] != "girls-und-panzer-der-film-1161"


def test_otakudesu_girls_panzer_search_and_matching():
    """Verify Otakudesu searches normalize German 'und' and matches the 12-episode TV series correctly."""
    # Search with 'und' should automatically find Otakudesu 'Girls Panzer'
    results = ot.search("girls und panzer")
    assert results, "Expected otakudesu search for 'girls und panzer' to return entries"
    tv_cand = next((r for r in results if r["id"] == "girls-panzer-v979ece"), None)
    assert tv_cand is not None
    assert "Girls Panzer" in tv_cand["title"]

    # Title matching precision
    assert ot._is_title_match("girls und panzer", "Girls Panzer") is True
    # Saishuushou Part 1/3 must NOT match the base TV series
    assert ot._is_title_match("girls und panzer", "Girls & Panzer: Saishuushou Part 1") is False
    assert ot._is_title_match("girls und panzer", "Girls & Panzer: Saishuushou Part 3") is False
