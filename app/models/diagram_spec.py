"""Qt-independent DiagramSpec models for Panel 2 and report exporters (WP-8).

Pure-Python data contracts containing zero PySide6 imports and zero engineering equations.
Geometry shapes and dimensions reflect draft inputs immediately, while force vectors
and warning callouts reflect deterministic CalculationResult outputs only.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class DiagramShape:
    """2D geometric primitive in schematic coordinates."""

    shape_id: str
    kind: str  # "rect", "line", "circle", "polygon", "arc"
    coords: Tuple[float, ...]
    fill_color: str = "#fde6cf"
    stroke_color: str = "#343a40"
    stroke_width: float = 1.5
    label: str = ""


@dataclass(frozen=True)
class DiagramDimension:
    """Typed dimension callout bound to user input geometry."""

    dim_id: str
    p1: Tuple[float, float]
    p2: Tuple[float, float]
    label: str
    symbol: str = ""
    value: Optional[float] = None
    unit: str = ""
    color: str = "#007bff"


@dataclass(frozen=True)
class DiagramForceVector:
    """Engine-derived force/moment/pressure vector (never fabricated without a result)."""

    vector_id: str
    origin: Tuple[float, float]
    direction: Tuple[float, float]
    label: str
    magnitude: Optional[float] = None
    unit: str = ""
    color: str = "#d96818"
    is_engine_derived: bool = True
    is_stale: bool = False


@dataclass(frozen=True)
class DiagramCalloutPill:
    """Status or detailing warning pill rendered in Panel 2."""

    text: str
    severity: str = "warning"  # "info", "warning", "pass", "fail"
    position: str = "top_right"


@dataclass(frozen=True)
class DiagramSpec:
    """Complete Qt-independent schematic specification for Panel 2 & PDF/XLSX export."""

    diagram_id: str
    module_id: str
    title: str
    is_empty_state: bool = False
    empty_message: str = ""
    has_geometry: bool = True
    has_engine_result: bool = False
    is_stale: bool = False
    geometry_params: Dict[str, Any] = field(default_factory=dict)
    derived_params: Dict[str, Any] = field(default_factory=dict)
    shapes: Tuple[DiagramShape, ...] = ()
    dimensions: Tuple[DiagramDimension, ...] = ()
    forces: Tuple[DiagramForceVector, ...] = ()
    callouts: Tuple[DiagramCalloutPill, ...] = ()
    summary_badge: str = ""
