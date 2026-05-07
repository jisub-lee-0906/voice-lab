import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app


def test_custom_css_uses_readable_light_theme_without_dark_hero():
    css = app.CUSTOM_CSS
    assert "linear-gradient" not in css
    assert "background: #111827" not in css
    assert "#0f172a" not in css
    assert "#ffffff" in css
    assert "color: #111827" in css


def test_custom_css_does_not_force_tiny_or_colored_body_text():
    css = app.CUSTOM_CSS
    assert "font-size: 30px" not in css
    assert "color: #dbeafe" not in css
