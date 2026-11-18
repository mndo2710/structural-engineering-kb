"""Canonical ModuleRegistry for WP-3: Single source of truth for module catalog, schemas, and dispatch."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.registry.module_spec import FieldSpec, ModuleMaturity, ModuleSpec


_CODE_DISPLAY_MAP: Dict[Tuple[str, str], str] = {
    ("ASCE_7", "v7_22"): "ASCE 7-22",
    ("ASCE_7", "v7_16"): "ASCE 7-16",
    ("IBC", "v2024"): "2024 IBC",
    ("IBC", "v2021"): "2021 IBC",
    ("CBC", "v2025"): "2025 CBC",
    ("NDS", "v2024"): "NDS 2024",
    ("SDPWS", "v2021"): "SDPWS 2021",
    ("AISC_360", "v16th_ed"): "AISC 360-22",
    ("ACI_318", "aci_318_19"): "ACI 318-19",
    ("ACI_318", "aci_318_25"): "ACI 318-25",
    ("TMS_402", "tms_402_22"): "TMS 402-22",
}


class ModuleRegistry:
    """Central registry unifying Add Calculation catalog, InputForm schemas, and CalculationService dispatch."""

    CATEGORIES_ORDER: Tuple[str, ...] = (
        "Loads (ASCE 7)",
        "Wood (NDS)",
        "Steel (AISC)",
        "Concrete / CMU (ACI / TMS)",
    )

    def __init__(self, active_code_registry_path: Optional[Path] = None) -> None:
        if active_code_registry_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent
            active_code_registry_path = repo_root / "config" / "active_code_registry.json"
        self._active_code_registry_path = Path(active_code_registry_path)
        self._active_codes: Dict[str, str] = self._load_active_codes()

        self._modules: Dict[str, ModuleSpec] = {}
        self._aliases: Dict[str, str] = {}

    def _load_active_codes(self) -> Dict[str, str]:
        if not self._active_code_registry_path.exists():
            return {}
        with open(self._active_code_registry_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return dict(data.get("ACTIVE_CODES", {}))

    def reload_active_codes(self) -> Dict[str, str]:
        """Reload active code editions from config/active_code_registry.json."""
        self._active_codes = self._load_active_codes()
        return dict(self._active_codes)

    def register(self, spec: ModuleSpec) -> None:
        """Register a ModuleSpec and index all of its aliases with uniqueness checks."""
        if spec.module_id in self._modules or spec.module_id in self._aliases:
            raise ValueError(f"Duplicate module_id registration: '{spec.module_id}'")
        for alias in spec.aliases:
            if alias in self._modules or alias in self._aliases:
                raise ValueError(f"Duplicate module alias registration: '{alias}'")

        self._modules[spec.module_id] = spec
        for alias in spec.aliases:
            self._aliases[alias] = spec.module_id

    def resolve(self, module_id_or_alias: str) -> ModuleSpec:
        """Resolve a canonical module_id or alias to its registered ModuleSpec."""
        key = module_id_or_alias.strip()
        if key in self._modules:
            return self._modules[key]
        if key in self._aliases:
            return self._modules[self._aliases[key]]
        raise KeyError(f"Module '{module_id_or_alias}' is not registered in ModuleRegistry.")

    def get(self, module_id_or_alias: str) -> Optional[ModuleSpec]:
        """Return ModuleSpec if registered, otherwise None."""
        try:
            return self.resolve(module_id_or_alias)
        except KeyError:
            return None

    def list_modules(
        self,
        maturity: Optional[ModuleMaturity] = None,
        category: Optional[str] = None,
        canonical_only: bool = False,
        catalog_only: bool = False,
    ) -> List[ModuleSpec]:
        """Return registered ModuleSpec entries filtered by optional criteria."""
        items: List[ModuleSpec] = []
        for spec in self._modules.values():
            if maturity is not None and spec.maturity != maturity:
                continue
            if category is not None and spec.category != category:
                continue
            if canonical_only and not spec.is_canonical:
                continue
            if catalog_only and not spec.show_in_catalog:
                continue
            items.append(spec)
        return items

    def list_canonical_verified_ids(self) -> List[str]:
        """Return canonical verified module IDs in registration order."""
        return [
            spec.module_id
            for spec in self._modules.values()
            if spec.maturity == ModuleMaturity.VERIFIED and spec.is_canonical
        ]

    def get_catalog_by_category(self) -> Dict[str, List[ModuleSpec]]:
        """Group catalog-visible ModuleSpec templates by UI dialog category."""
        grouped: Dict[str, List[ModuleSpec]] = {cat: [] for cat in self.CATEGORIES_ORDER}
        for spec in self._modules.values():
            if not spec.show_in_catalog:
                continue
            grouped.setdefault(spec.category, []).append(spec)
        return grouped

    def _format_code_token(self, family: str) -> str:
        raw_ver = self._active_codes.get(family, "")
        mapped = _CODE_DISPLAY_MAP.get((family, raw_ver))
        if mapped:
            return mapped
        if raw_ver:
            return f"{family.replace('_', ' ')} {raw_ver}"
        return family.replace("_", " ")

    def resolve_code_display(self, module_id_or_family: str) -> str:
        """Resolve human-readable active code edition dynamically from active_code_registry.json."""
        key = module_id_or_family.strip()
        spec = self.get(key)
        if spec is not None:
            if spec.module_id == "ibc_guardrail_loads":
                return f"{self._format_code_token('IBC')} / {self._format_code_token('ASCE_7')}"
            if spec.module_id in ("wood_shear_wall_sdpws", "wood_diaphragm_sdpws"):
                return f"{self._format_code_token('SDPWS')} / {self._format_code_token('NDS')}"
            if spec.module_id == "wood_simpson_hanger_tie":
                return f"Simpson C-C-2026 / {self._format_code_token('NDS')}"
            if spec.code_family == "ACI_TMS":
                return f"{self._format_code_token('ACI_318')} / {self._format_code_token('TMS_402')}"
            return self._format_code_token(spec.code_family)

        # Fallback for direct code family lookup
        upper = key.upper()
        if upper in ("ACI_TMS", "CONCRETE", "CMU"):
            return f"{self._format_code_token('ACI_318')} / {self._format_code_token('TMS_402')}"
        if upper == "WOOD_LATERAL":
            return f"{self._format_code_token('NDS')} / {self._format_code_token('SDPWS')}"
        if upper in self._active_codes:
            return self._format_code_token(upper)
        return self._format_code_token(key)

    def get_benchmark_inputs(self, module_id_or_alias: str) -> Dict[str, Any]:
        """Return controlled benchmark/sample inputs for tests and explicit demos."""
        spec = self.resolve(module_id_or_alias)
        values: Dict[str, Any] = dict(spec.preset_inputs)
        for fld in spec.fields:
            if fld.benchmark_value is not None:
                values[fld.key] = fld.benchmark_value
        return values

    def get_default_inputs(self, module_id_or_alias: str) -> Dict[str, Any]:
        """Return only code-authorized default inputs (never benchmark sample values)."""
        spec = self.resolve(module_id_or_alias)
        values: Dict[str, Any] = dict(spec.preset_inputs)
        for fld in spec.fields:
            if fld.default_value is not None:
                values[fld.key] = fld.default_value
        return values


def _build_fastener_fields(
    fastener_type_bm: str = "Lag_Screw",
    d_in_bm: float = 0.375,
    l_in_bm: float = 4.0,
    n_fasteners_bm: int = 4,
    v_demand_bm: float = 550.0,
    t_demand_bm: float = 320.0,
) -> Tuple[FieldSpec, ...]:
    return (
        FieldSpec(
            key="fastener_type",
            label="Type (Lag_Screw / Simpson_SDS / Wood_Screw / Common_Nail)",
            symbol="Type",
            value_type="enum",
            section="Fastener",
            enum_options=("Lag_Screw", "Simpson_SDS", "Wood_Screw", "Common_Nail"),
            benchmark_value=fastener_type_bm,
            affects_geometry=False,
        ),
        FieldSpec(
            key="species",
            label="Wood Species",
            symbol="Species",
            value_type="enum",
            section="Wood Member",
            enum_options=("Douglas Fir-Larch", "Southern Pine", "Hem-Fir", "Spruce-Pine-Fir"),
            enum_source="NDS-2024_Table_12.3.3A.csv",
            benchmark_value="Douglas Fir-Larch",
            affects_geometry=False,
        ),
        FieldSpec(
            key="side_member_type",
            label="Side Member (Wood / Steel)",
            symbol="Side",
            value_type="enum",
            section="Wood Member",
            enum_options=("Wood", "Steel"),
            benchmark_value="Wood",
        ),
        FieldSpec(
            key="D_in",
            label="Fastener Diameter D (in.)",
            symbol="D",
            quantity_type="length",
            unit="in.",
            value_type="float",
            section="Fastener",
            benchmark_value=d_in_bm,
            validation={"gt": 0.0},
        ),
        FieldSpec(
            key="L_in",
            label="Fastener Length L (in.)",
            symbol="L",
            quantity_type="length",
            unit="in.",
            value_type="float",
            section="Fastener",
            benchmark_value=l_in_bm,
            validation={"gt": 0.0},
        ),
        FieldSpec(
            key="t_s_in",
            label="Side Thickness t_s (in.)",
            symbol="t_s",
            quantity_type="length",
            unit="in.",
            value_type="float",
            section="Wood Member",
            benchmark_value=1.5,
            validation={"gt": 0.0},
        ),
        FieldSpec(
            key="n_fasteners",
            label="Total Fasteners N",
            symbol="N",
            quantity_type="count",
            value_type="int",
            section="Fastener",
            benchmark_value=n_fasteners_bm,
            validation={"ge": 1},
            affects_geometry=False,
        ),
        FieldSpec(
            key="C_D",
            label="Load Duration Factor C_D",
            symbol="C_D",
            quantity_type="factor",
            value_type="float",
            section="Adjustment Factors",
            benchmark_value=1.00,
            validation={"gt": 0.0, "le": 2.0},
            affects_geometry=False,
        ),
        FieldSpec(
            key="V_demand_lbs",
            label="Lateral Shear Demand V (lbs)",
            symbol="V",
            quantity_type="force",
            unit="lbs",
            value_type="float",
            section="Demand",
            benchmark_value=v_demand_bm,
            validation={"ge": 0.0},
            affects_geometry=False,
        ),
        FieldSpec(
            key="T_demand_lbs",
            label="Axial Withdrawal Demand T (lbs)",
            symbol="T",
            quantity_type="force",
            unit="lbs",
            value_type="float",
            section="Demand",
            benchmark_value=t_demand_bm,
            validation={"ge": 0.0},
            affects_geometry=False,
        ),
    )


def build_default_registry() -> ModuleRegistry:
    """Create and populate the canonical application ModuleRegistry."""
    from core.aci318.anchors import calculate_concrete_anchorage
    from core.aisc360.angles import calculate_steel_angle_connection
    from core.aisc360.base_plate import calculate_steel_base_plate
    from core.aisc360.bolts import calculate_steel_bolted_connection
    from core.aisc360.hss_connections import calculate_steel_hss_connection
    from core.aisc360.shear_tab import calculate_steel_shear_tab
    from core.aisc360.welds import calculate_steel_welded_connection
    from core.asce7.wind.awning import calculate_awning_canopy_loads
    from core.asce7.wind.guardrail import calculate_guardrail_loads
    from core.asce7.wind.parapet import calculate_parapet_wind
    from core.asce7.wind.roof_overhang import calculate_roof_overhang_wind
    from core.asce7.wind.trellis import calculate_trellis_loads
    from core.nds.connections.simpson_connectors import calculate_simpson_hanger_tie
    from core.nds.fasteners.bolts import calculate_wood_bolt_connection
    from core.nds.fasteners.nails_screws import calculate_wood_fastener_connection
    from core.nds.lateral.diaphragms import calculate_wood_diaphragm
    from core.nds.lateral.shear_walls import calculate_wood_shear_wall
    from core.tms402.cmu_anchorage import calculate_cmu_anchorage
    from core.tms402.embedded_post import calculate_embedded_steel_post

    registry = ModuleRegistry()

    # ==========================================================================
    # 1. LOADS (ASCE 7-22 / 2024 IBC) — 5 Verified Canonical Modules
    # ==========================================================================
    registry.register(
        ModuleSpec(
            module_id="asce7_parapet_wind",
            aliases=("cc_parapet",),
            category="Loads (ASCE 7)",
            title="Parapet wind pressure",
            subtitle="Component & Cladding net pressure · ASCE 7-22 Sec. 30.9",
            description="MWFRS and C&C parapet wind pressures, stud base shear/moment, and roof diaphragm reaction.",
            code_family="ASCE_7",
            default_name="C-10 · Roof parapet wind",
            default_group="Roof framing",
            preview_type="loads",
            calculation_callable=calculate_parapet_wind,
            diagram_id="cc_parapet",
            procedure_md="procedures/01_loads_and_seismic/cc_wind_parapet_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("V_mph", "Basic Wind Speed V (mph)", "V", "velocity", "mph", "float", "Wind Parameters", benchmark_value=115.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("exposure", "Exposure Category (B/C/D)", "Exp", value_type="enum", section="Wind Parameters", enum_options=("B", "C", "D"), benchmark_value="C", affects_geometry=False),
                FieldSpec("h_roof_ft", "Mean Roof Height h (ft)", "h", "length", "ft", "float", "Geometry", benchmark_value=25.0, validation={"gt": 0.0}),
                FieldSpec("h_par_ft", "Parapet Height h_par (ft)", "h_par", "length", "ft", "float", "Geometry", benchmark_value=3.5, validation={"gt": 0.0}),
                FieldSpec("spacing_ft", "Stud Spacing s (ft)", "s", "length", "ft", "float", "Geometry", benchmark_value=1.333, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("roof_slope_deg", "Roof Slope θ (deg)", "theta", "angle", "deg", "float", "Geometry", benchmark_value=5.0, validation={"ge": 0.0}),
                FieldSpec("wall_zone", "Wall Zone (Zone 4 / Zone 5)", "Zone_w", value_type="enum", section="Zones", enum_options=("Zone 4", "Zone 5"), benchmark_value="Zone 5", affects_geometry=False),
                FieldSpec("roof_zone", "Roof Zone (Zone 2 / Zone 3)", "Zone_r", value_type="enum", section="Zones", enum_options=("Zone 1", "Zone 2", "Zone 3"), benchmark_value="Zone 3", affects_geometry=False),
                FieldSpec("backspan_ft", "Stud Backspan L_back (ft)", "L_back", "length", "ft", "float", "Geometry", benchmark_value=10.0, validation={"gt": 0.0}),
                FieldSpec("M_cap_asd_lb_ft", "Stud Bending Cap M_cap (lb-ft)", "M_cap", "moment", "lb-ft", "float", "Capacities", benchmark_value=650.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("V_cap_asd_lbs", "Base Shear Cap V_cap (lbs)", "V_cap", "force", "lbs", "float", "Capacities", benchmark_value=450.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("R_cap_asd_lbs", "Roof Diaphragm Cap R_cap (lbs)", "R_cap", "force", "lbs", "float", "Capacities", benchmark_value=600.0, validation={"gt": 0.0}, affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="asce7_roof_overhang",
            aliases=("cc_overhang",),
            category="Loads (ASCE 7)",
            title="Roof overhang wind pressure",
            subtitle="Combined top roof + bottom soffit uplift · ASCE 7-22 Sec. 30.7",
            description="Roof overhang net uplift pressure, cantilever rafter bending, and hurricane tie uplift demand.",
            code_family="ASCE_7",
            default_name="C-11 · Eaves overhang",
            default_group="Roof framing",
            preview_type="loads",
            calculation_callable=calculate_roof_overhang_wind,
            diagram_id="cc_overhang",
            procedure_md="procedures/01_loads_and_seismic/cc_wind_overhang_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("V_mph", "Basic Wind Speed V (mph)", "V", "velocity", "mph", "float", "Wind Parameters", benchmark_value=115.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("exposure", "Exposure Category (B/C/D)", "Exp", value_type="enum", section="Wind Parameters", enum_options=("B", "C", "D"), benchmark_value="C", affects_geometry=False),
                FieldSpec("h_roof_ft", "Mean Roof Height h (ft)", "h", "length", "ft", "float", "Geometry", benchmark_value=20.0, validation={"gt": 0.0}),
                FieldSpec("L_oh_ft", "Overhang Projection L_oh (ft)", "L_oh", "length", "ft", "float", "Geometry", benchmark_value=2.5, validation={"gt": 0.0}),
                FieldSpec("L_back_ft", "Rafter Backspan L_back (ft)", "L_back", "length", "ft", "float", "Geometry", benchmark_value=14.0, validation={"gt": 0.0}),
                FieldSpec("spacing_ft", "Rafter Spacing s (ft)", "s", "length", "ft", "float", "Geometry", benchmark_value=2.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("roof_slope_deg", "Roof Slope θ (deg)", "theta", "angle", "deg", "float", "Geometry", benchmark_value=15.0, validation={"ge": 0.0}),
                FieldSpec("roof_zone", "Roof Zone (Zone 2 / Zone 3)", "Zone_r", value_type="enum", section="Zones", enum_options=("Zone 1", "Zone 2", "Zone 3"), benchmark_value="Zone 2", affects_geometry=False),
                FieldSpec("dead_load_psf", "Roof Dead Load D (psf)", "w_D", "pressure", "psf", "float", "Loads", benchmark_value=12.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("R_tie_cap_asd_lbs", "Hurricane Tie Cap R_cap (lbs)", "R_cap", "force", "lbs", "float", "Capacities", benchmark_value=685.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("M_cap_asd_lb_ft", "Rafter Bending Cap M_cap (lb-ft)", "M_cap", "moment", "lb-ft", "float", "Capacities", benchmark_value=950.0, validation={"gt": 0.0}, affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="asce7_awning_canopy",
            aliases=("cc_awning",),
            category="Loads (ASCE 7)",
            title="Awning and canopy loads",
            subtitle="Attached canopy wind & Ch. 13 seismic · ASCE 7-22 Sec. 30.11",
            description="Attached awning/canopy net wind pressures, Chapter 13 seismic Fp, and bracket/tie-back reactions.",
            code_family="ASCE_7",
            default_name="C-12 · Entry canopy wind",
            default_group="Level 1",
            preview_type="loads",
            calculation_callable=calculate_awning_canopy_loads,
            diagram_id="cc_awning",
            procedure_md="procedures/01_loads_and_seismic/cc_awning_canopy_loads_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("V_mph", "Basic Wind Speed V (mph)", "V", "velocity", "mph", "float", "Wind Parameters", benchmark_value=115.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("exposure", "Exposure Category (B/C/D)", "Exp", value_type="enum", section="Wind Parameters", enum_options=("B", "C", "D"), benchmark_value="C", affects_geometry=False),
                FieldSpec("h_roof_ft", "Main Roof Height h (ft)", "h", "length", "ft", "float", "Geometry", benchmark_value=20.0, validation={"gt": 0.0}),
                FieldSpec("he_ft", "Eave Height h_e (ft)", "h_e", "length", "ft", "float", "Geometry", benchmark_value=20.0, validation={"gt": 0.0}),
                FieldSpec("hc_ft", "Canopy Height h_c (ft)", "h_c", "length", "ft", "float", "Geometry", benchmark_value=10.0, validation={"gt": 0.0}),
                FieldSpec("Bc_ft", "Canopy Projection B_c (ft)", "B_c", "length", "ft", "float", "Geometry", benchmark_value=5.0, validation={"gt": 0.0}),
                FieldSpec("Sb_ft", "Bracket Spacing S_b (ft)", "S_b", "length", "ft", "float", "Geometry", benchmark_value=6.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("w_D_psf", "Canopy Dead Load w_D (psf)", "w_D", "pressure", "psf", "float", "Loads", benchmark_value=12.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("w_Lr_psf", "Canopy Live Load w_Lr (psf)", "w_Lr", "pressure", "psf", "float", "Loads", benchmark_value=20.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("SDS_g", "Seismic Parameter S_DS (g)", "S_DS", "acceleration", "g", "float", "Seismic Parameters", benchmark_value=1.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("support_type", "Support (Cantilever_Bracket / TieBack_Hanger)", "Support", value_type="enum", section="Geometry", enum_options=("Cantilever_Bracket", "TieBack_Hanger"), benchmark_value="Cantilever_Bracket"),
                FieldSpec("M_wall_cap_asd_lb_ft", "Wall Moment Cap M_cap (lb-ft)", "M_cap", "moment", "lb-ft", "float", "Capacities", benchmark_value=1600.0, validation={"gt": 0.0}, affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="asce7_trellis_loads",
            aliases=("cc_trellis",),
            category="Loads (ASCE 7)",
            title="Open-frame trellis & pergola loads",
            subtitle="Open frame drag Cf & post overturning · ASCE 7-22 Sec. 29.4",
            description="Open-frame trellis wind force coefficient Cf, seismic demands, and post base shear/moment.",
            code_family="ASCE_7",
            default_name="C-13 · Patio trellis wind",
            default_group="Level 1",
            preview_type="loads",
            calculation_callable=calculate_trellis_loads,
            diagram_id="cc_trellis",
            procedure_md="procedures/01_loads_and_seismic/cc_trellis_open_wind_seismic_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("V_mph", "Basic Wind Speed V (mph)", "V", "velocity", "mph", "float", "Wind Parameters", benchmark_value=115.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("exposure", "Exposure Category (B/C/D)", "Exp", value_type="enum", section="Wind Parameters", enum_options=("B", "C", "D"), benchmark_value="C", affects_geometry=False),
                FieldSpec("z_top_ft", "Trellis Top Height z (ft)", "z", "length", "ft", "float", "Geometry", benchmark_value=10.0, validation={"gt": 0.0}),
                FieldSpec("Hp_ft", "Post Clear Height H_p (ft)", "H_p", "length", "ft", "float", "Geometry", benchmark_value=10.0, validation={"gt": 0.0}),
                FieldSpec("Lt_ft", "Plan Length L_t (ft)", "L_t", "length", "ft", "float", "Geometry", benchmark_value=16.0, validation={"gt": 0.0}),
                FieldSpec("Bt_ft", "Plan Width B_t (ft)", "B_t", "length", "ft", "float", "Geometry", benchmark_value=12.0, validation={"gt": 0.0}),
                FieldSpec("Af_eff_ft2", "Projected Solid Area A_f,eff (ft^2)", "A_f", "area", "ft^2", "float", "Geometry", benchmark_value=28.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("epsilon_elev", "Solidity Ratio ε (As/Ag)", "epsilon", "ratio", None, "float", "Geometry", benchmark_value=0.18, validation={"gt": 0.0, "le": 1.0}, affects_geometry=False),
                FieldSpec("num_posts", "Number of Posts N_p", "N_p", "count", None, "int", "Geometry", benchmark_value=4, validation={"ge": 1}, affects_geometry=False),
                FieldSpec("w_D_psf", "Trellis Dead Load w_D (psf)", "w_D", "pressure", "psf", "float", "Loads", benchmark_value=8.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("SDS_g", "Seismic Parameter S_DS (g)", "S_DS", "acceleration", "g", "float", "Seismic Parameters", benchmark_value=1.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("M_post_cap_asd_lb_ft", "Post Base Moment Cap (lb-ft)", "M_cap", "moment", "lb-ft", "float", "Capacities", benchmark_value=2000.0, validation={"gt": 0.0}, affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="ibc_guardrail_loads",
            aliases=("cc_guardrail",),
            category="Loads (ASCE 7)",
            title="Guardrail and handrail loads",
            subtitle="200 lb concentrated / 50 plf uniform & wind · 2024 IBC Sec. 1607.9",
            description="Guardrail top rail, post base moment, and anchor bolt tension under IBC live and wind loads.",
            code_family="IBC",
            default_name="C-14 · Deck guardrail post",
            default_group="Level 2",
            preview_type="loads",
            calculation_callable=calculate_guardrail_loads,
            diagram_id="cc_guardrail",
            procedure_md="procedures/01_loads_and_seismic/guardrail_handrail_loads_ibc_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("occupancy", "Occupancy (R-3_Residential / Commercial_Standard)", "Occ", value_type="enum", section="Load Basis", enum_options=("R-3_Residential", "Commercial_Standard"), benchmark_value="R-3_Residential", affects_geometry=False),
                FieldSpec("H_guard_in", "Guard Height H_guard (in.)", "H_guard", "length", "in.", "float", "Geometry", benchmark_value=42.0, validation={"gt": 0.0}),
                FieldSpec("S_post_ft", "Post Spacing S_post (ft)", "S_post", "length", "ft", "float", "Geometry", benchmark_value=5.0, validation={"gt": 0.0}),
                FieldSpec("e_fas_in", "Fascia Offset e_fas (in.)", "e_fas", "length", "in.", "float", "Geometry", benchmark_value=0.0, validation={"ge": 0.0}),
                FieldSpec("p_W_psf", "Exterior Wind Pressure p_W (psf)", "p_W", "pressure", "psf", "float", "Wind Parameters", benchmark_value=20.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("epsilon_guard", "Guard Solidity Ratio ε", "epsilon", "ratio", None, "float", "Geometry", benchmark_value=0.30, validation={"gt": 0.0, "le": 1.0}, affects_geometry=False),
                FieldSpec("N_t_bolts", "Tension Row Bolts N_t", "N_t", "count", None, "int", "Anchorage", benchmark_value=2, validation={"ge": 1}, affects_geometry=False),
                FieldSpec("d_bolt_in", "Bolt Lever Arm d_bolt (in.)", "d_bolt", "length", "in.", "float", "Anchorage", benchmark_value=4.25, validation={"gt": 0.0}),
                FieldSpec("T_bolt_cap_asd_lbs", "Bolt Tension Cap T_cap (lbs)", "T_cap", "force", "lbs", "float", "Capacities", benchmark_value=1250.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("M_post_cap_asd_lb_ft", "Post Flexural Cap M_cap (lb-ft)", "M_cap", "moment", "lb-ft", "float", "Capacities", benchmark_value=950.0, validation={"gt": 0.0}, affects_geometry=False),
            ),
        )
    )

    # ==========================================================================
    # 2. WOOD (NDS 2024 / SDPWS 2021 / Simpson C-C-2026)
    # ==========================================================================
    registry.register(
        ModuleSpec(
            module_id="wood_bolt_lateral",
            aliases=("wood_bolt_nds",),
            category="Wood (NDS)",
            title="Bolt / dowel — lateral",
            subtitle="Single and double shear · yield modes I–IV · NDS Ch. 12",
            description="Wood bolted connection EYM yield modes, Hankinson angle, Cg, C_Delta, and Appendix E tear-out.",
            code_family="NDS",
            default_name="C-06 · Bolt connection",
            default_group="Roof framing",
            preview_type="wood_bolt",
            calculation_callable=calculate_wood_bolt_connection,
            diagram_id="wood_bolt_lateral",
            procedure_md="procedures/02_wood_design/wood_bolt_connection_nds_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("D_in", "Bolt Diameter D (in.)", "D", "length", "in.", "float", "Fastener", benchmark_value=0.625, validation={"gt": 0.0}),
                FieldSpec("shear_planes", "Shear Planes (Single Shear / Double Shear)", "Planes", value_type="enum", section="Fastener", enum_options=("Single Shear", "Double Shear"), benchmark_value="Single Shear"),
                FieldSpec("F_yb_psi", "Bolt Bending Yield F_yb (psi)", "F_yb", "stress", "psi", "float", "Fastener", benchmark_value=45000.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("main_species", "Main Member Species", "Species", value_type="enum", section="Main Member", enum_options=("Douglas Fir-Larch", "Southern Pine", "Hem-Fir", "Spruce-Pine-Fir"), enum_source="NDS-2024_Table_12.3.3A.csv", benchmark_value="Douglas Fir-Larch", affects_geometry=False),
                FieldSpec("side_material", "Side Member (Wood / Steel / Concrete)", "Side", value_type="enum", section="Side Member", enum_options=("Wood", "Steel", "Concrete"), benchmark_value="Wood"),
                FieldSpec("t_m_in", "Main Thickness t_m (in.)", "t_m", "length", "in.", "float", "Main Member", benchmark_value=1.5, validation={"gt": 0.0}),
                FieldSpec("t_s_in", "Side Thickness t_s (in.)", "t_s", "length", "in.", "float", "Side Member", benchmark_value=1.5, validation={"gt": 0.0}),
                FieldSpec("e_end_m_in", "Loaded End Distance e_end,m (in.)", "e_end,m", "length", "in.", "float", "Main Member", benchmark_value=3.0, validation={"gt": 0.0}),
                FieldSpec("n_rows", "Number of Bolt Rows n_rows", "n_rows", "count", None, "int", "Geometry", benchmark_value=1, validation={"ge": 1}),
                FieldSpec("n_bolts_per_row", "Bolts per Row n_b", "n_b", "count", None, "int", "Geometry", benchmark_value=1, validation={"ge": 1}),
                FieldSpec("C_D", "Load Duration Factor C_D", "C_D", "factor", None, "float", "Adjustment Factors", benchmark_value=1.00, validation={"gt": 0.0, "le": 2.0}, affects_geometry=False),
                FieldSpec("P_demand_lbs", "Applied Tension Demand P (lbs)", "P", "force", "lbs", "float", "Demand", benchmark_value=340.0, validation={"gt": 0.0}, affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="wood_fastener_nds",
            aliases=(),
            category="Wood (NDS)",
            title="Nail / Wood Screw / Lag Screw / Simpson SDS (NDS Ch. 12)",
            subtitle="Lateral, withdrawal & combined interaction · NDS Ch. 12 & ESR-2236",
            description="Unified NDS 2024 nail, wood screw, lag screw, and Simpson SDS screw connection checks.",
            code_family="NDS",
            default_name="C-07 · Fastener connection",
            default_group="Roof framing",
            preview_type="wood_bolt",
            calculation_callable=calculate_wood_fastener_connection,
            diagram_id="wood_fastener_nds",
            procedure_md="procedures/02_wood_design/wood_nail_screw_fastener_nds_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            is_canonical=True,
            show_in_catalog=False,
            fields=_build_fastener_fields(),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="wood_nail_lateral",
            aliases=(),
            category="Wood (NDS)",
            title="Nail / wood screw — lateral",
            subtitle="NDS Ch. 12",
            description="NDS 2024 Chapter 12 lateral shear connection for common nails and wood screws.",
            code_family="NDS",
            default_name="C-07 · Nail connection",
            default_group="Roof framing",
            preview_type="wood_bolt",
            calculation_callable=calculate_wood_fastener_connection,
            diagram_id="wood_fastener_nds",
            procedure_md="procedures/02_wood_design/wood_nail_screw_fastener_nds_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            is_canonical=False,
            show_in_catalog=True,
            preset_inputs={"fastener_category": "Common Nail", "fastener_id": "10d Common"},
            fields=_build_fastener_fields(
                fastener_type_bm="Common_Nail",
                d_in_bm=0.148,
                l_in_bm=3.0,
                n_fasteners_bm=6,
                v_demand_bm=650.0,
                t_demand_bm=0.0,
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="wood_screw_withdrawal",
            aliases=(),
            category="Wood (NDS)",
            title="Lag screw / nail — withdrawal",
            subtitle="NDS 12.2",
            description="NDS 2024 Section 12.2 lag screw and nail axial withdrawal capacity check.",
            code_family="NDS",
            default_name="C-08 · Lag screw withdrawal",
            default_group="Roof framing",
            preview_type="wood_bolt",
            calculation_callable=calculate_wood_fastener_connection,
            diagram_id="wood_fastener_nds",
            procedure_md="procedures/02_wood_design/wood_lag_screw_nds_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            is_canonical=False,
            show_in_catalog=True,
            preset_inputs={"fastener_category": "Lag Screw", "fastener_id": '1/2" Lag'},
            fields=_build_fastener_fields(
                fastener_type_bm="Lag_Screw",
                d_in_bm=0.50,
                l_in_bm=4.5,
                n_fasteners_bm=4,
                v_demand_bm=0.0,
                t_demand_bm=450.0,
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="wood_combined_lateral_withdrawal",
            aliases=(),
            category="Wood (NDS)",
            title="Combined lateral + withdrawal",
            subtitle="NDS 12.4",
            description="NDS 2024 Section 12.4 combined lateral shear and axial withdrawal interaction.",
            code_family="NDS",
            default_name="C-09 · Combined fastener check",
            default_group="Roof framing",
            preview_type="wood_bolt",
            calculation_callable=calculate_wood_fastener_connection,
            diagram_id="wood_fastener_nds",
            procedure_md="procedures/02_wood_design/wood_nail_screw_fastener_nds_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            is_canonical=False,
            show_in_catalog=True,
            preset_inputs={"fastener_category": "Lag Screw", "fastener_id": '1/2" Lag'},
            fields=_build_fastener_fields(
                fastener_type_bm="Lag_Screw",
                d_in_bm=0.50,
                l_in_bm=4.5,
                n_fasteners_bm=4,
                v_demand_bm=650.0,
                t_demand_bm=320.0,
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="wood_shear_wall_sdpws",
            aliases=(),
            category="Wood (NDS)",
            title="Wood-frame shear wall & holdown",
            subtitle="Unit shear, C_ar, HDU holdown & 3-term drift · SDPWS 2021 Sec. 4.3",
            description="Wood structural panel shear wall unit shear, aspect ratio factor, holdown tension, and story drift.",
            code_family="SDPWS",
            default_name="SW-01 · Exterior wood shear wall",
            default_group="Level 1",
            preview_type="wood_bolt",
            calculation_callable=calculate_wood_shear_wall,
            diagram_id="wood_shear_wall_sdpws",
            procedure_md="procedures/02_wood_design/wood_shear_wall_holdown_sdpws_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("h_ft", "Wall Clear Height h (ft)", "h", "length", "ft", "float", "Geometry", benchmark_value=10.0, validation={"gt": 0.0}),
                FieldSpec("bs_ft", "Wall Segment Width b_s (ft)", "b_s", "length", "ft", "float", "Geometry", benchmark_value=4.0, validation={"gt": 0.0}),
                FieldSpec("V_asd_lbs", "ASD Seismic Shear V_ASD (lbs)", "V_ASD", "force", "lbs", "float", "Loads", benchmark_value=2240.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("V_lrfd_lbs", "LRFD Seismic Shear V_LRFD (lbs)", "V_LRFD", "force", "lbs", "float", "Loads", benchmark_value=3200.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("w_DL_plf", "Tributary Dead Load w_DL (plf)", "w_DL", "line_load", "plf", "float", "Loads", benchmark_value=250.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("sheathing_category", "Sheathing Category (Structural I / Sheathing)", "Category", value_type="enum", section="Sheathing", enum_options=("Structural I", "Sheathing"), benchmark_value="Structural I", affects_geometry=False),
                FieldSpec("panel_thickness", "Panel Thickness (15/32 / 7/16 / 3/8)", "t_panel", value_type="enum", section="Sheathing", enum_options=("15/32", "7/16", "3/8"), benchmark_value="15/32", affects_geometry=False),
                FieldSpec("nail_size", "Common Nail Size (10d / 8d / 6d)", "Nail", value_type="enum", section="Sheathing", enum_options=("10d", "8d", "6d"), benchmark_value="10d", affects_geometry=False),
                FieldSpec("edge_spacing_in", "Edge Nail Spacing (6 / 4 / 3 / 2 in.)", "s_edge", "length", "in.", "int", "Sheathing", benchmark_value=3, validation={"ge": 2}, affects_geometry=False),
                FieldSpec("holdown_model", "Simpson Holdown Model", "Holdown", value_type="text", section="Anchorage", enum_source="Simpson_C-C-2026_Holdowns_HDU_HD_HTT.csv", benchmark_value="HDU5-SDS2.5", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="wood_diaphragm_sdpws",
            aliases=(),
            category="Wood (NDS)",
            title="Blocked wood diaphragm, chord & collector",
            subtitle="Unit shear, 3-term deflection & Simpson straps · SDPWS 2021 Sec. 4.2",
            description="Blocked wood diaphragm shear, 3-term deflection, chord axial force, and collector strap capacity.",
            code_family="SDPWS",
            default_name="D-01 · Roof diaphragm & collector",
            default_group="Roof framing",
            preview_type="wood_bolt",
            calculation_callable=calculate_wood_diaphragm,
            diagram_id="wood_diaphragm_sdpws",
            procedure_md="procedures/02_wood_design/wood_diaphragm_chord_collector_sdpws_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("L_span_ft", "Diaphragm Span L (ft)", "L", "length", "ft", "float", "Geometry", benchmark_value=72.0, validation={"gt": 0.0}),
                FieldSpec("W_depth_ft", "Diaphragm Depth W (ft)", "W", "length", "ft", "float", "Geometry", benchmark_value=30.0, validation={"gt": 0.0}),
                FieldSpec("w_asd_plf", "ASD Uniform Load w_ASD (plf)", "w_ASD", "line_load", "plf", "float", "Loads", benchmark_value=315.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("w_lrfd_plf", "LRFD Uniform Load w_LRFD (plf)", "w_LRFD", "line_load", "plf", "float", "Loads", benchmark_value=450.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("sheathing_grade", "Grade (Sheathing and Single-Floor / Structural I)", "Grade", value_type="enum", section="Sheathing", enum_options=("Sheathing and Single-Floor", "Structural I"), benchmark_value="Sheathing and Single-Floor", affects_geometry=False),
                FieldSpec("nail_size", "Common Nail Size (10d / 8d)", "Nail", value_type="enum", section="Sheathing", enum_options=("10d", "8d"), benchmark_value="10d", affects_geometry=False),
                FieldSpec("panel_thickness", "Panel Thickness (15/32 / 7/16 / 3/8)", "t_panel", value_type="enum", section="Sheathing", enum_options=("15/32", "7/16", "3/8"), benchmark_value="15/32", affects_geometry=False),
                FieldSpec("boundary_spacing_in", "Boundary Nail Spacing (6 / 4 / 2.5 / 2 in.)", "s_b", "length", "in.", "float", "Sheathing", benchmark_value=4.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("unsupported_drag_ft", "Unsupported Collector Length (ft)", "L_drag", "length", "ft", "float", "Collector", benchmark_value=15.0, validation={"ge": 0.0}),
                FieldSpec("strap_model", "Simpson Collector Strap Model", "Strap", value_type="text", section="Collector", enum_source="Simpson_C-C-2026_Straps_CS_CMST_LSTA_MSTA_MSTC_MST.csv", benchmark_value="MSTC66", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="wood_simpson_hanger_tie",
            aliases=(),
            category="Wood (NDS)",
            title="Simpson joist hanger & hurricane tie",
            subtitle="LUS/HUS/HGUS hangers & H10A/H2.5A multi-axis tie · Simpson C-C-2026",
            description="Simpson joist hanger download/uplift and multi-axis hurricane tie interaction checks.",
            code_family="NDS",
            default_name="C-09B · Roof girder hanger & tie",
            default_group="Roof framing",
            preview_type="wood_bolt",
            calculation_callable=calculate_simpson_hanger_tie,
            diagram_id="wood_simpson_hanger_tie",
            procedure_md="procedures/02_wood_design/wood_joist_hanger_hurricane_tie_simpson_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("hanger_model", "Simpson Hanger Model", "Hanger", value_type="text", section="Joist Hanger", enum_source="Simpson_C-C-2026_Joist_Hangers_LUS_HUS_HGUS.csv", benchmark_value="HUS210-2", affects_geometry=False),
                FieldSpec("hanger_species", "Hanger Wood Species (DF/SP / SPF/HF)", "Species_h", value_type="enum", section="Joist Hanger", enum_options=("DF/SP", "SPF/HF"), benchmark_value="DF/SP", affects_geometry=False),
                FieldSpec("H_joist_in", "Carried Member Depth H (in.)", "H", "length", "in.", "float", "Joist Hanger", benchmark_value=9.25, validation={"gt": 0.0}),
                FieldSpec("R_floor_lbs", "Floor Download R_floor (lbs, CD=1.00)", "R_floor", "force", "lbs", "float", "Joist Hanger", benchmark_value=2600.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("R_roof_lbs", "Roof Download R_roof (lbs, CD=1.25)", "R_roof", "force", "lbs", "float", "Joist Hanger", benchmark_value=3150.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("U_hanger_lbs", "Hanger Wind Uplift U (lbs, CD=1.60)", "U_hgr", "force", "lbs", "float", "Joist Hanger", benchmark_value=1450.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("tie_model", "Hurricane Tie Model", "Tie", value_type="text", section="Hurricane Tie", enum_source="Simpson_C-C-2026_Hurricane_Ties_and_Lateral_Plates_H_LTP_A35.csv", benchmark_value="H10A (Nails)", affects_geometry=False),
                FieldSpec("tie_species", "Hurricane Tie Species (SPF/HF / DF/SP)", "Species_t", value_type="enum", section="Hurricane Tie", enum_options=("SPF/HF", "DF/SP"), benchmark_value="SPF/HF", affects_geometry=False),
                FieldSpec("U_tie_lbs", "Rafter Wind Uplift U_tie (lbs)", "U_tie", "force", "lbs", "float", "Hurricane Tie", benchmark_value=520.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("F1_tie_lbs", "In-Plane Shear F1 (lbs)", "F_1", "force", "lbs", "float", "Hurricane Tie", benchmark_value=320.0, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("F2_tie_lbs", "Out-of-Plane Reaction F2 (lbs)", "F_2", "force", "lbs", "float", "Hurricane Tie", benchmark_value=95.0, validation={"ge": 0.0}, affects_geometry=False),
            ),
        )
    )

    # ==========================================================================
    # 3. STEEL (AISC 360-22 / Manual 16th Ed.) — 6 Verified Modules (Day 15)
    # ==========================================================================
    registry.register(
        ModuleSpec(
            module_id="aisc_shear_tab",
            aliases=("steel_shear_tab",),
            category="Steel (AISC)",
            title="Shear tab (single-plate) connection",
            subtitle="AISC 360-22 Part 10",
            description="Conventional & extended single-plate shear connection (4-stage load path).",
            code_family="AISC_360",
            default_name="C-13 · Beam shear tab",
            default_group="Level 2",
            preview_type="steel",
            calculation_callable=calculate_steel_shear_tab,
            diagram_id="aisc_shear_tab",
            procedure_md="procedures/03_steel_design/steel_shear_tab_connection_aisc_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("beam_section", "Beam Section", "Beam", value_type="text", section="Members", benchmark_value="W18x35"),
                FieldSpec("beam_grade", "Beam Grade", "Grade", value_type="enum", section="Members", enum_options=("A992", "A36", "A572 Gr. 50"), benchmark_value="A992", affects_geometry=False),
                FieldSpec("support_section", "Support Section", "Support", value_type="text", section="Members", benchmark_value="W14x90"),
                FieldSpec("support_grade", "Support Grade", "Grade", value_type="enum", section="Members", enum_options=("A992", "A36", "A572 Gr. 50", "A500 Gr. C"), benchmark_value="A992", affects_geometry=False),
                FieldSpec("plate_grade", "Plate Grade", "Grade", value_type="enum", section="Plate & Weld", enum_options=("A36", "A572 Gr. 50"), benchmark_value="A36", affects_geometry=False),
                FieldSpec("t_plate_in", "Plate Thickness t_p (in.)", "t_p", "length", "in.", "float", "Plate & Weld", benchmark_value=0.375, validation={"gt": 0.0}),
                FieldSpec("d_p_in", "Plate Depth d_p (in.)", "d_p", "length", "in.", "float", "Plate & Weld", benchmark_value=9.0, validation={"gt": 0.0}),
                FieldSpec("a_in", "Weld-to-Bolt Distance a (in.)", "a", "length", "in.", "float", "Plate & Weld", benchmark_value=3.0, validation={"gt": 0.0}),
                FieldSpec("w_weld_in", "Fillet Weld Leg w (in.)", "w", "length", "in.", "float", "Plate & Weld", benchmark_value=0.25, validation={"gt": 0.0}),
                FieldSpec("F_EXX_ksi", "Weld Electrode F_EXX (ksi)", "F_EXX", "stress", "ksi", "float", "Plate & Weld", benchmark_value=70.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("n_bolts", "Number of Bolts n", "n", "count", None, "int", "Bolts", benchmark_value=3, validation={"ge": 1}),
                FieldSpec("d_b_in", "Bolt Diameter d_b (in.)", "d_b", "length", "in.", "float", "Bolts", benchmark_value=0.75, validation={"gt": 0.0}),
                FieldSpec("bolt_grade", "Bolt Grade", "Bolt", value_type="enum", section="Bolts", enum_options=("A325", "A490"), benchmark_value="A325", affects_geometry=False),
                FieldSpec("thread_condition", "Threads (N / X)", "Thread", value_type="enum", section="Bolts", enum_options=("N", "X"), benchmark_value="N", affects_geometry=False),
                FieldSpec("hole_type", "Hole Type", "Hole", value_type="enum", section="Bolts", enum_options=("STD", "OVS", "SSLT"), benchmark_value="STD", affects_geometry=False),
                FieldSpec("s_in", "Bolt Pitch s (in.)", "s", "length", "in.", "float", "Bolts", benchmark_value=3.0, validation={"gt": 0.0}),
                FieldSpec("L_ev_in", "Vertical Edge Distance L_ev (in.)", "L_ev", "length", "in.", "float", "Bolts", benchmark_value=1.5, validation={"gt": 0.0}),
                FieldSpec("L_eh_in", "Horizontal Edge Distance L_eh (in.)", "L_eh", "length", "in.", "float", "Bolts", benchmark_value=1.5, validation={"gt": 0.0}),
                FieldSpec("V_a_kips", "ASD Shear Demand V_a (kips)", "V_a", "force", "kips", "float", "Demand", benchmark_value=30.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("V_u_kips", "LRFD Shear Demand V_u (kips)", "V_u", "force", "kips", "float", "Demand", benchmark_value=45.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="aisc_bolt_bearing",
            aliases=("steel_bolted_connection",),
            category="Steel (AISC)",
            title="Bolted connection in shear",
            subtitle="AISC 360-22 Section J3",
            description="High-strength bolt shear, bearing, tearout, block shear, and combined tension-shear checks.",
            code_family="AISC_360",
            default_name="C-14 · Bolted lap splice",
            default_group="Level 2",
            preview_type="steel",
            calculation_callable=calculate_steel_bolted_connection,
            diagram_id="aisc_bolt_bearing",
            procedure_md="procedures/03_steel_design/steel_bolted_connection_aisc_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("d_b_in", "Bolt Diameter d_b (in.)", "d_b", "length", "in.", "float", "Fastener", benchmark_value=0.75, validation={"gt": 0.0}),
                FieldSpec("bolt_grade", "Bolt Grade", "Bolt", value_type="enum", section="Fastener", enum_options=("A325", "A490", "A307"), benchmark_value="A325", affects_geometry=False),
                FieldSpec("thread_condition", "Threads (N / X)", "Thread", value_type="enum", section="Fastener", enum_options=("N", "X"), benchmark_value="N", affects_geometry=False),
                FieldSpec("hole_type", "Hole Type", "Hole", value_type="enum", section="Fastener", enum_options=("STD", "OVS", "SSLT", "LSLT"), benchmark_value="STD", affects_geometry=False),
                FieldSpec("n_shear_planes", "Shear Planes", "Planes", "count", None, "int", "Geometry", benchmark_value=1, validation={"ge": 1}),
                FieldSpec("n_bolts_per_line", "Bolts per Line n_row", "n_row", "count", None, "int", "Geometry", benchmark_value=2, validation={"ge": 1}),
                FieldSpec("n_lines", "Bolt Gauge Lines n_lines", "n_lines", "count", None, "int", "Geometry", benchmark_value=2, validation={"ge": 1}),
                FieldSpec("s_in", "Bolt Pitch s (in.)", "s", "length", "in.", "float", "Geometry", benchmark_value=3.0, validation={"gt": 0.0}),
                FieldSpec("l_e_in", "End Distance l_e (in.)", "l_e", "length", "in.", "float", "Geometry", benchmark_value=1.5, validation={"gt": 0.0}),
                FieldSpec("g_in", "Gauge Spacing g (in.)", "g", "length", "in.", "float", "Geometry", benchmark_value=3.0, validation={"gt": 0.0}),
                FieldSpec("e_x_in", "Eccentricity e_x (in.)", "e_x", "length", "in.", "float", "Geometry", benchmark_value=0.0, validation={"ge": 0.0}),
                FieldSpec("plate_grade", "Plate Grade", "Grade", value_type="enum", section="Plate", enum_options=("A36", "A572 Gr. 50", "A992"), benchmark_value="A36", affects_geometry=False),
                FieldSpec("t_plate_in", "Plate Thickness t_p (in.)", "t_p", "length", "in.", "float", "Plate", benchmark_value=0.375, validation={"gt": 0.0}),
                FieldSpec("w_plate_in", "Plate Width w_p (in.)", "w_p", "length", "in.", "float", "Plate", benchmark_value=6.0, validation={"gt": 0.0}),
                FieldSpec("U_shear_lag", "Shear Lag Factor U", "U", "factor", None, "float", "Plate", benchmark_value=1.0, validation={"gt": 0.0, "le": 1.0}, affects_geometry=False),
                FieldSpec("deformation_considered", "Deformation at Bolt Hole Considered", "Def", value_type="bool", section="Plate", benchmark_value=True, affects_geometry=False),
                FieldSpec("V_a_kips", "ASD Shear Demand V_a (kips)", "V_a", "force", "kips", "float", "Demand", benchmark_value=45.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("T_bolt_a_kips", "ASD Bolt Tension T_a (kips)", "T_a", "force", "kips", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("V_u_kips", "LRFD Shear Demand V_u (kips)", "V_u", "force", "kips", "float", "Demand", benchmark_value=68.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("T_bolt_u_kips", "LRFD Bolt Tension T_u (kips)", "T_u", "force", "kips", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="aisc_welded_connection",
            aliases=("steel_welded_connection",),
            category="Steel (AISC)",
            title="Welded connection (fillet / CJP)",
            subtitle="AISC 360-22 Section J2",
            description="Fillet weld throat shear, directional strength increase, ICOR eccentricity, and base metal rupture.",
            code_family="AISC_360",
            default_name="C-15 · Welded bracket",
            default_group="Level 2",
            preview_type="steel",
            calculation_callable=calculate_steel_welded_connection,
            diagram_id="aisc_welded_connection",
            procedure_md="procedures/03_steel_design/steel_welded_connection_aisc_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("weld_config", "Weld Group Config", "Config", value_type="enum", section="Weld", enum_options=("C_shape", "Double_fillet", "Single_fillet"), benchmark_value="C_shape"),
                FieldSpec("w_leg_in", "Fillet Weld Leg w (in.)", "w", "length", "in.", "float", "Weld", benchmark_value=0.25, validation={"gt": 0.0}),
                FieldSpec("F_EXX_ksi", "Electrode Strength F_EXX (ksi)", "F_EXX", "stress", "ksi", "float", "Weld", benchmark_value=70.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("b_w_in", "Top/Bottom Weld Length b_w (in.)", "b_w", "length", "in.", "float", "Weld", benchmark_value=5.0, validation={"ge": 0.0}),
                FieldSpec("d_w_in", "Vertical Weld Depth d_w (in.)", "d_w", "length", "in.", "float", "Weld", benchmark_value=10.0, validation={"gt": 0.0}),
                FieldSpec("e_face_in", "Load Eccentricity e_face (in.)", "e_face", "length", "in.", "float", "Weld", benchmark_value=8.0, validation={"ge": 0.0}),
                FieldSpec("theta_load_deg", "Load Angle theta (deg)", "theta", "angle", "deg", "float", "Weld", benchmark_value=0.0, validation={"ge": 0.0, "le": 90.0}, affects_geometry=False),
                FieldSpec("plate_grade", "Plate Grade", "Grade", value_type="enum", section="Members", enum_options=("A36", "A572 Gr. 50", "A992"), benchmark_value="A36", affects_geometry=False),
                FieldSpec("t_plate_in", "Plate Thickness t_p (in.)", "t_p", "length", "in.", "float", "Members", benchmark_value=0.50, validation={"gt": 0.0}),
                FieldSpec("support_section", "Support Section", "Support", value_type="text", section="Members", benchmark_value="W12x65"),
                FieldSpec("support_grade", "Support Grade", "Grade", value_type="enum", section="Members", enum_options=("A992", "A36", "A572 Gr. 50", "A500 Gr. C"), benchmark_value="A992", affects_geometry=False),
                FieldSpec("V_a_kips", "ASD Shear Demand V_a (kips)", "V_a", "force", "kips", "float", "Demand", benchmark_value=24.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("V_u_kips", "LRFD Shear Demand V_u (kips)", "V_u", "force", "kips", "float", "Demand", benchmark_value=36.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="aisc_angle_connection",
            aliases=("steel_angle_connection",),
            category="Steel (AISC)",
            title="Single / double angle shear connection",
            subtitle="AISC 360-22 Part 10 & Sec. J4",
            description="Bolted clip angle shear, block shear, coped beam web buckling, and bolt eccentricity checks.",
            code_family="AISC_360",
            default_name="C-16 · Double-angle clip",
            default_group="Level 2",
            preview_type="steel",
            calculation_callable=calculate_steel_angle_connection,
            diagram_id="aisc_angle_connection",
            procedure_md="procedures/03_steel_design/steel_single_double_angle_shear_aisc_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("connection_type", "Angle Configuration", "Type", value_type="enum", section="Angles", enum_options=("Single Angle", "Double Angle"), benchmark_value="Single Angle"),
                FieldSpec("angle_section", "Angle Section", "Angle", value_type="text", section="Angles", benchmark_value="L4x3x3/8"),
                FieldSpec("angle_grade", "Angle Grade", "Grade", value_type="enum", section="Angles", enum_options=("A36", "A572 Gr. 50"), benchmark_value="A36", affects_geometry=False),
                FieldSpec("L_a_in", "Angle Length L_a (in.)", "L_a", "length", "in.", "float", "Angles", benchmark_value=5.5, validation={"gt": 0.0}),
                FieldSpec("beam_section", "Beam Section", "Beam", value_type="text", section="Members", benchmark_value="W12x14"),
                FieldSpec("beam_grade", "Beam Grade", "Grade", value_type="enum", section="Members", enum_options=("A992", "A36", "A572 Gr. 50"), benchmark_value="A992", affects_geometry=False),
                FieldSpec("support_section", "Support Section", "Support", value_type="text", section="Members", benchmark_value="W18x35"),
                FieldSpec("support_grade", "Support Grade", "Grade", value_type="enum", section="Members", enum_options=("A992", "A36", "A572 Gr. 50"), benchmark_value="A992", affects_geometry=False),
                FieldSpec("n_bolts", "Bolts per Line n", "n", "count", None, "int", "Bolts", benchmark_value=2, validation={"ge": 1}),
                FieldSpec("d_b_in", "Bolt Diameter d_b (in.)", "d_b", "length", "in.", "float", "Bolts", benchmark_value=0.75, validation={"gt": 0.0}),
                FieldSpec("bolt_grade", "Bolt Grade", "Bolt", value_type="enum", section="Bolts", enum_options=("A325", "A490"), benchmark_value="A325", affects_geometry=False),
                FieldSpec("s_in", "Bolt Pitch s (in.)", "s", "length", "in.", "float", "Bolts", benchmark_value=3.0, validation={"gt": 0.0}),
                FieldSpec("L_ev_in", "Vertical Edge L_ev (in.)", "L_ev", "length", "in.", "float", "Bolts", benchmark_value=1.25, validation={"gt": 0.0}),
                FieldSpec("L_eh_in", "Horizontal Edge L_eh (in.)", "L_eh", "length", "in.", "float", "Bolts", benchmark_value=1.5, validation={"gt": 0.0}),
                FieldSpec("g_sup_in", "Support Leg Gauge g_sup (in.)", "g_sup", "length", "in.", "float", "Bolts", benchmark_value=1.75, validation={"gt": 0.0}),
                FieldSpec("g_beam_in", "Beam Leg Gauge g_beam (in.)", "g_beam", "length", "in.", "float", "Bolts", benchmark_value=2.25, validation={"gt": 0.0}),
                FieldSpec("is_coped", "Top Flange Coped", "Coped", value_type="bool", section="Cope", benchmark_value=True),
                FieldSpec("c_cope_in", "Cope Length c (in.)", "c", "length", "in.", "float", "Cope", benchmark_value=4.0, validation={"ge": 0.0}),
                FieldSpec("dc_cope_in", "Cope Depth d_c (in.)", "d_c", "length", "in.", "float", "Cope", benchmark_value=1.5, validation={"ge": 0.0}),
                FieldSpec("V_a_kips", "ASD Shear Demand V_a (kips)", "V_a", "force", "kips", "float", "Demand", benchmark_value=12.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("V_u_kips", "LRFD Shear Demand V_u (kips)", "V_u", "force", "kips", "float", "Demand", benchmark_value=18.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="aisc_base_plate",
            aliases=("steel_base_plate",),
            category="Steel (AISC)",
            title="Column base plate & anchor rods",
            subtitle="AISC Design Guide 1 / AISC 360-22",
            description="Column base plate concrete bearing, plate bending, and anchor rod tension/shear.",
            code_family="AISC_360",
            default_name="C-17 · Column base plate",
            default_group="Foundations",
            preview_type="steel",
            calculation_callable=calculate_steel_base_plate,
            diagram_id="aisc_base_plate",
            procedure_md="procedures/03_steel_design/steel_column_base_plate_aisc_dg1_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("column_section", "Column Section", "Col", value_type="text", section="Column & Plate", benchmark_value="W10x49"),
                FieldSpec("plate_grade", "Base Plate Grade", "Grade", value_type="enum", section="Column & Plate", enum_options=("A36", "A572 Gr. 50"), benchmark_value="A36", affects_geometry=False),
                FieldSpec("B_in", "Plate Width B (in.)", "B", "length", "in.", "float", "Column & Plate", benchmark_value=16.0, validation={"gt": 0.0}),
                FieldSpec("N_in", "Plate Length N (in.)", "N", "length", "in.", "float", "Column & Plate", benchmark_value=16.0, validation={"gt": 0.0}),
                FieldSpec("t_p_in", "Plate Thickness t_p (in.)", "t_p", "length", "in.", "float", "Column & Plate", benchmark_value=1.625, validation={"gt": 0.0}),
                FieldSpec("fc_ksi", "Concrete Strength f'_c (ksi)", "f'_c", "stress", "ksi", "float", "Concrete Pedestal", benchmark_value=4.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("ratio_A2_A1", "Pedestal Area Ratio A_2/A_1", "A2/A1", "factor", None, "float", "Concrete Pedestal", benchmark_value=4.0, validation={"ge": 1.0}, affects_geometry=False),
                FieldSpec("d_a_in", "Anchor Rod Diameter d_a (in.)", "d_a", "length", "in.", "float", "Anchor Rods", benchmark_value=1.0, validation={"gt": 0.0}),
                FieldSpec("rod_grade", "Anchor Rod Grade", "Grade", value_type="enum", section="Anchor Rods", enum_options=("F1554 Gr. 36", "F1554 Gr. 55", "F1554 Gr. 105"), benchmark_value="F1554 Gr. 36", affects_geometry=False),
                FieldSpec("n_rods_total", "Total Anchor Rods", "n_tot", "count", None, "int", "Anchor Rods", benchmark_value=4, validation={"ge": 2}),
                FieldSpec("n_rods_tension", "Rods in Tension", "n_tens", "count", None, "int", "Anchor Rods", benchmark_value=2, validation={"ge": 1}),
                FieldSpec("f_dist_in", "Rod Distance from Centerline f (in.)", "f", "length", "in.", "float", "Anchor Rods", benchmark_value=6.25, validation={"gt": 0.0}),
                FieldSpec("mu_friction", "Friction Coefficient mu", "mu", "factor", None, "float", "Anchor Rods", benchmark_value=0.55, validation={"ge": 0.0}, affects_geometry=False),
                FieldSpec("has_grout_pad", "Grout Pad Present", "Grout", value_type="bool", section="Anchor Rods", benchmark_value=True, affects_geometry=False),
                FieldSpec("welded_washers", "Plate Washers Welded for Shear", "Washer", value_type="bool", section="Anchor Rods", benchmark_value=True, affects_geometry=False),
                FieldSpec("P_a_kips", "ASD Axial Compression P_a (kips)", "P_a", "force", "kips", "float", "Demand", benchmark_value=80.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("M_a_kip_in", "ASD Moment M_a (kip-in.)", "M_a", "moment", "kip-in.", "float", "Demand", benchmark_value=600.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("V_a_kips", "ASD Base Shear V_a (kips)", "V_a", "force", "kips", "float", "Demand", benchmark_value=8.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("P_u_kips", "LRFD Axial Compression P_u (kips)", "P_u", "force", "kips", "float", "Demand", benchmark_value=120.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("M_u_kip_in", "LRFD Moment M_u (kip-in.)", "M_u", "moment", "kip-in.", "float", "Demand", benchmark_value=900.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("V_u_kips", "LRFD Base Shear V_u (kips)", "V_u", "force", "kips", "float", "Demand", benchmark_value=12.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="aisc_hss_connection",
            aliases=("steel_hss_connection",),
            category="Steel (AISC)",
            title="HSS-to-HSS moment & shear connection",
            subtitle="AISC 360-22 Chapter K & H3",
            description="HSS wall plastification, punching shear, sidewall yielding, and branch interaction.",
            code_family="AISC_360",
            default_name="C-18 · HSS moment connection",
            default_group="Level 2",
            preview_type="steel",
            calculation_callable=calculate_steel_hss_connection,
            diagram_id="aisc_hss_connection",
            procedure_md="procedures/03_steel_design/steel_hss_to_hss_moment_shear_aisc_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("connection_config", "Connection Config (T / Y / Cross)", "Config", value_type="enum", section="Geometry", enum_options=("T", "Y", "Cross"), benchmark_value="T"),
                FieldSpec("chord_section", "Chord HSS Section", "Chord", value_type="text", section="Geometry", benchmark_value="HSS8x8x3/8"),
                FieldSpec("chord_grade", "Chord Steel Grade", "Grade", value_type="enum", section="Geometry", enum_options=("A500 Gr. C", "A500 Gr. B", "A1085"), benchmark_value="A500 Gr. C", affects_geometry=False),
                FieldSpec("branch_section", "Branch HSS Section", "Branch", value_type="text", section="Geometry", benchmark_value="HSS8x6x1/4"),
                FieldSpec("branch_grade", "Branch Steel Grade", "Grade", value_type="enum", section="Geometry", enum_options=("A500 Gr. C", "A500 Gr. B", "A1085"), benchmark_value="A500 Gr. C", affects_geometry=False),
                FieldSpec("theta_deg", "Branch Angle theta (deg)", "theta", "angle", "deg", "float", "Geometry", benchmark_value=90.0, validation={"gt": 0.0, "le": 90.0}),
                FieldSpec("chord_in_compression", "Chord in Compression", "Comp", value_type="bool", section="Geometry", benchmark_value=True, affects_geometry=False),
                FieldSpec("M_a_ip_kip_in", "ASD In-Plane Moment M_a,ip (kip-in.)", "M_ip", "moment", "kip-in.", "float", "Demand", benchmark_value=160.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("M_a_op_kip_in", "ASD Out-of-Plane Moment M_a,op (kip-in.)", "M_op", "moment", "kip-in.", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("P_a_branch_kips", "ASD Branch Axial P_a (kips)", "P_br", "force", "kips", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("V_a_branch_kips", "ASD Branch Shear V_a (kips)", "V_br", "force", "kips", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("P_ao_chord_kips", "ASD Chord Axial P_ao (kips)", "P_ch", "force", "kips", "float", "Demand", benchmark_value=66.7, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("M_u_ip_kip_in", "LRFD In-Plane Moment M_u,ip (kip-in.)", "M_ip", "moment", "kip-in.", "float", "Demand", benchmark_value=240.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("M_u_op_kip_in", "LRFD Out-of-Plane Moment M_u,op (kip-in.)", "M_op", "moment", "kip-in.", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("P_u_branch_kips", "LRFD Branch Axial P_u (kips)", "P_br", "force", "kips", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("V_u_branch_kips", "LRFD Branch Shear V_u (kips)", "V_br", "force", "kips", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("P_uo_chord_kips", "LRFD Chord Axial P_uo (kips)", "P_ch", "force", "kips", "float", "Demand", benchmark_value=100.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    # ==========================================================================
    # 4. CONCRETE / CMU (ACI 318-19 / TMS 402-22) — 3 Verified Modules (Day 16)
    # ==========================================================================
    registry.register(
        ModuleSpec(
            module_id="aci318_anchor_tension_shear",
            aliases=("concrete_anchorage_aci318",),
            category="Concrete / CMU (ACI / TMS)",
            title="Cast-in anchor in tension & shear",
            subtitle="ACI 318-19 Chapter 17 breakout & pullout",
            description="ACI 318 Chapter 17 steel strength, concrete breakout, pullout, pry-out, and interaction.",
            code_family="ACI_318",
            default_name="C-19 · Foundation anchor bolts",
            default_group="Foundations",
            preview_type="concrete",
            calculation_callable=calculate_concrete_anchorage,
            diagram_id="aci318_anchor_tension_shear",
            procedure_md="procedures/04_concrete_masonry_foundation/concrete_anchorage_aci318_ch17_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("anchor_type", "Anchor Type", "Type", value_type="enum", section="Anchor", enum_options=("Cast-in Headed", "Post-Installed Mechanical", "Post-Installed Adhesive"), benchmark_value="Cast-in Headed"),
                FieldSpec("rod_grade", "Anchor Rod Grade", "Grade", value_type="enum", section="Anchor", enum_options=("F1554 Gr. 36", "F1554 Gr. 55", "F1554 Gr. 105"), benchmark_value="F1554 Gr. 36", affects_geometry=False),
                FieldSpec("d_a_in", "Anchor Diameter d_a (in.)", "d_a", "length", "in.", "float", "Anchor", benchmark_value=0.625, validation={"gt": 0.0}),
                FieldSpec("h_ef_in", "Effective Embedment h_ef (in.)", "h_ef", "length", "in.", "float", "Anchor", benchmark_value=9.0, validation={"gt": 0.0}),
                FieldSpec("fc_psi", "Concrete Strength f'_c (psi)", "f'_c", "stress", "psi", "float", "Concrete", benchmark_value=3000.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("lambda_a", "Lightweight Factor lambda_a", "lambda_a", "factor", None, "float", "Concrete", benchmark_value=1.0, validation={"gt": 0.0, "le": 1.0}, affects_geometry=False),
                FieldSpec("cracked_concrete", "Cracked Concrete", "Cracked", value_type="bool", section="Concrete", benchmark_value=True, affects_geometry=False),
                FieldSpec("condition", "Supplemental Reinf. Condition (A / B)", "Cond", value_type="enum", section="Concrete", enum_options=("A", "B"), benchmark_value="B", affects_geometry=False),
                FieldSpec("sdc", "Seismic Design Category", "SDC", value_type="enum", section="Concrete", enum_options=("A", "B", "C", "D", "E", "F"), benchmark_value="D", affects_geometry=False),
                FieldSpec("n_x", "Anchors in X-Direction n_x", "n_x", "count", None, "int", "Group & Edges", benchmark_value=1, validation={"ge": 1}),
                FieldSpec("n_y", "Anchors in Y-Direction n_y", "n_y", "count", None, "int", "Group & Edges", benchmark_value=1, validation={"ge": 1}),
                FieldSpec("s_x_in", "X Spacing s_x (in.)", "s_x", "length", "in.", "float", "Group & Edges", benchmark_value=0.0, validation={"ge": 0.0}),
                FieldSpec("s_y_in", "Y Spacing s_y (in.)", "s_y", "length", "in.", "float", "Group & Edges", benchmark_value=0.0, validation={"ge": 0.0}),
                FieldSpec("c_a1_in", "Edge Distance c_a1 (in.)", "c_a1", "length", "in.", "float", "Group & Edges", benchmark_value=12.0, validation={"gt": 0.0}),
                FieldSpec("c_a2_in", "Perpendicular Edge c_a2 (in.)", "c_a2", "length", "in.", "float", "Group & Edges", benchmark_value=18.0, validation={"gt": 0.0}),
                FieldSpec("h_a_in", "Member Thickness h_a (in.)", "h_a", "length", "in.", "float", "Group & Edges", benchmark_value=18.0, validation={"gt": 0.0}),
                FieldSpec("N_asd_lbs", "ASD Tension Demand N_asd (lbs)", "N_asd", "force", "lbs", "float", "Demand", benchmark_value=3150.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("V_asd_lbs", "ASD Shear Demand V_asd (lbs)", "V_asd", "force", "lbs", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("N_ua_lbs", "LRFD Tension Demand N_ua (lbs)", "N_ua", "force", "lbs", "float", "Demand", benchmark_value=4500.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("V_ua_lbs", "LRFD Shear Demand V_ua (lbs)", "V_ua", "force", "lbs", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="tms402_cmu_anchorage",
            aliases=("cmu_anchorage_tms402",),
            category="Concrete / CMU (ACI / TMS)",
            title="CMU anchor bolt breakout",
            subtitle="TMS 402-22 Section 9.1.6",
            description="Grouted CMU anchor bolt tension/shear breakout, crushing, pryout, and interaction checks.",
            code_family="TMS_402",
            default_name="C-20 · CMU wall anchor",
            default_group="Level 2",
            preview_type="concrete",
            calculation_callable=calculate_cmu_anchorage,
            diagram_id="tms402_cmu_anchorage",
            procedure_md="procedures/04_concrete_masonry_foundation/cmu_masonry_anchorage_out_of_plane_breakout_tms402_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("cmu_nominal_in", "Nominal CMU Wall Thickness (in.)", "t_nom", "length", "in.", "int", "CMU Wall", benchmark_value=8, validation={"ge": 6}),
                FieldSpec("fm_psi", "Masonry Strength f'_m (psi)", "f'_m", "stress", "psi", "float", "CMU Wall", benchmark_value=2000.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("is_grouted", "Solidly Grouted Cell", "Grouted", value_type="bool", section="CMU Wall", benchmark_value=True, affects_geometry=False),
                FieldSpec("bolt_type", "Anchor Type", "Type", value_type="enum", section="Anchor Bolt", enum_options=("Headed", "Bent-Bar"), benchmark_value="Headed"),
                FieldSpec("rod_grade", "Anchor Rod Grade", "Grade", value_type="enum", section="Anchor Bolt", enum_options=("F1554 Gr. 36", "F1554 Gr. 55"), benchmark_value="F1554 Gr. 36", affects_geometry=False),
                FieldSpec("d_b_in", "Bolt Diameter d_b (in.)", "d_b", "length", "in.", "float", "Anchor Bolt", benchmark_value=0.625, validation={"gt": 0.0}),
                FieldSpec("l_b_in", "Effective Embedment l_b (in.)", "l_b", "length", "in.", "float", "Anchor Bolt", benchmark_value=6.0, validation={"gt": 0.0}),
                FieldSpec("l_be_shear_in", "Shear Edge Distance l_be (in.)", "l_be", "length", "in.", "float", "Anchor Bolt", benchmark_value=12.0, validation={"gt": 0.0}),
                FieldSpec("edge_tension_in", "Tension Edge Distance (in.)", "c_e", "length", "in.", "float", "Anchor Bolt", benchmark_value=12.0, validation={"gt": 0.0}),
                FieldSpec("n_anchors", "Number of Anchors", "n", "count", None, "int", "Anchor Bolt", benchmark_value=1, validation={"ge": 1}),
                FieldSpec("s_anchors_in", "Anchor Spacing s (in.)", "s", "length", "in.", "float", "Anchor Bolt", benchmark_value=16.0, validation={"ge": 0.0}),
                FieldSpec("b_af_lbs", "ASD Tension Demand b_af (lbs)", "b_af", "force", "lbs", "float", "Demand", benchmark_value=2500.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("b_vf_lbs", "ASD Shear Demand b_vf (lbs)", "b_vf", "force", "lbs", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("b_af_sd_lbs", "LRFD/SD Tension Demand b_af (lbs)", "b_af,u", "force", "lbs", "float", "Demand", benchmark_value=3571.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("b_vf_sd_lbs", "LRFD/SD Shear Demand b_vf (lbs)", "b_vf,u", "force", "lbs", "float", "Demand", benchmark_value=0.0, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    registry.register(
        ModuleSpec(
            module_id="tms402_embedded_post",
            aliases=("embedded_steel_post",),
            category="Concrete / CMU (ACI / TMS)",
            title="Embedded steel post in concrete / CMU",
            subtitle="2024 IBC Sec. 1807.3 & TMS 402-22",
            description="Cantilever steel post embedded in concrete pier/CMU footing with discrete rebar couple or soil bearing.",
            code_family="TMS_402",
            default_name="C-21 · Embedded steel post",
            default_group="Foundations",
            preview_type="concrete",
            calculation_callable=calculate_embedded_steel_post,
            diagram_id="tms402_embedded_post",
            procedure_md="procedures/04_concrete_masonry_foundation/cantilever_steel_post_embedded_concrete_cmu_workflow.md",
            maturity=ModuleMaturity.VERIFIED,
            fields=(
                FieldSpec("transfer_path", "Transfer Path", "Path", value_type="enum", section="Embedment", enum_options=("discrete_rebar", "soil_bearing"), benchmark_value="discrete_rebar"),
                FieldSpec("medium", "Embedment Medium", "Medium", value_type="enum", section="Embedment", enum_options=("CMU", "Concrete"), benchmark_value="CMU"),
                FieldSpec("cmu_nominal_in", "Nominal Wall Thickness (in.)", "t_nom", "length", "in.", "int", "Embedment", benchmark_value=8, validation={"ge": 6}),
                FieldSpec("fm_psi", "Masonry/Concrete Strength f'_m (psi)", "f'_m", "stress", "psi", "float", "Embedment", benchmark_value=2000.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("post_section", "Post Steel Section", "Post", value_type="text", section="Post", benchmark_value="HSS4x4x1/4"),
                FieldSpec("post_grade", "Post Steel Grade", "Grade", value_type="enum", section="Post", enum_options=("A500 Gr. C", "A500 Gr. B", "A992", "A36"), benchmark_value="A500 Gr. C", affects_geometry=False),
                FieldSpec("H_post_in", "Cantilever Height H_post (in.)", "H_post", "length", "in.", "float", "Post", benchmark_value=48.0, validation={"gt": 0.0}),
                FieldSpec("L_e_in", "Embedment Length L_e (in.)", "L_e", "length", "in.", "float", "Post", benchmark_value=24.0, validation={"gt": 0.0}),
                FieldSpec("a_0_in", "Grout Offset a_0 (in.)", "a_0", "length", "in.", "float", "Post", benchmark_value=2.0, validation={"ge": 0.0}),
                FieldSpec("d_top_in", "Top Cover d_top (in.)", "d_top", "length", "in.", "float", "Rebar & Weld", benchmark_value=4.0, validation={"gt": 0.0}),
                FieldSpec("z_b_in", "Couple Lever Arm z_b (in.)", "z_b", "length", "in.", "float", "Rebar & Weld", benchmark_value=16.0, validation={"gt": 0.0}),
                FieldSpec("rebar_size", "U-Bar Size", "Bar", value_type="enum", section="Rebar & Weld", enum_options=("#3", "#4", "#5", "#6"), benchmark_value="#4", affects_geometry=False),
                FieldSpec("n_ubar_legs", "Number of U-Bar Legs", "n_legs", "count", None, "int", "Rebar & Weld", benchmark_value=2, validation={"ge": 1}),
                FieldSpec("L_weld_leg_in", "Weld Length per Leg L_w (in.)", "L_w", "length", "in.", "float", "Rebar & Weld", benchmark_value=2.5, validation={"gt": 0.0}),
                FieldSpec("n_weld_lines", "Weld Lines per Leg", "n_w", "count", None, "int", "Rebar & Weld", benchmark_value=2, validation={"ge": 1}),
                FieldSpec("F_EXX_ksi", "Electrode F_EXX (ksi)", "F_EXX", "stress", "ksi", "float", "Rebar & Weld", benchmark_value=70.0, validation={"gt": 0.0}, affects_geometry=False),
                FieldSpec("b_bb_in", "Bond Beam Depth b_bb (in.)", "b_bb", "length", "in.", "float", "Rebar & Weld", benchmark_value=16.0, validation={"gt": 0.0}),
                FieldSpec("V_a_kips", "ASD Lateral Demand V_a (kips)", "V_a", "force", "kips", "float", "Demand", benchmark_value=1.20, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("P_a_kips", "ASD Axial Demand P_a (kips)", "P_a", "force", "kips", "float", "Demand", benchmark_value=1.50, validation={"ge": 0.0}, visible_if="design_method == ASD", affects_geometry=False),
                FieldSpec("V_u_kips", "LRFD Lateral Demand V_u (kips)", "V_u", "force", "kips", "float", "Demand", benchmark_value=1.92, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
                FieldSpec("P_u_kips", "LRFD Axial Demand P_u (kips)", "P_u", "force", "kips", "float", "Demand", benchmark_value=2.40, validation={"ge": 0.0}, visible_if="design_method == LRFD", affects_geometry=False),
            ),
        )
    )

    return registry


_DEFAULT_REGISTRY: Optional[ModuleRegistry] = None


def get_module_registry() -> ModuleRegistry:
    """Return the shared singleton ModuleRegistry instance."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = build_default_registry()
    return _DEFAULT_REGISTRY
