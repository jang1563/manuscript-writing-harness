from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_figure_review import analyze_font_resolution, analyze_png


def test_analyze_font_resolution_detects_preferred_and_fallback() -> None:
    font_policy = {
        "families": {
            "sans_preferred": ["DejaVu Sans", "Liberation Sans"],
            "sans_fallbacks": ["Arial", "Helvetica", "Nimbus Sans"],
        }
    }

    preferred = analyze_font_resolution(
        {
            "font_resolution": {
                "family": "DejaVu Sans",
                "path": "/tmp/DejaVuSans.ttf",
            }
        },
        font_policy,
    )
    fallback = analyze_font_resolution(
        {
            "font_resolution": {
                "family": "DejaVu Sans",
                "path": "/System/Library/Fonts/Helvetica.ttc",
            }
        },
        font_policy,
    )

    assert preferred["status"] == "preferred"
    assert fallback["status"] == "fallback"


def test_analyze_png_flags_hotspot_when_ink_touches_edge(tmp_path: Path) -> None:
    image_path = tmp_path / "edge_case.png"
    image = Image.new("RGBA", (200, 120), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 15, 25, 105), fill=(0, 0, 0, 255))
    image.save(image_path)

    analysis = analyze_png(image_path)

    assert analysis["hotspot_edge"] == "left"
    assert analysis["clipping_risk"] in {"moderate", "high"}
    assert analysis["edge_gaps_px"]["left"] == 0
