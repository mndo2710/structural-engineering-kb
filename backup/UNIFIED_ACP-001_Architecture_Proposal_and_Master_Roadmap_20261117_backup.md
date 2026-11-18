# UNIFIED ACP-001 — Master Architecture Change Proposal & End-to-End Execution Roadmap
## Clean Architecture Contracts, Project-Scoped Workspaces, Structured Calculation Trace, and V1.0 Completion Plan (Post-Day 14 to 100% Release)

**Project:** `structural-engineering-kb` (Standalone US Structural Engineering Calculation Application)  
**Authoritative Baseline:** [`proposed.md` (SAD v1.0)](https://drive.google.com/file/d/1r0tQBUQo9xMdINqxKfUkCDeDsG5J0sFE/view?usp=drivesdk), [`rules.md`](https://drive.google.com/file/d/1teDErExvnqyEUHd5YJuz2I2H5aPxJbjd/view?usp=drivesdk), and [`state_summary.txt`](https://drive.google.com/file/d/1TvcAYN6E9xItjiWToTFzN8UdZkv19L3m/view?usp=drivesdk)  
**Synthesized Sources:** [`CLAUDE_ACP-001_architecture_change_proposal.md`](https://drive.google.com/file/d/17hafIk3nW6gdgudzkLvrwT1hkJ1VmQRo/view?usp=drivesdk) and [`GPT_Structural_Calculation_App_Architecture_Review_Proposal.md`](https://drive.google.com/file/d/1LktRaHRreSKrgaRL_1vwqM6priy2Inib/view?usp=drivesdk) in [`proposal/`](https://drive.google.com/drive/folders/1VggHm-vqTQvyVcVQ0uoSc44utEy4x_7V)  
**Date:** November 17, 2026  
**Status:** DRAFT FOR USER APPROVAL — Do not modify locked SAD sections or execute code refactoring until approved in writing (see Section 6).  
**Target Audience:** Primary Agent (Tech Lead), `desktop-app`, `calculation-engine`, `cloud-data`, `qa-verifier`

## 0. Governance, Agent Protocol, and Current Project Baseline

### 0.1 Mandatory Pre-Work Protocol
1. Read [`AGENTS.md`](https://github.com/mndo2710/structural-engineering-kb/blob/main/AGENTS.md), [`rules.md`](https://drive.google.com/file/d/1teDErExvnqyEUHd5YJuz2I2H5aPxJbjd/view?usp=drivesdk), [`proposed.md`](https://drive.google.com/file/d/1r0tQBUQo9xMdINqxKfUkCDeDsG5J0sFE/view?usp=drivesdk), and [`state_summary.txt`](https://drive.google.com/file/d/1TvcAYN6E9xItjiWToTFzN8UdZkv19L3m/view?usp=drivesdk) before starting any work package.
2. Preserve all protected Knowledge Base assets (`database/` — 66 verified CSVs; `procedures/` — 26 verified 7-section Markdown procedures; `config/reference_manifest.json` — 92 SHA-256 hashes). Never alter, move, or reformat CSV/Markdown engineering content without explicit user instruction and the mandatory 5-step verification protocol.
3. Follow Rule 2 strictly: 100% US Structural Engineering English and US Customary units (`in.`, `ft`, `lbs`, `kips`, `psi`, `ksi`, `psf`, `plf`, `lb-in.`, `lb-ft`, `kip-in.`, `kip-ft`) across all code, schemas, UI labels, and exported deliverables; strict Dual ASD and LRFD separation (never mix ASD safety factors $\Omega$ with LRFD resistance factors $\phi$).
4. Follow Rule 3 strictly: upload all `.csv`, `.md`, `.py`, `.json`, and `.txt` files to Google Drive as raw binary/text streams (`mime_type="application/octet-stream"`); back up any superseded file with a `_backup` suffix into `backup/` (`168YNvao8onqXfHC-cjcSCWZz0sPnHz7h`) before replacement; update `state_summary.txt` and Section `2.1` of `proposed.md` every 3 turns or at milestone completion.
5. Never invent engineering data, code provisions, or silent numerical fallbacks. Any missing required user input or unsupported condition must return `INCOMPLETE` or `REQUIRES REVIEW`, never `PASS`.

### 0.2 Current Project Progress Baseline (~70% Complete — Post-Day 14)

| Milestone Phase | Scope & Deliverables | Status | Verification Evidence |
|---|---|---|---|
| **Phase 1 (Days 1–10)** | Engineering Knowledge Base: 66 verified CSV lookup tables (`database/`) and 26 verified 7-section Markdown calculation procedures (`procedures/`) across ASCE 7-22, IBC/CBC, NDS 2024, SDPWS 2021, AISC 360-22, ACI 318-19, TMS 402-22, and Simpson Strong-Tie catalogs | **100% Completed** | 92/92 SHA-256 hashes verified in `config/reference_manifest.json` |
| **Day 11 (Phase 2 Part 1)** | Core common contracts (`calculation_result.py`, `units.py`, `load_combinations.py`, `validation.py`, `exceptions.py`) and `KnowledgeBaseService` with `utf-8-sig` caching and SHA-256 audit | **100% Completed** | 92/92 manifest integrity audit passing |
| **Day 12 (Phase 2 Part 2)** | SQLite `ProjectRepository` (8 tables), `ProjectService`, `HistoryService`, PySide6 `MainWindow`, `BaseCalculationWorkspace`, and `AddCalculationDialog` | **100% Completed** | Repository and service unit tests passing |
| **Day 13 (C&C Vertical Slice)** | `core/asce7/wind/` (velocity pressure, C&C pressure, parapet, overhang, awning, trellis, guardrail) and `core/asce7/seismic/seismic_loads.py`, `CalculationService`, `ReportService`, `exporters/excel_builder.py`, `pdf_builder.py`, `audit_logger.py`, and `gui/widgets/cc_workspace.py` | **100% Completed** | 61/61 unit, benchmark, regression, and E2E tests (`tests/test_cc_vertical_slice.py`) |
| **Day 14 (Wood Vertical Slice)** | `core/nds/fasteners/` (`bolts.py` incl. Appendix E tear-out, `nails_screws.py`), `core/nds/lateral/` (`shear_walls.py`, `diaphragms.py`), `core/nds/connections/simpson_connectors.py`, and `gui/widgets/wood_workspace.py` | **100% Completed** | 8/8 multi-level benchmark/E2E suites (`tests/test_wood_vertical_slice.py`), 69/69 total tests passing; synced to GitHub `origin/main` |
| **Pre-Day 15 Prep (2026-11-17)** | Upgraded `steel_hss_to_hss_moment_shear_aisc_workflow.md` and `steel_shear_tab_connection_aisc_workflow.md` (with Table K1.2 HSS wall slenderness & punching shear); standardized Rule 5 4-Stage Load-Path Verification Order in `rules.md` | **100% Completed** | 92/92 manifest SHA-256 hashes refreshed and verified |
| **Remaining Roadmap (Days 15–20)** | Architecture Stabilization + Day 15 (AISC 360 Steel), Day 16 (ACI 318 / TMS 402 Anchorage), Day 17 (Cloud Sync), Day 18 (Full Exporters), Day 19 (5-Level QA & PyInstaller `.exe`), Day 20 (UAT & V1.0 Release) | **Pending (30%)** | Governed by Section 4 of this unified plan |

## 1. Comparative Synthesis of Claude (ACP-001) and GPT Architecture Reviews

Both [`CLAUDE_ACP-001_architecture_change_proposal.md`](https://drive.google.com/file/d/17hafIk3nW6gdgudzkLvrwT1hkJ1VmQRo/view?usp=drivesdk) and [`GPT_Structural_Calculation_App_Architecture_Review_Proposal.md`](https://drive.google.com/file/d/1LktRaHRreSKrgaRL_1vwqM6priy2Inib/view?usp=drivesdk) independently reached the same overarching conclusion: **the existing Python + PySide6 + deterministic `core/` + SQLite + CSV/Markdown KB foundation is sound and must not be rewritten from scratch, but internal data contracts, layer boundaries, and multi-item workspace state management must be refactored before scaling to Steel (Day 15) and Concrete/CMU (Day 16).**

### 1.1 Key Synergies and Reconciled Architectural Decisions

| Architectural Dimension | Claude (`ACP-001`) Contribution | GPT (`Architecture Review`) Contribution | Unified Synthesis Decision (`UNIFIED ACP-001`) |
|---|---|---|---|
| **1. Dependency Direction (`gui` <-> `app` <-> `core`)** | Identified `gui/` importing `core.common.calculation_result` directly (`F-10`); proposed `app/models/` DTOs and `WorkspaceController`. | Identified **bidirectional** violation (`§4.1`): `gui/` imports `core/`, AND `core/asce7/` & `core/nds/` import concrete `KnowledgeBaseService` from `app/services/`. | **Enforce Inward Clean Architecture**: (a) Define `ReferenceDataPort` (`Protocol` in `core/common/ports.py`) implemented by `KnowledgeBaseService`; (b) Expose DTOs/ViewModels in `app/models/` so `gui/` never imports `core/`. |
| **2. Multi-Item Project Tree & Persistence** | Concrete SQLite Schema v2 (`PRAGMA user_version = 2`): `calculation_groups`, item `sort_order`, monotonic `item_number`, `draft_inputs_json`, `last_dcr`, `last_input_hash`, `is_deleted`, and `project_settings`. | Explicit use-case separation (`CreateCalculation`, `RunCalculation`, `SaveCalculationRevision`, `LoadCalculationRevision`) plus per-revision `ReferenceSnapshot` (SHA-256 hashes + software version) (`§4.5`, `§4.7`). | **Combine Both in Schema v2**: Implement Claude's Schema v2 tables/columns for grouping, drag-to-reorder, and draft autosave, AND add GPT's `reference_snapshot_json` and `engine_version` columns to `calculation_revisions`. |
| **3. Calculation Trace & Math Rendering (Panel 3)** | Concrete `CalcStep` + `RefSpec` dataclasses with restricted LaTeX `math_markup` grammar and 3-target renderers (`KaTeX` in Qt, `ReportLab` in PDF, `openpyxl` in XLSX) (`§3.6`). | Structured `CalculationStep` with typed `Quantity(value, unit)`, non-DCR check support (geometry/detailing limits), and offline bundled renderer (`§4.2`, `§4.5`, `§6.3`). | **Unified `CalcStep` Contract**: Combine Claude's 4-stage `CalcStep` + `math_markup` multi-target renderers with GPT's `Quantity(value, unit)` operands and non-DCR acceptance criteria (`PASS`/`FAIL` on geometry/spacing limits without artificial DCRs). Use vendored offline KaTeX with `QTextEdit` rich-text fallback. |
| **4. Workspace Host vs. Existing Custom Diagrams** | Single `WorkspaceHost` + schema-driven `InputForm` + `DiagramSpec` + `DiagramCanvas`, retiring `cc_workspace.py` and `wood_workspace.py` after parity (`§3.7–3.8`). | Preserve the verified C&C and Wood custom schematic `QPainter` logic while feeding them a typed `VisualizationModel` via `VisualizationMapper` (`§4.3–4.4`, `§6.5`). | **Hybrid Non-Disruptive Migration**: Extract the 10 verified C&C and Wood custom drawing routines into modular `DiagramSpec` builders/painters, host all calculations through `WorkspaceHost` + `WorkspaceController(item_id)` so multiple items of the same module coexist, and retain compatibility wrappers until all 69 tests pass on the new host. |
| **5. Canonical Module Catalog** | `ModuleRegistry` (`ModuleSpec`, `FieldSpec` with `enum_source` linked to KB CSV tables) replacing 3+ duplicate catalogs (`§3.5`). | `ModuleDefinition` catalog with explicit availability states (`AVAILABLE`, `COMING_SOON`, `UNVERIFIED`, `DISABLED`) preventing unimplemented templates from falling through to C&C (`§4.6`). | **Unified `ModuleRegistry`**: Single source of truth driving `AddCalculationDialog`, `InputForm`, `CalculationService`, and `DiagramSpec` dispatch, with explicit `maturity`/`availability` gating and manifest-verified `procedure_md` / `enum_source` references. |

### 1.2 Unified Finding & Resolution Register (`UF-01` to `UF-18`)

| Unified ID | Priority | Source Mapping | Finding Summary | Target Resolution Work Package |
|---|---|---|---|---|
| **UF-01** | **P0** | Claude `F-01`, GPT `§4.8` | Hard-coded mockup numbers, sample calculation sheet HTML, sample limit-state rows, `c_delta = 0.69` fallback, and silent `inputs.get(key, default)` fallbacks can display uncomputed or silently defaulted results as valid calculations. | **WP-0b** (GUI Hotfix) & **WP-3** (Schema Default Policy) |
| **UF-02** | **P0** | Claude `F-02`, GPT `§4.7` | Sidebar items in [`gui/main_window.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/gui/main_window.py) are an in-memory hard-coded list (`len(list)+1` IDs); `+ Add Calculation`, `Run Calculation`, and `Save Revision` are not fully wired to `ProjectService` / SQLite persistence. | **WP-1b**, **WP-4**, **WP-5** |
| **UF-03** | **P0** | Claude `F-03`, GPT `§4.6` | `MainWindow` holds only one workspace widget instance per material category and routes by `"wood" in template_id` (falling through to C&C otherwise); two calculations of the same module type cannot hold separate inputs/states. | **WP-4**, **WP-6** |
| **UF-04** | **P0** | Claude `F-10`, GPT `§4.1` | Bidirectional layer violation: `gui/` imports domain types directly from `core/`, while `core/asce7/` and `core/nds/` import concrete `KnowledgeBaseService` from `app/services/`. | **WP-1a** (`ReferenceDataPort` & `app/models/` DTOs) |
| **UF-05** | **P0** | Claude `F-06`, GPT `§4.6` | Module definitions are duplicated across `CalculationService._registry`, `list_supported_modules()`, `CCCalculationWorkspace.MODULE_CONFIGS`, `WoodCalculationWorkspace.MODULE_CONFIGS`, and `AddCalculationDialog.TEMPLATES_DATA`. | **WP-3** (`ModuleRegistry`) |
| **UF-06** | **P1** | Claude `F-04`, GPT `§4.7` | SQLite schema lacks calculation groups, user-defined `sort_order`, monotonic `item_number`, working draft input storage (`draft_inputs_json`), `is_stale` hash tracking, and per-revision KB SHA-256 hash snapshots. | **WP-1b** (SQLite Schema v2 Migration) |
| **UF-07** | **P1** | Claude `F-05`, GPT `§4.2`, `§4.5` | Panel 3 (`BaseCalculationWorkspace.display_results`) injects raw `equation_latex` text inside `<code>` tags in `QTextEdit` rather than rendering true mathematical notation, and lacks structured step/variable/reference objects. | **WP-2**, **WP-7**, **WP-9** |
| **UF-08** | **P1** | Claude `F-07`, GPT `§6.1` | Input forms use plain text line edits with raw underscore keys (`F_yb`), lacking mathematical symbol labels, explicit unit badges, field-level validation messages, and KB CSV-backed dropdowns. | **WP-3**, **WP-6** |
| **UF-09** | **P1** | Claude `F-08`, GPT `§4.3`, `§4.4` | Panel 2 diagram widgets merge raw `input_parameters` and `intermediate_results` dicts, only redraw after pressing `Run Calculation`, and inherit bolt drawing logic in base/placeholder classes. | **WP-8** (`DiagramSpec` & Input-Reactive Sync) |
| **UF-10** | **P1** | Claude `F-09` | Window titles and code banners hardcode `"NDS 2018"` whereas the Knowledge Base, manifest, and engines implement **NDS 2024** (`config/active_code_registry.json`). | **WP-0b**, **WP-3** |
| **UF-11** | **P1** | Claude `F-15` | Project-level default design method and active code registry snapshot are not persisted per project; segmented `ASD | LRFD` toggle is not persisted per calculation item. | **WP-1b**, **WP-4** |
| **UF-12** | **P2** | Claude `F-11` | Status bar hardcodes `"66 Tables / 26 Procedures"` and project title instead of querying `KnowledgeBaseService` manifest audit and `ProjectService`. | **WP-5** |
| **UF-13** | **P2** | Claude `F-12` | Dead hidden widgets (`radio_asd`, `radio_lrfd`, `ref_text`) remain in `base_workspace.py` solely for legacy test compatibility. | **WP-6** |
| **UF-14** | **P2** | Claude `F-13` | Sidebar navigation icons use emoji glyphs that exhibit UTF-8 byte corruption on Drive sync; replace with local bundled SVG icons (`gui/assets/icons/`). | **WP-5** |
| **UF-15** | **P2** | Claude `F-14`, GPT `§4.10` | Documentation drift: `README.md` still references `CustomTkinter`, and `context_guide.txt` contains outdated Drive File IDs. | **WP-0** |
| **UF-16** | **P2** | GPT `§4.10` | `exporters/excel_builder.py` can skip certain multi-header CSVs during `Database` tab embedding, and `simpson_connectors.py` has a hardcoded `HUS210-2` catalog special case. | **WP-9**, **WP-13** |
| **UF-17** | **P2** | GPT `§4.9` | Day 15 (`core/aisc360/`), Day 16 (`core/aci318/`, `core/tms402/`), and Day 17 (`cloud/`) packages are pending; dialog templates must remain gated until each module passes Level 1–5 verification. | **WP-3**, **WP-10**, **WP-11**, **WP-12** |
| **UF-18** | **P2** | GPT `§4.10` | Headless/offscreen `pytest` + `pytest-qt` + `PySide6` verification must be standardized so UI tests never silently fall back to AST syntax checks. | **WP-14** |

## 2. Frozen UI Specification (Non-Negotiable Visual & Interaction Contract)

Per user mandate in both reviews, the approved four-panel desktop interface is **visually frozen**. Architectural refactoring may replace internal controllers, models, and renderers, but must preserve the exact layout, proportions, colors, typography, and interaction flow below:

| UI Region | Locked Visual & Behavioral Specification |
|---|---|
| **Header Bar** | Left hamburger toggle button, dynamic active calculation title (`[Display Label] — [Item Title]`), right-aligned segmented `ASD | LRFD` design method switch |
| **Sidebar (Expanded — 232 px)** | Smooth ~120 ms collapse/expand transition; App logo & subtitle; navigation links (`Dashboard`, `Projects`, `Reports`, `Settings`); `PROJECT` header with active project name; full-width blue `+ Add Calculation` button; calculation tree grouped under user-defined group headers (`calculation_groups`), each row displaying item code/name, governing DCR, status badge, and subtle stale marker (`*` / dot when `is_stale=True`); footer hint `"Drag to reorder. Order reflects in reports."` |
| **Sidebar (Collapsed Rail — 48 px)** | Hamburger button, SVG navigation icons, compact blue `+` button, horizontal divider, numeric badge chips (`01`, `02`, `03!`) with status-colored underline, hover flyout card showing full title, module type, DCR, and status |
| **Workspace Split Layout** | 4-Panel Workspace: **Panel 1 (Inputs)** on the left (280–380 px width) with `Run Calculation` and `Save Revision` action buttons anchored at the bottom; right main area stacked vertically with adjustable `QSplitter` handles into **Panel 2 (Diagram — top right)**, **Panel 3 (Calculation Sheet — middle right)**, and **Panel 4 (Summary — bottom right)** |
| **Panel 1 — INPUTS** | Schema-driven grouped input sections (`Geometry`, `Material / Member`, `Fastener / Connector`, `Loads & Boundary Conditions`); mathematical symbol labels with subscripts (`t_m`, `F_{yb}`), explicit US Customary unit badges (`in.`, `lbs`, `psi`, `psf`), KB-backed dropdown selectors, and inline field validation state |
| **Panel 2 — DIAGRAM** | Live 2D engineering schematic (`DiagramCanvas`) rendering scaled member geometry, dimension lines with symbol + value labels (`t_m = 1.50 in.`), support conditions, load/force vectors, and an amber warning pill whenever a geometric or detailing limit state is violated |
| **Panel 3 — CALCULATION SHEET** | Dynamic code-basis banner (resolved from `config/active_code_registry.json`, e.g., `NDS 2024 • ASD`), followed by sequential calculation steps ordered per **Rule 5 (Stages 1–4)**: `Symbolic Equation -> Numerical Substitution -> Result -> Acceptance Limit / Criterion` with right-aligned clickable governing code/table references merged inline (no separate 5th reference panel) |
| **Panel 4 — SUMMARY** | Overall status pill (`PASS`, `FAIL`, `REQUIRES REVIEW`, `INCOMPLETE`, `INVALID INPUT`), governing limit state callout, visual DCR gauge, and 7-column summary table (`Step`, `Limit state check`, `Governing clause`, `Demand`, `Capacity`, `DCR`, `Status`) supporting both ratio-based (DCR) and pass/fail detailing checks |
| **Add Calculation Dialog** | 3-column modal dialog: **Column 1** Categories (`Recent`, `Loads`, `Wood`, `Steel`, `Concrete/CMU`) \| **Column 2** Module Templates (with `COMING SOON` badge for unverified modules) \| **Column 3** Configuration Preview (`Name`, `Group`, `Design method`, `Start from: Blank | Duplicate Existing`); `Cancel` and `Add & Open` buttons |

## 3. Unified Target Architecture

### 3.1 Clean Architecture Layering & Dependency Rule

Dependencies point strictly inward toward `core/`. No outer layer implementation detail may leak into an inner layer:

1. **Presentation Layer (`gui/`)**: Owns PySide6 widgets, `ProjectTreeModel`, `WorkspaceHost`, `InputForm`, `DiagramCanvas`, `CalcSheetView`, and dialogs. Imports **only** `app/controllers/`, `app/services/`, `app/models/`, and `app/rendering/`. Must **never** import `core/`, `storage/`, `cloud/`, or `exporters/` directly.
2. **Application Layer (`app/`)**:
   - `app/controllers/`: Pure-Python `WorkspaceController` managing per-item state transitions, debounced input editing, draft autosaving, and stale-state detection without importing `PySide6`.
   - `app/services/`: `ProjectService`, `CalculationService`, `HistoryService`, `ReportService`, `KnowledgeBaseService`.
   - `app/registry/`: Canonical `ModuleRegistry` (`ModuleSpec`, `FieldSpec`, `EnumSource`).
   - `app/models/`: Application DTOs and ViewModels (`ItemSummary`, `GroupSummary`, `WorkspaceViewModel`, `DiagramSpec`, `SummaryViewModel`).
   - `app/rendering/`: Multi-target math and diagram renderers (`katex_renderer.py`, `richtext_renderer.py`, `pdf_math_renderer.py`, `excel_math_renderer.py`, `diagram_builders/`).
3. **Domain / Calculation Engine Layer (`core/`)**: Pure deterministic Python + NumPy/Pandas calculation modules (`core/common/`, `core/asce7/`, `core/nds/`, `core/aisc360/`, `core/aci318/`, `core/tms402/`). Depends **only** on `core/common/` contracts and `ReferenceDataPort`. Must **never** import `app/services/`, `gui/`, or SQLite/file adapters.
4. **Infrastructure & Output Adapters (`storage/`, `exporters/`, `cloud/`, `database/`, `procedures/`)**: Concrete SQLite repository (`ProjectRepository`), `KnowledgeBaseService` (implementing `ReferenceDataPort`), `excel_builder.py`, `pdf_builder.py`, `csv_exporter.py`, and `CloudSyncService`.

### 3.2 `ReferenceDataPort` (Decoupling `core/` from `app/services/`)

To resolve GPT Finding `§4.1` without breaking existing unit tests that call engine functions directly:

```python
# core/common/ports.py
from typing import Any, Protocol
import pandas as pd

class ReferenceDataPort(Protocol):
    def get_table(self, reference_id: str) -> pd.DataFrame: ...
    def get_reference_hash(self, reference_id: str) -> str: ...
    def get_active_code_edition(self, code_family: str) -> str: ...
```

Engine functions accept an optional `kb: ReferenceDataPort | None = None` parameter (injected by `CalculationService` at runtime, with a lazy default provider wired in `core/common/ports.py` so standalone engine benchmark tests run unchanged).

### 3.3 Canonical `ModuleRegistry` (`app/registry/module_registry.py`)

A single immutable catalog replaces all duplicated dictionaries across `CalculationService`, workspace classes, and `AddCalculationDialog`:

```python
@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    symbol: str | None                 # Restricted LaTeX math markup, e.g. "t_{m}"
    unit: str | None                   # Validated via core.common.units
    kind: Literal["float", "int", "enum", "bool", "text"]
    section: Literal["Geometry", "Material / Member", "Fastener / Connector", "Loads & Boundary"]
    enum_source: EnumSource | None = None   # KB CSV table + column or static tuple
    required: bool = True
    default: Any = None                     # None for required engineering inputs unless code-authorized
    default_ref: str | None = None          # Mandatory code clause citation if default is non-None
    sample_value: Any = None                # Used ONLY when user explicitly loads a benchmark/demo template
    min_value: float | None = None
    max_value: float | None = None
    affects_geometry: bool = False          # Triggers immediate Panel 2 geometry redraw when edited
    visible_if: str | None = None

@dataclass(frozen=True)
class ModuleSpec:
    module_id: str
    aliases: tuple[str, ...]
    category: Literal["loads", "wood", "steel", "concrete_cmu"]
    title: str
    subtitle: str
    code_family: str                        # Resolved dynamically via config/active_code_registry.json
    supported_methods: tuple[str, ...]      # ("ASD", "LRFD")
    calc_fn: Callable[..., CalculationResult] | None
    fields: tuple[FieldSpec, ...]
    diagram_id: str
    procedure_md: str                       # Must exist in config/reference_manifest.json
    availability: Literal["VERIFIED", "COMING_SOON", "DISABLED"]
```

**Input Default Policy (Resolving `UF-01`):**
- Every new calculation created with `Start from: Blank` initializes required engineering fields as empty (`None`) and sets calculation status to `INCOMPLETE` with an empty Panel 3 Calculation Sheet.
- Silent `inputs.get(key, sample_number)` fallbacks inside `core/` and `gui/` are strictly prohibited unless the parameter is an explicit code-prescribed constant with `default_ref` documented.
- Sample values (`FieldSpec.sample_value`) are populated **only** in automated benchmark tests or when a user explicitly clicks `Load Verified Example` in the UI.

### 3.4 Structured Calculation Trace (`CalcStep`, `Quantity`, `RefSpec`) & Multi-Target Math Rendering

Extend `core/common/calculation_result.py` additively so all 69 existing tests continue to pass while enabling rich math rendering and full code provenance:

```python
@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str
    display_precision: int = 2

@dataclass(frozen=True)
class RefSpec:
    code: str                     # e.g. "NDS", "AISC 360", "ASCE 7"
    edition: str                  # e.g. "2024", "2022"
    kind: Literal["section", "equation", "table", "figure", "esr"]
    locator: str                  # e.g. "Table 12K", "Eq. J3-1", "Sec. K1.2"
    kb_reference_id: str | None = None
    sha256_hash: str | None = None

@dataclass(frozen=True)
class CalcStep:
    step_id: str
    stage: Literal[1, 2, 3, 4]    # Rule 5 4-Stage Load-Path Order:
                                  # 1=Geometry/Limits, 2=Primary Force Transfer,
                                  # 3=Connecting Element/Base Metal, 4=Supporting Member/Global
    title: str
    symbolic_markup: str          # Validated restricted LaTeX markup
    substituted_markup: str       # Validated restricted LaTeX markup with substituted operands
    operands: dict[str, Quantity]
    result: Quantity
    limit: Quantity | str | None = None
    dcr: float | None = None      # None for pure geometric/detailing pass/fail checks
    status: CalculationStatus = CalculationStatus.PASS
    refs: tuple[RefSpec, ...] = ()
    note: str = ""
```

**Multi-Target Math Rendering (`app/rendering/`):**
- **Restricted Math Grammar (`core/common/math_markup.py`)**: Validates `_`, `^`, `\frac{a}{b}`, `\sqrt{x}`, `\cdot`, `\times`, `\leq`, `\geq`, `\phi`, `\Omega`, `\Delta`, `\theta`, `\lambda`, `\parallel`, `\prime`, `\text{...}`, `\left(`, `\right)` at construction time.
- **Target 1 — Panel 3 (`CalcSheetView`)**: Renders `CalcStep` rows via locally vendored offline **KaTeX** (`gui/assets/katex/`) inside `QWebEngineView` with `QWebChannel` links so clicking any `RefSpec` badge opens `ReferencePopup` displaying the verified CSV table and SHA-256 hash. Includes an automatic `QTextEdit` HTML `<sub>`/`<sup>` fallback renderer (`richtext_renderer.py`) for environments without `QtWebEngine`.
- **Target 2 — PDF (`exporters/pdf_builder.py`)**: Converts `math_markup` into ReportLab `<sub/>` and `<super/>` tags across the 12-section report layout.
- **Target 3 — Excel (`exporters/excel_builder.py`)**: Converts `math_markup` into `openpyxl` cell text following **Rule 6** (`vertAlign="baseline"`, Arial 10pt, roots as `(a)^(1/2)`, multiplication as `.`, 17 columns `A:Q`, 3 tabs `Calc_Sheet`, `Database`, `Source_Audit`).

### 3.5 Typed `DiagramSpec` & Input-Reactive Synchronization (Panel 2)

```python
# app/models/visualization_model.py
@dataclass(frozen=True)
class DiagramSpec:
    diagram_id: str
    title: str
    is_stale: bool
    primitives: tuple[ShapePrimitive, ...]       # Plates, members, HSS sections, bolts, welds, anchors, walls
    dimensions: tuple[DimensionAnnotation, ...]  # Subscript math label + true value & unit
    supports: tuple[SupportAnnotation, ...]
    forces: tuple[ForceVectorAnnotation, ...]    # Derived strictly from CalculationResult (hidden or marked stale if uncalculated)
    warning_pills: tuple[str, ...]               # Populated from detailing/geometric limit states
```

- **Synchronization Rule**: Editing any geometry field (`affects_geometry=True`) in Panel 1 triggers `WorkspaceController.edit_field()` -> updates `DiagramSpec` geometry dimensions immediately in Panel 2 -> sets `is_stale = True` on any previous calculation result so outdated internal forces or DCRs are never mistaken for current results.

### 3.6 SQLite Schema v2 (`PRAGMA user_version = 2`) & Revision Provenance

Migration in `storage/repositories/project_repository.py` automatically backs up existing v1 databases to `storage/backups/` before executing idempotent DDL upgrades:

```sql
-- 1. User-defined calculation groups within a project
CREATE TABLE IF NOT EXISTS calculation_groups (
    group_id      TEXT PRIMARY KEY,
    project_id    TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    is_collapsed  INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

-- 2. Project-scoped ordering, working drafts, stale detection, and soft delete on calculations
ALTER TABLE calculations ADD COLUMN group_id TEXT REFERENCES calculation_groups(group_id) ON DELETE SET NULL;
ALTER TABLE calculations ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE calculations ADD COLUMN item_number INTEGER;
ALTER TABLE calculations ADD COLUMN draft_inputs_json TEXT;
ALTER TABLE calculations ADD COLUMN draft_updated_at TEXT;
ALTER TABLE calculations ADD COLUMN last_dcr REAL;
ALTER TABLE calculations ADD COLUMN last_input_hash TEXT;
ALTER TABLE calculations ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0;

-- 3. Reproducibility provenance on immutable calculation_revisions (GPT §4.5/§6.4)
ALTER TABLE calculation_revisions ADD COLUMN reference_snapshot_json TEXT;
ALTER TABLE calculation_revisions ADD COLUMN engine_version TEXT;

-- 4. Project-level engineering defaults and active code edition snapshot
CREATE TABLE IF NOT EXISTS project_settings (
    project_id            TEXT PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
    default_design_method TEXT NOT NULL DEFAULT 'ASD',
    code_registry_json    TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);
```

## 4. Master Execution Plan: From Current Stage (Post-Day 14) to 100% V1.0 Completion

**Strategic Sequencing Principle:** Do **not** build Day 15 (AISC 360 Steel) or Day 16 (ACI 318 / TMS 402 Concrete & CMU) on top of the legacy duplicated `MODULE_CONFIGS` or single-instance workspace classes. Execute **Stage 0, Stage 1, and Stage 2** first to establish the Clean Architecture contracts, `ModuleRegistry`, `CalcStep` trace, and schema-driven `WorkspaceHost`. Then implement **Stage 3 (Days 15 & 16)** natively on the new architecture rails, followed by **Stage 4 (Days 17 & 18)** and **Stage 5 (Days 19 & 20)** to reach 100% project completion.

### Stage 0 — Governance Sign-Off, Read-Only Audit & P0 Safety Hotfix

| Work Package | Owner | Dependencies | Detailed Scope & File Targets | Acceptance & Verification Gate |
|---|---|---|---|---|
| **WP-0: Governance, Baseline Audit & Doc Sync** | `Primary Agent` | User approval of `UNIFIED ACP-001` | 1. Record user sign-off on Section 6 decisions (`D-1` to `D-6`) and amend authorized sections of `proposed.md`.<br>2. Complete read-only audit of remaining uninspected files (`cc_workspace.py`, `add_calculation_dialog.py`, `report_service.py`, `excel_builder.py`, `pdf_builder.py`).<br>3. Fix `UF-15` doc drift in `README.md` (replace `CustomTkinter` with `PySide6`) and update Drive File IDs in `context_guide.txt`. | Signed-off `UNIFIED ACP-001`; `README.md`, `context_guide.txt`, and `state_summary.txt` synchronized with backups in `backup/`. |
| **WP-0b: P0 Safety Hotfix (Zero Silent Sample Defaults & Code Edition Fix)** | `desktop-app` | `WP-0` | 1. Resolve `UF-01`: Remove `_populate_sample_inputs`, `_populate_sample_calc_sheet`, `_populate_sample_table`, `c_delta = 0.69` fallback, and default warning strings from `gui/widgets/base_workspace.py` and `wood_workspace.py`.<br>2. Resolve `UF-10`: Replace hardcoded `"NDS 2018"` strings in `main_window.py` and workspaces with dynamic lookups from `config/active_code_registry.json` (`NDS 2024`, `ASCE 7-22`, `SDPWS 2021`). | Fresh workspace starts with blank required inputs, status `INCOMPLETE`, and empty Calculation Sheet; automated test verifies zero uncomputed engineering numbers appear before `Run Calculation`. |

### Stage 1 — Clean Architecture Contracts, SQLite Schema v2 & Single Module Registry

| Work Package | Owner | Dependencies | Detailed Scope & File Targets | Acceptance & Verification Gate |
|---|---|---|---|---|
| **WP-1a: Bidirectional Dependency Inversion (`ReferenceDataPort` & App DTOs)** | `calculation-engine` + `desktop-app` | `WP-0` | 1. Resolve `UF-04`: Create `core/common/ports.py` defining `ReferenceDataPort`; refactor `core/asce7/` and `core/nds/` to use `ReferenceDataPort` instead of importing `app.services.knowledge_base_service` directly.<br>2. Create `app/models/workspace_dtos.py` re-exporting/wrapping status and result DTOs so `gui/` imports zero symbols from `core/`. | Static AST import test enforces `gui/` -> no `core/` imports and `core/` -> no `app.services` or `gui/` imports; all 69 existing tests pass. |
| **WP-1b: SQLite Schema v2 Migration & `ProjectService` Multi-Item APIs** | `cloud-data` + `desktop-app` | `WP-0` | 1. Resolve `UF-02`, `UF-06`, `UF-11`: Upgrade `storage/repositories/project_repository.py` to `PRAGMA user_version = 2` (`calculation_groups`, item ordering/draft/stale/soft-delete columns, `project_settings`, and revision `reference_snapshot_json` + `engine_version`) with automatic backup to `storage/backups/`.<br>2. Implement `ProjectService` item/group APIs (`list_items`, `list_groups`, `add_item`, `duplicate_item`, `move_item`, `rename_item`, `delete_item`, `create_group`, `get/set_project_defaults`). | Migration test from v1 SQLite fixture preserves 100% of existing revisions byte-for-byte; unit tests pass for item creation, duplication, group move, drag reorder, soft delete, and revision hash snapshot. |
| **WP-2: Structured Calculation Trace (`CalcStep`) & Math Markup Parser** | `calculation-engine` | `WP-0` | 1. Resolve `UF-07`: Implement `Quantity`, `RefSpec`, and `CalcStep` (with `stage: Literal[1, 2, 3, 4]` matching Rule 5) in `core/common/calculation_result.py` and add optional `trace: tuple[CalcStep, ...] = ()` to `CalculationResult`.<br>2. Implement `core/common/math_markup.py` validator for the restricted LaTeX subset. | Unit tests for `math_markup` parser (valid expressions, nested subscripts/fractions, rejection of unknown macros); all 69 existing tests pass unchanged. |
| **WP-3: Canonical `ModuleRegistry` (`ModuleSpec` & `FieldSpec`)** | `desktop-app` | `WP-1a`, `WP-2` | 1. Resolve `UF-05`, `UF-08`, `UF-17`: Implement `app/registry/module_registry.py` (`ModuleRegistry`, `ModuleSpec`, `FieldSpec`, `EnumSource`).<br>2. Register all 10 verified Day 13 (C&C) and Day 14 (Wood) modules with full `FieldSpec` schemas, units, KB CSV `enum_source` bindings, and `procedure_md` paths; register planned Steel and Concrete/CMU templates as `COMING_SOON` until Stage 3 completes.<br>3. Wire `CalculationService` dispatch and `AddCalculationDialog` to `ModuleRegistry`. | Registry consistency test proves every `procedure_md` and `enum_source` CSV exists in `config/reference_manifest.json`, all aliases resolve uniquely, and `COMING_SOON` templates cannot fall through to C&C. |
| **WP-4: Pure-Python `WorkspaceController` & Item Lifecycle** | `desktop-app` | `WP-1b`, `WP-3` | 1. Resolve `UF-03`: Implement `app/controllers/workspace_controller.py` managing `load(item_id)`, `edit_field(key, raw_value)` (validation + debounced draft autosave + immediate geometry update), `set_design_method(method)`, `run()` (in-memory execution + `last_dcr` cache), and `save_revision(notes)` (immutable SQLite revision with `reference_snapshot_json`).<br>2. Compute `is_stale = (last_input_hash != current_hash)` without altering the 5 locked SAD 8.4 statuses. | Pure-Python controller unit tests (zero Qt dependency) verify multi-item state isolation, Blank vs. Duplicate initialization, `INCOMPLETE` gating on missing inputs, and `is_stale` detection on input/method/KB hash changes. |

### Stage 2 — Unified 4-Panel GUI, Offline Math Renderer, Typed Diagrams & Day 13/14 Trace Backfill

| Work Package | Owner | Dependencies | Detailed Scope & File Targets | Acceptance & Verification Gate |
|---|---|---|---|---|
| **WP-5: Project Tree Sidebar, Drag-and-Drop Reorder & SVG Icons** | `desktop-app` | `WP-1b`, `WP-3` | 1. Resolve `UF-02`, `UF-12`, `UF-14`: Implement `gui/sidebar/` (`sidebar_widget.py`, `project_tree_model.py`, `project_tree_view.py`, `rail_widget.py`) with `InternalMove` drag-and-drop reorder, group headers, context menu (`Rename`, `Duplicate`, `Move to Group`, `Delete`), and 48 px rail badge chips.<br>2. Replace corrupted emoji strings with bundled SVG icons in `gui/assets/icons/` and wire status bar to live `KnowledgeBaseService` manifest counts. | `pytest-qt` offscreen tests verify items, groups, and drag-and-drop order persist across restart; rail chips mirror tree order (`01`, `02`, `03!`). |
| **WP-6: Schema-Driven `WorkspaceHost`, `InputForm` & `SummaryPanel`** | `desktop-app` | `WP-4`, `WP-5` | 1. Resolve `UF-03`, `UF-08`, `UF-13`: Implement `gui/workspace/` (`workspace_host.py`, `workspace_view.py`, `input_form.py`, `summary_panel.py`).<br>2. Render Panel 1 inputs dynamically from `ModuleSpec.fields` (subscripts, unit badges, KB dropdowns, validation highlights); support multiple project items of the same module type with independent states.<br>3. Remove dead hidden widgets (`radio_asd`, `radio_lrfd`, `ref_text`) and retire legacy monolithic workspace state once parity tests pass. | Two Wood Bolt items in the same project hold distinct inputs and DCRs simultaneously; all existing C&C and Wood UI tests ported and passing. |
| **WP-7: Multi-Target Math Renderers, Offline `CalcSheetView` & `ReferencePopup`** | `desktop-app` | `WP-2`, `WP-6` | 1. Resolve `UF-07`: Implement `app/rendering/` (`katex_renderer.py`, `richtext_renderer.py`, `pdf_math_renderer.py`, `excel_math_renderer.py`).<br>2. Implement `gui/workspace/calc_sheet_view.py` using locally vendored KaTeX (`gui/assets/katex/`) with automatic `QTextEdit` rich-text fallback.<br>3. Implement `gui/dialogs/reference_popup.py` opening verified CSV tables and SHA-256 metadata when a code reference badge is clicked in Panel 3. | Golden-file rendering tests pass for all 4 renderers; 100% offline execution verified (zero external CDN requests); clicking any reference opens its manifest-verified table. |
| **WP-8: Typed `DiagramSpec`, Builders & Input-Reactive `DiagramCanvas`** | `desktop-app` | `WP-3`, `WP-6` | 1. Resolve `UF-09`: Implement `app/models/visualization_model.py` (`DiagramSpec`) and extract the 5 C&C and 5 Wood schematic views into modular pure-Python builders in `app/rendering/diagram_builders/`.<br>2. Implement `gui/workspace/diagram_canvas.py` rendering `DiagramSpec` with immediate geometry updates on Panel 1 edits, engine-derived force vectors, subscript dimension labels, and dynamic amber detailing warning pills. | Pure-Python unit tests verify `DiagramSpec` geometry and warning pills for all 10 C&C and Wood modules without Qt; editing a dimension in Panel 1 immediately updates Panel 2 and marks prior forces stale. |
| **WP-9: Day 13 (ASCE 7) & Day 14 (NDS/SDPWS) Engine `CalcStep` Trace Backfill** | `calculation-engine` | `WP-1a`, `WP-2` | 1. Populate structured `trace: tuple[CalcStep, ...]` (ordered per Rule 5 Stages 1–4 with resolvable `RefSpec` IDs) across all Day 13 (`core/asce7/`) and Day 14 (`core/nds/`) modules.<br>2. Resolve `UF-16` part 1: Remove the hardcoded `HUS210-2` special case in `simpson_connectors.py` by generalizing multi-row catalog lookup in `KnowledgeBaseService`. | 100% numerical parity across all 69 existing unit, benchmark, and regression tests; every emitted `CalcStep` has valid `math_markup` and manifest-verified `RefSpec` entries. |

### Stage 3 — Native Engineering Vertical Slices: Day 15 (Steel) & Day 16 (Concrete/CMU)

With Stages 1 and 2 complete, Day 15 and Day 16 require **zero new workspace subclasses**—each module is implemented cleanly as a deterministic `core/` engine emitting `CalcStep` traces, a `ModuleSpec` entry in `ModuleRegistry`, and a `DiagramSpec` builder.

| Work Package | Owner | Dependencies | Detailed Scope & File Targets | Acceptance & Verification Gate |
|---|---|---|---|---|
| **WP-10 (Roadmap Day 15): AISC 360-22 Steel Connections Pipeline** | `calculation-engine` + `desktop-app` | `WP-3`, `WP-7`, `WP-8`, `WP-9` | 1. Implement `core/aisc360/` using `ReferenceDataPort`, Dual LRFD/ASD parity, and **Rule 5 4-Stage Load-Path Order** (`CalcStep` Stages 1–4):<br>   - `bolts.py`: AISC 360-22 Ch. J3 bolt shear, tension, combined tension/shear interaction, bearing/tearout, slip-critical, block shear ($R_n$), and prying action.<br>   - `welds.py`: Ch. J2 fillet, CJP, PJP welds, directional strength factor $k_{ds}$, and eccentric weld groups (elastic vector & instantaneous center tables).<br>   - `shear_tab.py`: AISC Manual 16th Ed. Part 10 single-plate shear connections (conventional & extended) + **Table K1.2 HSS column wall slenderness & punching shear checks** per updated procedure `1V6UTtkmWNjIpU1HIAXFXNztsIJJpXx-T`.<br>   - `angles.py`: Single-angle and double-angle connections.<br>   - `base_plate.py`: AISC Design Guide 1 axial + moment base plates, concrete bearing, critical cantilever plate bending ($m, n, \lambda n'$), and anchor rod tension.<br>   - `hss_connections.py`: Unified **HSS-to-HSS moment & shear connection checks** (skewed/matched/stepped branch-to-column, throat-weighted Table K5.1 weld group, Chord sidewall plastification/crippling/punching, and Sec. H3 torsion interaction) per updated procedure `1wPgJu2YB-EwSJTlIU6nmBq6D1d8jzKqx`.<br>2. Register all 6 Steel modules in `ModuleRegistry` (`availability="VERIFIED"`), add 6 `DiagramSpec` builders (`app/rendering/diagram_builders/steel_builders.py`), and create `tests/test_steel_vertical_slice.py`. | Level 1–5 verification suite (`tests/test_steel_vertical_slice.py`) passing with AISC Manual 16th Ed. / Design Guide 1 benchmarks in both ASD and LRFD; all 6 Steel templates unlocked and interactive in `WorkspaceHost`. |
| **WP-11 (Roadmap Day 16): ACI 318-19 & TMS 402-22 Concrete and CMU Anchorage Pipeline** | `calculation-engine` + `desktop-app` | `WP-3`, `WP-7`, `WP-8`, `WP-9` | 1. Implement `core/aci318/` and `core/tms402/` using `ReferenceDataPort`, Dual LRFD/ASD parity, and **Rule 5 4-Stage Load-Path Order**:<br>   - `core/aci318/anchors.py`: ACI 318-19 Ch. 17 cast-in headed studs/bolts and post-installed expansion/adhesive anchors (steel strength $N_{sa}/V_{sa}$, concrete breakout $N_{cb}/N_{cbg}/V_{cb}/V_{cbg}$, pullout $N_{pn}$, side-face blowout $N_{sb}$, prying $V_{cp}$, seismic tension/shear provisions, and tension-shear interaction Eq. 17.8.3).<br>   - `core/tms402/cmu_anchorage.py`: TMS 402-22 out-of-plane & in-plane masonry anchor bolts, masonry breakout cones, anchor pullout/crushing, and hairpin/hooked bar engagement.<br>   - `core/tms402/embedded_post.py`: Cantilevered steel HSS/WF column embedded in CMU wall or concrete grade beam (embedment bearing couple, punch-through/out-of-plane breakout, grouted cell reinforcement, and local wall checks).<br>2. Register all Concrete/CMU modules in `ModuleRegistry` (`availability="VERIFIED"`), add `DiagramSpec` builders (`anchorage_builders.py`), and create `tests/test_anchorage_vertical_slice.py`. | Level 1–5 verification suite (`tests/test_anchorage_vertical_slice.py`) passing against ACI 318-19 / TMS 402-22 hand-calc benchmarks; 100% of V1.0 engineering modules (`Loads/C&C`, `Wood`, `Steel`, `Concrete/CMU`) active and verified. |

### Stage 4 — Cloud Synchronization & Full Multi-Item Engineering Exporters (Days 17 & 18)

| Work Package | Owner | Dependencies | Detailed Scope & File Targets | Acceptance & Verification Gate |
|---|---|---|---|---|
| **WP-12 (Roadmap Day 17 — Phase 5): Google Drive Raw Cloud Synchronization** | `cloud-data` + `desktop-app` | `WP-1b`, `WP-5` | 1. Implement `cloud/` package (`cloud/authentication/oauth_client.py`, `cloud/google_drive/drive_client.py`, `cloud/sync/cloud_sync_service.py`):<br>   - Google OAuth 2.0 authentication with Windows secure credential storage (zero hardcoded secrets).<br>   - Raw binary/text sync (`application/octet-stream` per Rule 3) for `database/`, `procedures/`, `config/reference_manifest.json`, and `state_summary.txt` without format conversion.<br>   - SHA-256 checksum comparison between local cache and remote Drive metadata.<br>   - Non-destructive conflict detection (preserving both local and remote copies, recording resolution in SQLite `sync_history`).<br>2. Implement `gui/dialogs/sync_dialog.py` and wire Settings/Header sync status indicators while guaranteeing 100% non-blocking offline calculation mode (SAD Sec. 10.6). | Offline calculation test passes with network disabled; mock & live Drive sync tests verify SHA-256 checksum detection, conflict preservation, and `_backup` archive creation in `168YNvao8onqXfHC-cjcSCWZz0sPnHz7h`. |
| **WP-13 (Roadmap Day 18 — Phase 6): Unified Multi-Item PDF, Excel & CSV Exporters** | `desktop-app` | `WP-7`, `WP-8`, `WP-10`, `WP-11` | 1. Upgrade `app/services/report_service.py` and `gui/reports/` to accept an ordered list of project calculation items (matching sidebar tree order and group headers, with item selection checkboxes).<br>2. Upgrade `exporters/excel_builder.py` (Rule 6): consume `CalcStep` traces (`Equation -> Substitution -> Result -> Limit -> DCR`), format subscripts/superscripts with `vertAlign="baseline"`, Arial 10pt, 17 columns (`A:Q`), 3 tabs (`Calc_Sheet`, `Database`, `Source_Audit`), and fix multi-header CSV parsing (`UF-16`).<br>3. Upgrade `exporters/pdf_builder.py` (SAD Sec. 11.3): generate 12-section ReportLab PDF packages with Table of Contents, item display labels (`C-01`, `C-02`), vector figures rendered from `DiagramSpec`, `<sub/>`/`<super/>` math formulas, and immutable revision/hash audit tables.<br>4. Implement `exporters/csv_exporter.py` for structured summary batch export. | End-to-end multi-item export test (combining C&C, Wood, Steel, and Concrete/CMU items) verifies exact tree ordering, zero formula/rendering errors, valid multi-header CSV embedding in `Database` tab, and SHA-256 audit traceability in both `.xlsx` and `.pdf`. |

### Stage 5 — Full 5-Level QA Verification, Windows Packaging & V1.0 Release (Days 19 & 20)

| Work Package | Owner | Dependencies | Detailed Scope & File Targets | Acceptance & Verification Gate |
|---|---|---|---|---|
| **WP-14 (Roadmap Day 19 — Phase 7 Part 1): 5-Level QA Verification & PyInstaller Windows `.exe` Build** | `qa-verifier` + `desktop-app` | `WP-12`, `WP-13` | 1. Execute complete 5-Level QA Suite (`pytest` + `pytest-qt` with `QT_QPA_PLATFORM=offscreen`):<br>   - **Level 1**: Unit tests across `core/`, `app/`, `storage/`, `exporters/`, `cloud/`.<br>   - **Level 2**: 92-file CSV/Markdown SHA-256 manifest, encoding (`utf-8-sig`), header, and footnote verification.<br>   - **Level 3**: Independent engineering benchmark verification across all C&C, Wood, Steel, and Concrete/CMU modules (ASD & LRFD).<br>   - **Level 4**: Full regression suite & static Clean Architecture import boundary checks.<br>   - **Level 5**: End-to-end workflow tests (`Create Project -> Add Items -> Group & Reorder -> Edit Inputs -> Run -> Save Revision -> Reload Revision -> Export PDF/XLSX`).<br>2. Create PyInstaller specification (`packaging/structural_app.spec`) bundling Python runtime, PySide6, vendored KaTeX (`gui/assets/katex/`), SVG icons, `config/`, `database/`, and `procedures/` into a standalone Windows executable distribution. | 100% test pass rate across all 5 levels; screenshot regression confirms frozen 4-panel UI; standalone Windows `.exe` launches cleanly offline and passes smoke calculation & PDF/XLSX export. |
| **WP-15 (Roadmap Day 20 — Phase 7 Part 2): Final UAT, Recovery Drills & V1.0 Release Sign-Off** | `Primary Agent` + `qa-verifier` | `WP-14` | 1. Execute SQLite database backup/restore drill and corrupted-input error-handling checks (SAD Sec. 13 & 14).<br>2. Profile startup time, memory footprint, diagram redraw latency (< 16 ms geometry redraw), and PDF/XLSX export speed.<br>3. Finalize `README.md`, user/developer documentation in `docs/`, `state_summary.txt`, and Section `2.1` of `proposed.md`; push tagged `v1.0.0` release commit to GitHub `mndo2710/structural-engineering-kb` and sync raw files to Google Drive. | All 15 SAD Acceptance Criteria (`AC-01` to `AC-15`) and all 20 Unified ACP Acceptance Criteria (`UACP-AC-01` to `UACP-AC-20`) verified 100% complete; V1.0 signed off. |

## 5. Unified Acceptance Criteria Checklist (`UACP-AC-01` to `UACP-AC-20`)

| ID | Category | Acceptance Criterion |
|---|---|---|
| **UACP-AC-01** | **UI Freeze** | The 4-panel workspace layout, collapsible sidebar (232 px / 48 px rail), header bar, and 3-column Add Calculation dialog match Section 2 with zero unintended visual changes in screenshot regression. |
| **UACP-AC-02** | **Safety & Defaults** | Creating a Blank calculation displays empty required inputs, status `INCOMPLETE`, and an empty Calculation Sheet; zero uncomputed or sample numbers (`c_delta = 0.69`, mockup HTML) ever appear as active calculation results. |
| **UACP-AC-03** | **Clean Boundaries** | Static import test verifies `gui/` imports nothing from `core/`, `storage/`, `cloud/`, or `exporters/`, and `core/` imports nothing from `app/services/` or `gui/` (using `ReferenceDataPort`). |
| **UACP-AC-04** | **Single Registry** | `ModuleRegistry` is the single source of truth for dialog templates, `InputForm` schemas, `CalculationService` dispatch, `DiagramSpec` builders, and `procedure_md` links; unimplemented modules are gated as `COMING_SOON`. |
| **UACP-AC-05** | **Multi-Item State** | Multiple calculation items of the same module type within a project maintain independent inputs, design methods (`ASD` vs. `LRFD`), draft states, diagrams, and results simultaneously. |
| **UACP-AC-06** | **Persistence & Order** | Projects, calculation groups, item drag-and-drop ordering, and working draft inputs persist across application restarts in SQLite Schema v2 (`PRAGMA user_version = 2`). |
| **UACP-AC-07** | **Non-Destructive Migration** | Migrating an existing v1 SQLite database to Schema v2 creates an automatic backup in `storage/backups/` and preserves 100% of existing `calculation_revisions` byte-for-byte. |
| **UACP-AC-08** | **Revision Provenance** | `Run Calculation` updates in-memory results and `last_dcr` without creating a revision; `Save Revision` creates an immutable revision storing inputs, results, `reference_snapshot_json` (SHA-256 hashes), and `engine_version`. |
| **UACP-AC-09** | **Stale State Tracking** | Modifying any input, toggling `ASD | LRFD`, changing project defaults, or updating a KB reference hash sets `is_stale = True` and displays a stale indicator while keeping statuses strictly within the 5 SAD 8.4 values. |
| **UACP-AC-10** | **Structured Trace & Load-Path** | Every calculation module emits an ordered `trace: tuple[CalcStep, ...]` following **Rule 5 4-Stage Load-Path Order** (`Geometry/Limits -> Primary Force Transfer -> Connecting Element/Base Metal -> Supporting Member/Global Interaction`). |
| **UACP-AC-11** | **Offline Math Rendering** | Panel 3 renders `CalcStep` equations and substitutions with true stacked fractions, subscripts, superscripts, and Greek symbols via offline vendored KaTeX (with `QTextEdit` fallback), and every reference badge opens `ReferencePopup`. |
| **UACP-AC-12** | **Input-Reactive Diagrams** | Panel 2 draws from a typed `DiagramSpec`; editing geometry fields in Panel 1 redraws geometry immediately, while derived forces and warning pills originate strictly from the deterministic `core/` engine. |
| **UACP-AC-13** | **Code Edition Fidelity** | All UI titles, banners, steps, and exports dynamically display the authoritative code editions from `config/active_code_registry.json` (`ASCE 7-22`, `NDS 2024`, `SDPWS 2021`, `AISC 360-22`, `ACI 318-19`, `TMS 402-22`). |
| **UACP-AC-14** | **Day 13 & 14 Parity** | Backfilling `CalcStep` traces into ASCE 7 (C&C) and NDS/SDPWS (Wood) modules preserves 100% numerical equivalence across all 69 existing unit and benchmark tests. |
| **UACP-AC-15** | **Day 15 Steel Complete** | All 6 AISC 360-22 Steel Connection modules (Bolts, Welds, Shear Tab incl. HSS punching shear, Angles, Base Plate, HSS-to-HSS Moment/Shear) pass Level 1–5 verification in both ASD and LRFD. |
| **UACP-AC-16** | **Day 16 Anchorage Complete** | All ACI 318-19 and TMS 402-22 Concrete/CMU Anchorage modules (Cast-in/Post-Installed Anchors, CMU Breakout, Embedded Steel Post) pass Level 1–5 verification in both ASD and LRFD. |
| **UACP-AC-17** | **Day 17 Cloud Sync** | `CloudSyncService` synchronizes raw files with Google Drive (`application/octet-stream`), validates SHA-256 hashes, preserves conflicting copies for manual resolution, and never blocks offline calculation. |
| **UACP-AC-18** | **Day 18 Exporters** | `ReportService` exports multi-item PDF (12-section ReportLab layout with `DiagramSpec` figures) and Excel (17-col Arial 10pt `openpyxl` with `Calc_Sheet`, `Database`, `Source_Audit`) in exact sidebar tree order. |
| **UACP-AC-19** | **Day 19 Windows `.exe`** | PyInstaller produces a standalone offline Windows executable bundling PySide6, vendored KaTeX, SVG icons, and the verified 92-file Knowledge Base. |
| **UACP-AC-20** | **Governance & Zero AI Runtime** | Zero AI/LLM calls or external network dependencies exist in the V1.0 runtime; `rules.md`, `proposed.md` Sec. 2.1, `state_summary.txt`, and `backup/` discipline are maintained 100%. |

## 6. Requested SAD v1.0 Amendments & User Decision Checklist

### 6.1 Proposed Amendments to `proposed.md` (SAD v1.0) Upon Approval

| SAD Section | Proposed Amendment |
|---|---|
| **Sec. 6.4 Calculation Result Standard** | Add optional structured `trace: tuple[CalcStep, ...]` (`Quantity`, `RefSpec`, `ReferenceSnapshot`) alongside existing fields. |
| **Sec. 8.1–8.3 Interface & Workspace** | Document project-scoped calculation tree with user-defined groups and drag-to-reorder in sidebar; align Panel 2 (`Diagram`) and Panel 3 (`Calculation Sheet` with merged inline code references) with frozen UI. |
| **Sec. 9.2–9.4 Storage & Revisions** | Document SQLite Schema v2 (`PRAGMA user_version = 2`: `calculation_groups`, item ordering/draft/stale columns, `project_settings`, and per-revision `reference_snapshot_json` + `engine_version`). Clarify Sec. 9.2 folder tree as the exported deliverable layout. |
| **Sec. 15 Repository Structure** | Add `core/common/ports.py`, `app/registry/`, `app/controllers/`, `app/models/`, `app/rendering/`, and modular `gui/sidebar/`, `gui/workspace/`, `gui/assets/`. |
| **Sec. 18 Architectural Decisions** | Append `ADR-11` (Project-scoped ordered calculation items & groups), `ADR-12` (Structured `CalcStep` trace & single math markup across UI/PDF/XLSX), `ADR-13` (Single `ModuleRegistry` & `ReferenceDataPort` dependency inversion), `ADR-14` (Offline vendored KaTeX with `QTextEdit` fallback), and `ADR-15` (Typed `DiagramSpec` & input-reactive geometry sync). |

### 6.2 Decisions Requested from the User to Kick Off Execution

| Decision ID | Decision Topic | Recommended Option |
|---|---|---|
| **D-1** | **Panel 3 Math Renderer** | **Approve Vendored Offline KaTeX (`QWebEngineView`) + `QTextEdit` Rich-Text Fallback** (delivers true stacked fractions and math typography offline, with fallback if a lightweight build is desired). |
| **D-2** | **Blank Input Default Policy** | **Approve Strict `INCOMPLETE` Start for Blank Items** (no silent sample numbers; defaults allowed only when code-mandated with a `default_ref` citation, plus an explicit `Load Verified Example` button for testing). |
| **D-3** | **Stale Result Representation** | **Approve Separate `is_stale` Flag + Visual Badge** (preserves the exact 5 locked statuses in SAD Sec. 8.4 without adding a 6th `OUTDATED` enum value). |
| **D-4** | **Dependency Inversion (`ReferenceDataPort`)** | **Approve `ReferenceDataPort` in `core/common/ports.py`** (eliminates `core/` -> `app/services/` coupling while keeping a default adapter so all 69 existing tests run without signature breakage). |
| **D-5** | **Master Roadmap Sequencing (Stages 0–5)** | **Approve Executing Stages 0–2 (Architecture & GUI Stabilization) Before Stage 3 (Days 15 & 16 Steel/Concrete)** so Steel and Concrete/CMU are built natively on `ModuleRegistry`, `CalcStep`, and `WorkspaceHost`. |
| **D-6** | **Authorization to Amend `proposed.md`** | **Approve Amending SAD Sections 6.4, 8.1–8.3, 9.2–9.4, 15, and 18** per Table 6.1 and starting **Stage 0 (`WP-0` & `WP-0b`)** immediately. |

## 7. Copy-Ready Master Execution Prompt for the Coding Agent Team

> **Role & Mandate:** You are the Lead Implementation Agent for `structural-engineering-kb`. Before touching any file, read `AGENTS.md`, `rules.md`, `proposed.md`, `state_summary.txt`, and `proposal/UNIFIED_ACP-001_Architecture_Proposal_and_Master_Roadmap.md`.
>
> **Non-Negotiable Constraints:**
> 1. **UI Freeze:** The approved PySide6 4-panel workspace (Panel 1 Inputs, Panel 2 Diagram top-right, Panel 3 Calculation Sheet with inline code references middle-right, Panel 4 Summary bottom-right) and collapsible sidebar (232 px / 48 px rail) are visually frozen. Do not alter layout proportions, colors, typography, or panel positions.
> 2. **Protected Assets & Change Control:** Never modify, reformat, or delete the 66 verified CSVs in `database/` or 26 Markdown procedures in `procedures/`. Before replacing any active root/config file on Google Drive, back up the prior version with a `_backup` suffix into `backup/` (`168YNvao8onqXfHC-cjcSCWZz0sPnHz7h`). Upload all `.csv`, `.md`, `.py`, `.json`, and `.txt` files as raw `application/octet-stream`.
> 3. **Engineering Rigor:** Enforce 100% US Structural Engineering English and US Customary units. Keep ASD and LRFD strictly separated. Never invent engineering data or use silent sample defaults for missing user inputs (return `INCOMPLETE`). Emit every calculation trace in the mandatory **Rule 5 4-Stage Load-Path Verification Order** (`1: Geometry/Limits -> 2: Primary Force Transfer -> 3: Connecting Element/Base Metal -> 4: Supporting Member/Global Interaction`).
>
> **Execution Sequence:** Execute Stages 0 through 5 (`WP-0` to `WP-15`) sequentially as defined in Section 4 of `UNIFIED_ACP-001_Architecture_Proposal_and_Master_Roadmap.md`. At the completion of each Work Package, run the required test suite, verify numerical parity against existing benchmarks, update `state_summary.txt` and Section `2.1` of `proposed.md`, and report exact files created/modified with test output evidence.
