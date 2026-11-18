"""Single ModuleRegistry exports for WP-3."""

from app.registry.module_spec import FieldSpec, ModuleMaturity, ModuleSpec
from app.registry.module_registry import ModuleRegistry, build_default_registry, get_module_registry

__all__ = [
    "FieldSpec",
    "ModuleMaturity",
    "ModuleRegistry",
    "ModuleSpec",
    "build_default_registry",
    "get_module_registry",
]
