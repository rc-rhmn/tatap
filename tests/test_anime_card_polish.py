"""Tests for Anime Card visual polish and low-end device optimization."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE_CSS = ROOT / "frontend" / "css" / "style.css"
TERM_JS = ROOT / "frontend" / "js" / "term.js"


def test_anime_card_media_container_and_aspect_ratio():
    """Verify pc-media container uses 2/3 anime key-visual aspect ratio."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    js = TERM_JS.read_text(encoding="utf-8")

    assert ".pc-media" in css
    assert "aspect-ratio:2/3" in css or "aspect-ratio: 2/3" in css
    assert 'media.className="pc-media"' in js or 'media.className = "pc-media"' in js


def test_anime_card_pseudo_element_scrim():
    """Verify poster scrim is implemented via pseudo-element (zero extra DOM nodes)."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert ".pc-media::after" in css
    assert "linear-gradient(to top" in css


def test_anime_card_semantic_badges():
    """Verify semantic badge classes exist in CSS and are generated in JS."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    js = TERM_JS.read_text(encoding="utf-8")

    assert ".pc-score" in css
    assert ".pc-badge-tag" in css
    assert ".pc-badge-ep" in css
    assert ".pc-badge-tamat" in css
    assert ".pc-badge-long" in css
    assert ".pc-badge-type" in css

    assert "pc-score" in js
    assert "pc-badge-ep" in js
    assert "pc-badge-tamat" in js
    assert "pc-badge-long" in js
    assert "pc-badge-type" in js


def test_anime_card_low_end_performance_guarantees():
    """Verify zero backdrop-filter and strict containment for low-end device smoothness."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    # Verify containment
    assert "contain:content" in css or "contain: content" in css
    assert "will-change:transform" in css or "will-change: transform" in css

    # Isolate poster card section
    start_idx = css.find(".poster-card{")
    end_idx = css.find(".poster-body b{")
    assert start_idx != -1 and end_idx != -1
    card_css_slice = css[start_idx:end_idx]

    # Verify NO backdrop-filter is used on card or badges
    assert "backdrop-filter" not in card_css_slice
