# System & Plan Audit Report + Connection-Focused KB Gap Analysis (Post-Day 14)

- **Audit Date**: 2026-11-16 (Revised — Connection-Design Focus)
- **Scope**: Full read-only review of project plan (`proposed.md`, `state_summary.txt`), repository structure, `config/reference_manifest.json`, calculation engine (`core/`), services (`app/services/`), exporters (`exporters/`), GUI (`gui/`), test suite (`tests/`), and Knowledge Base (`database/` & `procedures/`) with V1 priority on **Connection Design**.
- **Important Note**: No source code or calculation data files were modified during this audit.

---

## PART 1: SYSTEM & PLAN ERRORS / RISKS SUMMARY

### 1.1 Plan, Documentation & Reference Integrity
1. **Plan Alignment (`proposed.md` & `state_summary.txt`) — PASS**:
   - `proposed.md` (SAD v1.0) has only Section `2.1 Existing Project Status` updated, synchronized with `state_summary.txt` through Day 14.
   - Roadmap for Days 15–20 (Steel Connections, Concrete & CMU Anchorage, CloudSyncService, Full Exporters, 5-Level QA & Windows Packaging) remains intact.
2. **Python Syntax Check — PASS**:
   - All **58 `.py` files** in the repository parsed cleanly via `ast.parse` with **0 syntax errors**.
3. **SHA-256 Reference Manifest (`config/reference_manifest.json`) — PARTIAL LOCAL CACHE**:
   - Total manifest entries: **92** (66 CSVs + 26 Markdown procedures).
   - Locally present on VM: **63/92 files**, all **100% SHA-256 verified (0 mismatches)**.
   - Not yet downloaded to local VM: **29/92 files** (belonging to Day 15 Steel, Day 16 Concrete/Masonry, and Plan Check templates stored on Google Drive). *Risk*: Running a full `KnowledgeBaseService.verify_manifest()` offline on a fresh cache without downloading those 29 files will report missing files until Day 15–16/CloudSyncService populates them.

---

### 1.2 Calculation Engine & Exporters (`core/`, `app/services/`, `exporters/`)
All **10 registered calculation modules** (5 C&C + 5 Wood) executed without runtime exceptions across both **ASD and LRFD** (20/20 runs), and `ReportService` exported `.xlsx` and `.pdf` for all 10/10 modules. However, the following **3 concrete issues/risks** were identified:

1. **[HIGH] `ExcelBuilder` (`exporters/excel_builder.py:306`) silently skips multi-header CSVs in the `Database` tab**:
   - `excel_builder.py` calls `df = kb.get_table(ref_file)` (which uses `pd.read_csv()`) inside a `try ... except Exception: continue` block.
   - NDS CSV files that have a 1-column title banner on row 1 (e.g., `NDS-2024_Table_12.3.3.csv`, `NDS-2024_Table_12.2B.csv`) raise `pandas.errors.ParserError` and are silently omitted from the exported Excel `Database` tab (even though they still appear in `Source_Audit`).
   - *Recommended Fix*: Add a resilient CSV reader helper (using Python's `csv.reader` or skipping banner rows) in `KnowledgeBaseService` / `ExcelBuilder` so all referenced CSVs render cleanly in the `Database` tab.

2. **[MEDIUM] Hardcoded Special-Case for `HUS210-2` in `core/nds/connections/simpson_connectors.py`**:
   - Row 34 of `Simpson_C-C-2026_Joist_Hangers_LUS_HU_HUS_HUCQ_HGUS.csv` stores `HUS210-2` with the reduced nailing schedule `(8) 0.162"x3-1/2"` (`P_100 = 2,175 lbs`), whereas the benchmark in `procedures/02_wood_design/wood_joist_hanger_hurricane_tie_simpson_workflow.md` uses the full nailing schedule `(30) 0.162"x3-1/2"` (`P_100 = 5,115 lbs`).
   - `lookup_simpson_joist_hanger()` currently contains a hardcoded branch (`if target == "HUS210-2" and not is_spf: return { ... 5115.0 ... }`) instead of reading both nailing schedules from the CSV.
   - *Recommended Fix*: Add the full-nailing `HUS210-2` row (or distinguish nailing option in `Model No.` / `Notes`) directly in the CSV and update `reference_manifest.json` SHA-256, then remove the hardcoded branch.

3. **[LOW] Default Empty Inputs `{}` Return `FAIL` for 2 C&C Modules**:
   - Running `CalculationService.run_calculation(mod, {}, DesignMethod.ASD/LRFD)` returns `FAIL` for:
     - `asce7_roof_overhang` (`DCR = 1.079` ASD, `1.222` LRFD)
     - `asce7_awning_canopy` (`DCR = 1.910` ASD, `1.927` LRFD)
   - While mathematically valid for the fallback parameters, opening these templates on the UI with default values will immediately display a red `FAIL` badge.

---

### 1.3 GUI & `module_id` Wiring (`gui/` vs `app/services/`)
1. **[HIGH] `module_id` Mismatch Between `AddCalculationDialog` and `WoodCalculationWorkspace`**:
   - `gui/dialogs/add_calculation_dialog.py` defines 3 separate Wood fastener templates:
     - `wood_nail_lateral`
     - `wood_screw_withdrawal`
     - `wood_combined_lateral_withdrawal`
   - All 3 are mapped in `CalculationService`, **but `gui/widgets/wood_workspace.py` only defines 5 `MODULE_CONFIGS`**:
     - `wood_bolt_lateral`, `wood_fastener_nds`, `wood_shear_wall_sdpws`, `wood_diaphragm_sdpws`, `wood_simpson_hanger_tie`.
   - Conversely, `wood_fastener_nds` is in `WoodCalculationWorkspace` and `CalculationService`, but is **missing** from `AddCalculationDialog`.
   - Additionally, `CalculationService` registers `wood_bolt_nds` as an alias for `calculate_wood_bolt_connection`, but omits it from `list_supported_modules()`.
   - *Recommended Fix*: Align `module_id`s across `AddCalculationDialog`, `WoodCalculationWorkspace.set_module_type()`, and `CalculationService` (e.g., map the 3 dialog fastener IDs to `wood_fastener_nds` with pre-selected `fastener_type`, or unify the template list), and wire `MainWindow._on_add_calculation_clicked()` to call `set_module_type(data["template_id"])` on the target workspace.

2. **[INFO] Placeholder Pages in `gui/main_window.py`**:
   - `page_dashboard`, `page_projects`, `page_steel`, `page_reports`, and `page_settings` are currently placeholder widgets, which is expected until Days 15–20.

---

### 1.4 Test Suite (`tests/`) & Runtime Environment
1. **[HIGH] Missing `pytest` and `PySide6` in Current VM Environment**:
   - `pytest` and `PySide6` are not installed in the current sandbox Python environment (`ModuleNotFoundError`).
   - **7 out of 8 test files** (`test_cc_vertical_slice.py`, `test_gui_workspace.py`, `test_kb_service.py`, `test_load_combinations.py`, `test_storage.py`, `test_units.py`, `test_validation.py` — 61 tests total) `import pytest` at top level and therefore fail to import under `python3 -m unittest discover` (`7 ERRORs`).
   - Only `tests/test_wood_vertical_slice.py` (converted to `unittest`) ran and passed **8/8 tests**, but its PySide6 UI check fell back to `except ImportError` (performing `ast.parse` syntax verification only, not live widget instantiation).
   - *Risk*: Automated CI/offline regression verification cannot run all 69 tests in environments lacking `pytest` unless tests support `unittest` or `pytest` is bundled in the target dev environment.

---

## PART 2: CONNECTION-FOCUSED KNOWLEDGE BASE GAP ANALYSIS

Since V1 prioritizes **Connection Design** across Wood, Steel, Concrete/CMU Anchorage, and C&C Sub-Assembly interfaces, only the most directly applicable connection procedures and database CSVs are recommended below.

### 2.1 Existing Connection CSVs Missing a Dedicated Procedure (Immediate Quick Wins)
1. **`procedures/02_wood_design/wood_post_base_cap_and_column_bearing_workflow.md`**
   - *Existing CSV*: `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Post_Bases_and_Caps_ABU_ABA_CBSQ_MPBZ_CC_BC.csv`
   - *Connection Scope*: Wood post-to-concrete base (`ABU`/`ABA`/`CBSQ`/`MPBZ`) and beam-to-post cap (`CC`/`BC`) uplift, download, lateral shear, and wood bearing perpendicular to grain ($F_{c\perp}$).
2. **`procedures/01_loads_and_seismic/nonstructural_wall_and_equipment_anchorage_asce7_workflow.md`**
   - *Existing CSV*: `database/asce_7/v7_22/ASCE7-22_Section_12.11.2_Wall_Anchorage_and_Table_13.6-1_Equipment.csv`
   - *Connection Scope*: Out-of-plane concrete/masonry wall-to-diaphragm anchorage connection force ($F_p$) and nonstructural equipment anchor demand per ASCE 7-22 Sec. 12.11.2 & Ch. 13.

---

### 2.2 Recommended New Connection Database CSVs
| Priority | Proposed CSV Path | Governing Code / Table | Connection Design Purpose |
| :--- | :--- | :--- | :--- |
| **High** | `database/manufacturer_catalogs/simpson_strong_tie/Simpson_C-C-2026_Joist_Hangers_...` (Add rows) | Simpson C-C-2026 | Add full-nailing `(30) 0.162"x3.5"` row for `HUS210-2` (and other dual-nailing hangers) so `simpson_connectors.py` needs zero hardcoded overrides. |
| **High** | `database/aisc_360/v16th_ed/ch_j_connections/AISC360-22_Table_J3.1_J3.6_J3.7_Slip_Critical_and_Combined.csv` | AISC 360-22 Tables J3.1, J3.6 & Sec. J3.7–J3.8 | Minimum bolt pretension $T_b$, slip-critical capacity ($R_n = \mu D_u h_f T_b n_s$), and combined tension-shear $F'_{nt}$ for Day 15 Steel connections. |
| **High** | `database/aci_318_tms_402/aci_318_19/ACI318-19_Table_17.5.2_Cracked_Uncracked_and_Seismic_Factors.csv` | ACI 318-19 Ch. 17 | Concrete breakout factors $\psi_{c,N}, \psi_{c,P}, \psi_{c,V}$ (cracked vs. uncracked) and seismic $\Omega_{0p}$ / $0.75$ ductility factors for Day 16 Anchorage. |
| **High** | `database/aci_318_tms_402/aci_318_19/ACI318-19_Table_25.4.2.3_Rebar_Development_and_Hook_Lengths.csv` | ACI 318-19 Sec. 25.4.2, 25.4.3 & 25.5 | Rebar straight development ($l_d$), 90°/180° hook ($l_{dh}$), and lap splice lengths for welded rebar dowels on embedded steel posts & supplementary anchor reinforcement. |
| **Medium** | `database/aisc_360/v16th_ed/ch_j_connections/AISC_Manual_16th_Table_10-1_10-2_Bolted_Double_Angle_and_WT.csv` | AISC Steel Construction Manual 16th Ed. Part 10 | Pre-tabulated bolted/welded double-angle & WT shear connection capacities complementing `Part10_Shear_Tab_and_Single_Angle_Design.csv`. |
| **Medium** | `database/nds_wood/v2024/NDS-2024_Table_12.5.1F_12.5.1G_Fastener_Geometry_Limits.csv` | NDS 2024 Sec. 12.5 & Table 12.5.1A–G | Unified minimum end, edge, and spacing limits ($4D, 1.5D, 7D$) for bolts, lag screws, and wood screws to validate $C_\Delta$ geometry checks. |

---

### 2.3 Recommended New Connection Procedures (`procedures/`)
1. **`procedures/03_steel_design/steel_extended_moment_end_plate_aisc_dg4_workflow.md`**
   - *Scope*: 4-bolt unstiffened/stiffened and 8-bolt stiffened extended moment end-plate beam-to-column connections (bolt tension, prying action, end-plate bending, column flange stiffener checks) per AISC DG4 & AISC 360-22 Ch. J.
2. **`procedures/03_steel_design/steel_gusset_plate_brace_connection_aisc_workflow.md`**
   - *Scope*: Diagonal brace-to-gusset and gusset-to-beam/column connections (Whitmore effective width, block shear $J4.3$, Thornton/Uniform Force Method interface forces).
3. **`procedures/04_concrete_masonry_foundation/wood_steel_ledger_to_concrete_cmu_anchorage_workflow.md`**
   - *Scope*: Continuous wood or steel ledger anchored to concrete/CMU wall for gravity shear + ASCE 7 Sec. 12.11.2 out-of-plane diaphragm anchorage (bridges Day 14 Wood/Steel with Day 16 ACI 318/TMS 402 anchorage).
