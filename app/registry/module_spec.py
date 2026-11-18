"""Module specification, field schema, and maturity contract definitions for WP-3."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

from app.models import CalculationResult


class ModuleMaturity(str, Enum):
    """Lifecycle maturity gating for registered calculation modules."""

    VERIFIED = "verified"
    PREVIEW = "preview"
    COMING_SOON = "coming_soon"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class FieldSpec:
    """Typed schema specification for a single engineering input parameter."""

    key: str
    label: str
    symbol: Optional[str] = None
    quantity_type: Optional[str] = None
    unit: Optional[str] = None
    value_type: str = "float"  # "float", "int", "enum", "bool", "text"
    section: str = "Parameters"
    required: bool = True
    default_value: Any = None
    default_reference: Optional[str] = None
    benchmark_value: Any = None
    enum_options: Tuple[str, ...] = ()
    enum_source: Optional[str] = None
    validation: Dict[str, Any] = field(default_factory=dict)
    visible_if: Optional[str] = None
    affects_geometry: bool = True
    affects_analysis: bool = True


@dataclass(frozen=True)
class ModuleSpec:
    """Single source of truth describing a calculation module across UI, registry, and dispatch."""

    module_id: str
    aliases: Tuple[str, ...]
    category: str  # "Loads (ASCE 7)", "Wood (NDS)", "Steel (AISC)", "Concrete / CMU (ACI / TMS)"
    title: str
    subtitle: str
    description: str
    code_family: str
    default_name: str
    default_group: str
    preview_type: str
    calculation_callable: Optional[Callable[..., CalculationResult]]
    fields: Tuple[FieldSpec, ...]
    diagram_id: Optional[str]
    procedure_md: Optional[str]
    maturity: ModuleMaturity = ModuleMaturity.VERIFIED
    supported_methods: Tuple[str, ...] = ("ASD", "LRFD")
    preset_inputs: Dict[str, Any] = field(default_factory=dict)
    is_canonical: bool = True
    show_in_catalog: bool = True
