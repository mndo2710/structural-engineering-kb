"""Application rendering helpers for offline Panel 3 math and Qt-independent DiagramSpec."""

from app.rendering.diagram_builders import build_diagram_spec
from app.rendering.math_renderer import (
    KATEX_SPIKE_REPORT,
    STAGE_TITLES,
    has_webengine_support,
    render_calculation_sheet_html,
    safe_markup_to_html,
)

__all__ = [
    "KATEX_SPIKE_REPORT",
    "STAGE_TITLES",
    "build_diagram_spec",
    "has_webengine_support",
    "render_calculation_sheet_html",
    "safe_markup_to_html",
]
