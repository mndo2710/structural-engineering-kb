# SOFTWARE ARCHITECTURE DOCUMENT (SAD)
## Structural Engineering Calculation Application

**Project:** `structural-engineering-kb`  
**Product:** Standalone Structural Engineering App  
**Document Version:** 1.1 – Consolidated Architecture & V1.0 Completion Baseline (Synchronized with [`proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md`](https://drive.google.com/file/d/1KlEES_QYXMFnwYAKwqdathM7LalXiBq8/view?usp=drivesdk))  
**Date:** November 17, 2026  
**Platform:** Windows Desktop  
**Operation Mode:** Cloud-connected, offline-capable  
**AI Integration:** None in V1  
**Initial Scope:** Components & Cladding (C&C) and Structural Connections

---

# 1. DOCUMENT PURPOSE

## 1.1 Objective

This document defines the software architecture for converting the existing `structural-engineering-kb` project into a Windows desktop application for structural engineering calculations.

The application will provide a structured environment to:

- Maintain and access structural engineering reference data.
- Perform deterministic engineering calculations.
- Support ASD and LRFD design methods.
- Display calculation procedures, equations, substitutions, results, and governing limit states.
- Generate engineering calculation reports.
- Synchronize engineering databases and procedures with Google Drive.
- Maintain project, calculation, and revision records.

The application is intended to support US residential and light-commercial structural engineering workflows.

## 1.2 Architecture Philosophy

The application will be developed around five principles:

1. **Calculation-first:** Engineering calculations must be performed by deterministic Python functions, not by AI-generated responses.
2. **Traceability:** Every calculation result must be traceable to its input parameters, code edition, reference data, procedure, and software version.
3. **Separation of concerns:** Knowledge Base, Calculation Engine, GUI, cloud synchronization, and report generation must remain independent modules governed by Clean Architecture / Ports-and-Adapters boundaries.
4. **Cloud-connected:** Google Drive provides remote storage and synchronization for engineering reference files.
5. **Engineering verification:** Every calculation module must have test cases and independent verification before being released.

## 1.3 Out of Scope for V1

The following capabilities are explicitly excluded:

- AI Agents or autonomous agents.
- Gemini API or other LLM API integration.
- AI-generated engineering calculations.
- Automatic interpretation of construction drawings.
- Automatic engineering approval or code-compliance certification.
- Automatic submission of calculations to building departments.
- Real-time collaborative editing of the same calculation.

---

# 2. PROJECT BASELINE AND INHERITED CONVENTIONS

## 2.1 Existing Project Status

The existing project has completed all 10 days of Phase 1 Knowledge Base development (66 verified CSV lookup tables and 26 verified 7-section Markdown calculation procedures), Day 11 (Phase 2 Architecture Foundation Part 1), Day 12 (Phase 2 Architecture Foundation Part 2: SQLite Storage & PySide6 4-Panel GUI Workspace), Day 13 (Component Pipeline: C&C Module Vertical Slice E2E), Day 14 (Component Pipeline: Wood Connections & Lateral Vertical Slice E2E), GitHub repository synchronization (commit `2b77570` pushed to `origin/main`), the November 17, 2026 Steel Procedure Upgrades (`steel_hss_to_hss_moment_shear_aisc_workflow.md` and `steel_shear_tab_connection_aisc_workflow.md` + Rule 5 4-Stage Load-Path Verification Order), and user adoption of `proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md` (`1KlEES_QYXMFnwYAKwqdathM7LalXiBq8`) as the authoritative V1.0 completion roadmap (`Phase 0 / WP-0` through `Phase 10 / Day 20`).

The current repository includes:

- `proposal/` (`Structural_Calculation_App_Consolidated_Architecture_Proposal.md` — Approved Consolidated Architecture Review, Change Proposal & V1.0 Completion Roadmap)
- `database/` (`asce_7/`, `ibc_cbc/`, `nds_wood/`, `aisc_360/`, `aci_318_tms_402/`, `manufacturer_catalogs/` — 66 verified CSVs with SHA-256 integrity validation)
- `procedures/` (`01_loads_and_seismic/`, `02_wood_design/`, `03_steel_design/`, `04_concrete_masonry_foundation/`, `05_plan_check_responses/`, `06_components_and_cladding/` — 26 verified MD procedures following the 7-section Plan Check layout and 4-Stage Load-Path sequence)
- `core/` (`common/`: `calculation_result.py`, `units.py`, `load_combinations.py`, `validation.py`, `exceptions.py`; `ports/`; `asce7/wind/`: `velocity_pressure.py`, `c_and_c_pressure.py`, `parapet.py`, `roof_overhang.py`, `awning.py`, `trellis.py`, `guardrail.py`; `asce7/seismic/`: `seismic_loads.py`; `nds/fasteners/`: `bolts.py`, `nails_screws.py`; `nds/lateral/`: `shear_walls.py`, `diaphragms.py`; `nds/connections/`: `simpson_connectors.py`; `aisc360/`, `aci318/`, `tms402/`)
- `app/` (`models/`, `registry/`, `controllers/`, `rendering/`, `services/`: `knowledge_base_service.py`, `project_service.py`, `history_service.py`, `calculation_service.py`, `report_service.py`)
- `storage/` (`repositories/project_repository.py` managing SQLite tables for projects, calculation groups, ordered calculation items, drafts, inputs, results, and immutable revisions; `migrations/`, `backups/`)
- `gui/` (`main_window.py` with frozen expandable/collapsible 232px / 48px rail sidebar, segmented `ASD | LRFD` toggle; `widgets/base_workspace.py`, `widgets/cc_workspace.py` & `widgets/wood_workspace.py` interactive 4-panel C&C and Wood workspaces with 10 dynamic sub-assembly/connection diagrams; `dialogs/add_calculation_dialog.py` 3-column template selector; `assets/`)
- `exporters/` (`excel_builder.py` 17-col Arial 10pt 3-tab XLSX builder, `pdf_builder.py` 12-section ReportLab PDF builder, `audit_logger.py` SHA-256 reference audit logger)
- `cloud/`
- `config/` (`app_settings.json`, `active_code_registry.json`, `reference_manifest.json` with 92 verified SHA-256 checksums)
- `tests/` (69 passing unit, benchmark, regression, and E2E tests covering units, load combinations, validation, KnowledgeBaseService, SQLite storage, PySide6 GUI, C&C Vertical Slice, and Wood Connections & Lateral Vertical Slice)
- `logs/`, `docs/`, `backup/`, `.agents/agents/`
- `AGENTS.md`, `rules.md`, `state_summary.txt`, `context_guide.txt`, `main.py`, `requirements.txt`, `README.md`

| Work Package / Milestone | Status |
|---|---|
| Days 1–10 – Phase 1 Engineering Knowledge Base (66 CSVs + 26 MDs) | Completed (100%) |
| Days 11–12 – Phase 2 Architecture Foundation (`core/common/`, `KnowledgeBaseService`, SQLite v1, PySide6 4-Panel UI) | Completed (100%) |
| Day 13 – Component Pipeline: ASCE 7-22 C&C Vertical Slice E2E (61/61 tests) | Completed (100%) |
| Day 14 – Component Pipeline: NDS 2024 & SDPWS 2021 Wood Vertical Slice E2E (69/69 total tests) | Completed (100%) |
| Pre-Day 15 Prep – Steel HSS/Shear Tab Procedure Upgrades & Rule 5 4-Stage Load-Path Standard | Completed (100%) |
| Consolidated ACP Synchronization (`1KlEES_QYXMFnwYAKwqdathM7LalXiBq8`) | Completed (100%) |
| Phase 0 (`WP-0`) – Read-Only Baseline Audit & Dependency/Schema Verification | Completed (100%) |
| Phase 1 (`WP-0b`) – P0 Live-Data Safety Hotfix (Zero Silent Sample Defaults) | Completed (100%) |
| Phase 2 (`WP-1a` + `WP-2` + `WP-3`) – SQLite Schema v2, Structured `CalcStep` Trace & `ModuleRegistry` | Completed (100%) |
| Phase 3 (`WP-1b` + `WP-4`) – `ProjectService` Item/Group APIs & Pure-Python `WorkspaceController` | Completed (100%) |
| Phase 4 (`WP-5` + `WP-6`) – Sidebar Tree, Add Dialog Integration & Schema-Driven `WorkspaceHost` | Completed (100%) |
| Phase 5 (`WP-7` + `WP-8` + `WP-9`) – Offline KaTeX Assets, `DiagramSpec` Builders & C&C/Wood Trace Migration | Completed (100%) |
| Phase 6 (`WP-11` + `Day 15` & `Day 16`) – AISC 360-22 Steel & ACI 318-19 / TMS 402-22 Concrete/CMU Engines | Completed (100%) |
| Phase 7 (`WP-10` + `Day 18`) – Ordered Multi-Item Reports & PDF/XLSX Exporter Completion | Completed (100%) |
| Phase 8 (`Day 17`) – Google Drive Raw-File Synchronization & Offline Cache | Completed (100%) |
| Phase 9 (`Day 19`) – Full 8-Category QA, Screenshot Regression & Windows PyInstaller Packaging | Completed (100% — 240/240 tests) |
| Phase 10 (`Day 20`) – Final UAT, Documentation & V1.0 Release Sign-Off | Ready for User Sign-Off |

## 2.2 Locked Engineering Data Conventions

The following rules are mandatory and must not be changed without an explicit project decision.

### Language and Units

- User-facing communication: Vietnamese.
- CSV, Markdown, Python code, variable names, class names, and filenames: US Structural Engineering English.
- Unit system: US Customary (`in.`, `ft`, `lbs`, `kips`, `psi`, `ksi`, `psf`, `plf`, `lb-in.`, `lb-ft`, `kip-in.`, `kip-ft`).
- Design methods: ASD and LRFD (strictly separated; never mix ASD and LRFD factors in the same check).

### CSV Standard

- Filename convention: `[Code]_[TableNumber].csv`.
- Encoding: `utf-8-sig`.
- Preserve exact source row and column order.
- Preserve exact mathematical symbols.
- Include complete verbatim footnotes at the bottom.
- Perform five-step verification against the applicable TCUS reference PDFs, Simpson Strong-Tie catalogs, and SkyCiv documentation.

### Procedure Markdown Standard & 4-Stage Load-Path Sequence

Every engineering procedure must follow the seven-section Plan Check structure:

1. Assumptions & Load Path
2. Load Combos & Internal Forces
3. Primary Member Checks
4. Sequential Connection Limit States
5. Supporting Substrate Checks
6. Mandatory Detailing Notes
7. Summary Checklist Table

Within Section 4 (and across `CalcStep.stage`), every calculation workflow follows the mandatory **4-Stage Load-Path Verification Sequence**:
- **Stage 1:** Geometry, Detailing & Applicability Limits
- **Stage 2:** Primary Force-Transfer Mechanism
- **Stage 3:** Connecting Element & Base Metal Limit States
- **Stage 4:** Supporting Member / Global Substrate & Combined Interaction

### Google Drive File Standard

CSV, Markdown, JSON, PY, and TXT files must remain raw files uploaded with:
- `base64_content="file:///..."`
- `mime_type="application/octet-stream"`

---

# 3. SYSTEM OVERVIEW & CLEAN ARCHITECTURE

## 3.1 Clean Architecture / Ports-and-Adapters Model

The application evolves the layered architecture into a lightweight Clean Architecture / Ports-and-Adapters structure with strict inward dependency direction:

```text
PRESENTATION / GUI — PySide6 (Frozen 4-Panel UI)
  MainWindow | Sidebar Tree & Rail | Add Dialog | WorkspaceHost
  InputForm | DiagramCanvas | CalcSheetView | SummaryPanel
       |
       |  (App-facing DTOs, ViewModels, Commands)
       v
APPLICATION LAYER (app/)
  WorkspaceController (pure Python, no Qt imports) | ModuleRegistry (ModuleSpec, FieldSpec)
  ProjectService | CalculationService | HistoryService | ReportService
  app/rendering/ (KaTeX, RichText, PDF/XLSX math & DiagramSpec projection)
       |                                      |
       | (Domain Request / CalculationResult) | (Ports / Interfaces)
       v                                      v
ENGINEERING DOMAIN / CORE (core/)       INFRASTRUCTURE ADAPTERS
  ASCE 7 | NDS | AISC 360                KnowledgeBaseService (implements ReferenceDataPort)
  ACI 318 | TMS 402                      SQLite ProjectRepository (Schema v2)
  Units | Combinations | Checks          PDF (ReportLab) & XLSX (openpyxl) Exporters
  CalcStep / Quantity / RefSpec          Local Cache & Google Drive Raw CloudSyncService
  ReferenceDataPort (core/ports/)
```

## 3.2 Enforceable Dependency Rules

| Layer | Responsibility | Prohibited Dependencies |
|---|---|---|
| **GUI Layer (`gui/`)** | User interaction, frozen 4-panel presentation, Qt models/views | Must **never** import `core/`, `storage/`, `cloud/`, or `exporters/` directly; must **never** implement engineering equations |
| **Application Layer (`app/`)** | Use-case orchestration, `WorkspaceController`, `ModuleRegistry`, view-model & rendering projection | Must **never** import `PySide6` inside `app/controllers/`, `app/models/`, or `app/registry/`; must **never** implement structural formulas |
| **Calculation Engine (`core/`)** | Deterministic engineering calculations, units, load combinations, structured `CalcStep` traces | Must **never** import `PySide6`, `gui/`, or concrete `app.services` implementations (accesses reference data through `ReferenceDataPort`) |
| **Infrastructure (`storage/`, `exporters/`, `cloud/`)** | SQLite persistence, CSV/MD parsing, PDF/XLSX report building, Google Drive raw sync | Must **never** recalculate engineering demands/capacities or alter protected KB files |

---

# 4. TECHNOLOGY STACK

## 4.1 Recommended Technologies

| Component | Recommended Technology | Purpose |
|---|---|---|
| Programming Language | Python 3.x | Main application language |
| Desktop GUI | PySide6 | Native Windows desktop interface (4-panel frozen workspace) |
| Math Rendering | Vendored Offline KaTeX (`QWebEngineView`) + `QTextEdit` fallback | True mathematical notation in Panel 3 without internet |
| Calculation Engine | Python + NumPy / SciPy / Pandas | Deterministic engineering calculations |
| Reference Database | CSV (`utf-8-sig`) / JSON | Engineering lookup tables & SHA-256 manifest |
| Procedure Files | Markdown (`.md`) | 7-Section engineering workflows |
| Project Database | SQLite (Schema v2, `PRAGMA user_version = 2`) | Project, group, ordered item, draft, and immutable revision records |
| Excel Export | `openpyxl` / `XlsxWriter` | 17-column (`A:Q`) Arial 10pt 3-tab XLSX workbook generation |
| PDF Export | `ReportLab` | 12-section calculation report generation |
| Testing | `pytest` + `pytest-qt` | 5-level + GUI + offline + packaging verification |
| Application Packaging | `PyInstaller` | Standalone Windows `.exe` executable |
| Cloud Storage | Google Drive API v3 + `keyring` | Raw reference file synchronization & OS credential storage |

---

# 5. KNOWLEDGE BASE ARCHITECTURE & REFERENCE DATA PORT

## 5.1 Knowledge Base Protection & `ReferenceDataPort`

The existing `database/` (66 CSVs) and `procedures/` (26 MDs) folders remain locked and protected. To prevent `core/` from depending on concrete `app.services.KnowledgeBaseService`, `core/ports/` defines a narrow `ReferenceDataPort` protocol implemented by `KnowledgeBaseService`.

`KnowledgeBaseService` responsibilities:
- Locate and load CSV tables (`utf-8-sig`) including resilient parsing of multi-header CSV files so zero referenced tables are silently skipped.
- Resolve active code editions from `config/active_code_registry.json`.
- Validate SHA-256 checksums against `config/reference_manifest.json` (92 entries) and provide reference hash snapshots for calculation revisions.

---

# 6. CALCULATION ENGINE, MODULE REGISTRY & STRUCTURED TRACE

## 6.1 Canonical `ModuleRegistry` (`app/registry/`)

A single `ModuleRegistry` replaces all duplicated module lists across the Add Calculation dialog, workspaces, `CalculationService`, and `MainWindow`:
- **`ModuleSpec`**: `module_id`, `aliases`, `category` (`loads`, `wood`, `steel`, `concrete_cmu`), `title`, `description`, `code_family`, `calculation_callable`, `fields: tuple[FieldSpec, ...]`, `diagram_id`, `procedure_md`, `maturity` (`verified`, `preview`, `coming_soon`, `unavailable`), `supported_methods`.
- **`FieldSpec`**: `key`, `label`, `symbol`, `quantity_type`, `unit`, `value_type`, `section`, `required`, `default_value`, `default_reference`, `enum_source`, `validation`, `visible_if`, `affects_geometry`, `affects_analysis`.

## 6.2 Input Policy & Zero Silent Sample Defaults

1. Required engineering inputs start **blank** on a newly created calculation item.
2. Missing mandatory inputs yield `INCOMPLETE`; invalid units/types/ranges yield `INVALID INPUT`.
3. Default values are permitted **only** when explicitly authorized by the governing code/workflow and accompanied by `default_reference`.
4. Sample values are restricted to test/benchmark fixtures or an explicit demonstration fixture—never used as live defaults for a real user item.

## 6.3 Calculation Result Standard & Structured Trace (`CalcStep`)

`CalculationResult` retains all existing fields for backward compatibility and adds an ordered `trace: tuple[CalcStep, ...]` field:

- **`RefSpec`**: `code`, `edition`, `kind` (`section`, `equation`, `table`, `figure`, `procedure`, `catalog`), `locator`, `kb_reference_id`, `source_path`, `sha256`.
- **`CalcStep`**: `step_id`, `stage` (1–4 per Rule 5), `title`, `symbolic` (validated restricted LaTeX math markup), `substituted`, `variables` (typed `Quantity` values/units), `result_value`, `result_unit`, `acceptance` (supports both DCR limits and non-DCR dimensional/drift/spacing criteria), `dcr`, `status`, `refs: tuple[RefSpec, ...]`, `note`.

---

# 7. APPLICATION SERVICE LAYER & WORKSPACE CONTROLLER

## 7.1 `WorkspaceController` (`app/controllers/`)

Pure-Python controller (no `PySide6` imports) managing the state of a selected calculation item and returning a `WorkspaceViewModel`:
- `load(item_id) -> WorkspaceViewModel`
- `edit_field(item_id, key, raw_value) -> WorkspaceViewModel`
- `set_design_method(item_id, method) -> WorkspaceViewModel`
- `run(item_id) -> WorkspaceViewModel` (computes in-memory result, updates `last_dcr`; **does not create a revision**)
- `save_revision(item_id, change_notes) -> WorkspaceViewModel` (writes an **immutable revision** with inputs, result, trace, code context, software version, and reference SHA-256 snapshot)
- `load_revision(item_id, revision_number) -> WorkspaceViewModel`

## 7.2 `ProjectService` Item & Group APIs

- `list_items(project_id)` / `list_groups(project_id)`
- `add_item(project_id, module_id, title, group_id, start_from)` (`Blank` or `Duplicate` — duplicate copies draft inputs/settings only, never revision history)
- `duplicate_item(item_id)` / `move_item(item_id, group_id, new_index)` (atomic transaction) / `rename_item(item_id, title)` / `delete_item(item_id)` (soft delete, preserving revisions)
- `create_group(project_id, name)` / `rename_group(group_id, name)` / `move_group(group_id, new_index)` / `set_group_collapsed(group_id, collapsed)`
- `get_project_defaults(project_id)` / `set_project_defaults(project_id, defaults)`

---

# 8. GUI ARCHITECTURE (FROZEN 4-PANEL PYSIDE6 SPECIFICATION)

## 8.1 Non-Negotiable UI Freeze

The approved PySide6 UI is **visually frozen**. Only internal data bindings, controllers, persistence, and renderers may change:

| Area / Panel | Position | Locked Design & Responsibility |
|---|---|---|
| **Header Bar** | Top full-width | Hamburger button, dynamic calculation item title, right-aligned segmented `ASD \| LRFD` toggle |
| **Sidebar (Expanded)** | Left, 232 px (~120 ms animation) | Logo/subtitle; navigation (`Dashboard`, `Projects`, `Reports`, `Settings`); `PROJECT` label/name; blue full-width `+ Add Calculation`; calculation items under user-defined group headers showing name and DCR/status; footer hint `"Drag to reorder. Order reflects in reports."` |
| **Sidebar (Collapsed Rail)** | Left, 48 px | Hamburger, navigation icons, blue `+` button, divider, numbered item badge chips (`01`, `02`, `03!`) with status underline, hover flyout (title, module, DCR, status) |
| **Add Calculation Dialog** | Modal, 3 columns | Column 1: Categories (`Recent`, `Loads`, `Wood`, `Steel`, `Concrete/CMU`) \| Column 2: Templates (from `ModuleRegistry`, gating unverified items as `COMING_SOON`) \| Column 3: Preview with `Name`, `Group`, `Design method`, `Start from` (`Blank` / `Duplicate`); `Cancel` and `Add & Open` |
| **Panel 1 — INPUTS** | Workspace Left (280–380 px) | Schema-driven engineering input form (`FieldSpec` symbols, units, KB-backed dropdowns, validation); `Run Calculation` and `Save Revision` buttons below |
| **Panel 2 — DIAGRAM** | Workspace Top-Right | Dynamic schematic driven by Qt-independent `DiagramSpec`; true dimension symbols/subscripts and values; immediate geometry redraw on input change; engine-derived force arrows (marked stale on input edit); amber warning pill for detailing violations |
| **Panel 3 — CALCULATION SHEET** | Workspace Middle-Right | Dynamic code-basis banner; ordered calculation rows (`Equation -> Substitution -> Result`) with right-aligned governing code references integrated inline (no separate 5th reference panel); rendered via offline vendored KaTeX (`QWebEngineView`) with rich-text fallback |
| **Panel 4 — SUMMARY** | Workspace Bottom-Right | `SummaryViewModel`: status pill (`PASS`, `FAIL`, `REQUIRES REVIEW`, `INCOMPLETE`, `INVALID INPUT`) + separate `is_stale` indicator, governing limit state, DCR gauge, and 7-column table (`Step`, `Limit state check`, `Governing clause`, `Demand`, `Capacity`, `DCR`, `Status`) |

---

# 9. PROJECT AND DATA STORAGE (SQLITE SCHEMA v2)

## 9.1 SQLite Schema v2 (`PRAGMA user_version = 2`)

SQLite (`storage/projects/structural_app.sqlite3`) is the authoritative local store for projects, groups, calculation items, drafts, and immutable revisions. Pre-migration v1 databases are automatically backed up to `storage/backups/` before applying additive Schema v2 DDL:

```sql
CREATE TABLE IF NOT EXISTS calculation_groups (
    group_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    is_collapsed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

ALTER TABLE calculations ADD COLUMN group_id TEXT REFERENCES calculation_groups(group_id) ON DELETE SET NULL;
ALTER TABLE calculations ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE calculations ADD COLUMN item_number INTEGER;
ALTER TABLE calculations ADD COLUMN draft_inputs_json TEXT;
ALTER TABLE calculations ADD COLUMN draft_updated_at TEXT;
ALTER TABLE calculations ADD COLUMN last_dcr REAL;
ALTER TABLE calculations ADD COLUMN last_input_hash TEXT;
ALTER TABLE calculations ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS project_settings (
    project_id TEXT PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
    default_design_method TEXT NOT NULL DEFAULT 'ASD',
    code_registry_json TEXT,
    updated_at TEXT NOT NULL
);
```

- **Stale Hash Rule:** `last_input_hash` is computed from canonical normalized serialization of inputs + design method + effective code context + applicable project defaults + module version + reference-manifest snapshot.
- **Export Folder Layout:** Any `Projects/Project_001/reports/...` folder tree is an export output layout; SQLite remains the single local source of truth for project state.

---

# 10. CLOUD-CONNECTED ARCHITECTURE

Google Drive serves as the remote storage and synchronization platform for the raw engineering Knowledge Base (`database/`, `procedures/`, `config/reference_manifest.json`).
- **Raw Sync Only:** Upload/download raw `.csv`, `.md`, `.json`, and `.txt` files (`application/octet-stream`) without converting to Google Docs/Sheets.
- **Project Boundary (`Decision D-7`):** Local project SQLite databases are not automatically synced to Google Drive in V1 unless separately scoped and approved.
- **Offline Guarantee:** Cloud availability must never block local deterministic calculations or PDF/XLSX report generation.

---

# 11. EXPORT ENGINE

`ReportService`, `exporters/excel_builder.py`, and `exporters/pdf_builder.py` consume the ordered list of project calculation items, `CalculationResult.trace`, `DiagramSpec`, and reference snapshots without recalculating any engineering equation:
- **XLSX (`openpyxl`)**: 17 columns (`A:Q`), Arial 10pt, `vertAlign="baseline"`, 3 tabs (`Calc_Sheet`, resilient multi-header `Database`, and `Source_Audit`), flow `Equation -> Substitution -> Result -> Limit -> DCR`.
- **PDF (`ReportLab`)**: 12-section formal engineering report built around the mandatory 7-section Plan Check structure in project tree order.

---

# 12. ENGINEERING VERIFICATION AND QUALITY CONTROL

Every release candidate must pass 8 verification categories in a provisioned environment with pinned dependencies:
1. **L1 — Unit Testing:** Units, validation, load combinations, formulas, trace models, math parser, registry, diagram builders, controller, and services.
2. **L2 — Reference Data Testing:** 92/92 SHA-256 manifest verification, `utf-8-sig` encoding, headers, and footnotes.
3. **L3 — Benchmark Testing:** Every C&C, Wood, Steel, and Concrete/CMU module verified against independent hand calculations / code examples (ASD & LRFD).
4. **L4 — Regression & Boundary Testing:** Historical numerical parity, schema v1->v2 migration preservation, and static Clean Architecture import boundary checks.
5. **L5 — End-to-End Testing:** `Add -> Input -> Validate -> Diagram -> Run -> Save Revision -> Reopen -> Duplicate/Reorder -> Export`.
6. **GUI — Visual Regression:** Before/after screenshot comparison confirming the Frozen 4-Panel UI.
7. **Offline — Runtime Verification:** Full startup, calculation, and export with network disabled.
8. **Packaging — Clean-Machine Windows Build:** Standalone PyInstaller `.exe` verified on a clean Windows environment.

---

# 13. ERROR HANDLING AND APPLICATION LOGGING

Structured logs (`logs/application.log`, `calculation.log`, `cloud_sync.log`, `error.log`) with credential redaction and explicit handling of input, unit, reference, calculation, cloud, and export errors.

---

# 14. SECURITY AND DATA INTEGRITY

OAuth 2.0 credentials stored via OS `keyring`; SHA-256 verification on all 92 reference files; automatic SQLite backups in `storage/backups/` before schema migration; Markdown procedures treated strictly as non-executable reference documentation.

---

# 15. PROPOSED REPOSITORY STRUCTURE

```text
structural-engineering-kb/
├── proposal/
│   └── Structural_Calculation_App_Consolidated_Architecture_Proposal.md
├── database/           # 66 verified CSV tables (protected)
├── procedures/         # 26 verified 7-section Markdown procedures (protected)
├── core/
│   ├── common/         # units.py, load_combinations.py, calculation_result.py, math_markup.py, validation.py
│   ├── ports/          # ReferenceDataPort protocol
│   ├── asce7/          # Wind & seismic C&C modules
│   ├── nds/            # Wood fasteners, lateral & Simpson connectors
│   ├── aisc360/        # Steel connections (Day 15)
│   ├── aci318/         # Concrete anchorage (Day 16)
│   └── tms402/         # Masonry anchorage & embedded posts (Day 16)
├── app/
│   ├── models/         # Application DTOs, WorkspaceViewModel, DiagramSpec, SummaryViewModel
│   ├── registry/       # ModuleRegistry, ModuleSpec, FieldSpec
│   ├── controllers/    # Pure-Python WorkspaceController
│   ├── ports/          # Application persistence/export ports
│   ├── services/       # ProjectService, CalculationService, KnowledgeBaseService, ReportService, HistoryService
│   └── rendering/      # KaTeX/RichText/PDF/XLSX math renderers & DiagramSpec builders
├── gui/
│   ├── main_window.py
│   ├── dialogs/
│   ├── widgets/
│   └── assets/         # Vendored offline KaTeX & SVG icons
├── storage/
│   ├── repositories/   # SQLite ProjectRepository (Schema v2)
│   ├── migrations/
│   ├── projects/
│   └── backups/
├── exporters/          # excel_builder.py, pdf_builder.py, audit_logger.py
├── cloud/              # Google Drive OAuth 2.0 raw sync & offline cache
├── config/             # app_settings.json, active_code_registry.json, reference_manifest.json
├── tests/              # L1-L5, GUI, migration, and E2E test suites
├── .agents/agents/     # Subagent role specifications
├── AGENTS.md
├── rules.md
├── proposed.md
├── state_summary.txt
├── context_guide.txt
├── main.py
├── requirements.txt
└── README.md
```

---

# 16. CONSOLIDATED V1.0 COMPLETION ROADMAP (PHASE 0 TO PHASE 10)

Full work-package specifications, tasks, and acceptance gates are detailed in [`proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md`](https://drive.google.com/file/d/1KlEES_QYXMFnwYAKwqdathM7LalXiBq8/view?usp=drivesdk) Sections 10 & 11:

1. **Phase 0 (`WP-0` — Read-Only Baseline Audit):** Owner: `Primary Agent` + `qa-verifier`. Verify `F-01..F-22`, map imports/IDs/SQLite v1 schema/UI flows, capture baseline screenshots and test/numerical baselines, produce file-level `KEEP / REFACTOR / ADD / DEFER` plan.
2. **Phase 1 (`WP-0b` — P0 Live-Data Safety Hotfix):** Owner: `desktop-app`. Remove sample values, sample sheet/table, and `c_delta=0.69` fallback from live new-item paths so blank items start `INCOMPLETE`.
3. **Phase 2 (`WP-1a` + `WP-2` + `WP-3` — Foundational Contracts in Parallel):**
   - `Phase 2A (WP-1a)`: `cloud-data` — SQLite Schema v2 migration (`PRAGMA user_version = 2`) with backup and v1 revision preservation tests.
   - `Phase 2B (WP-2)`: `calculation-engine` — `CalcStep`, `Quantity`, `RefSpec`, restricted math markup validator, additive `CalculationResult.trace`.
   - `Phase 2C (WP-3)`: `desktop-app` — `ModuleRegistry`, `ModuleSpec`, `FieldSpec`, unify dispatch/catalog, gate Steel & Concrete as `COMING_SOON`.
4. **Phase 3 (`WP-1b` + `WP-4` — Item Services & `WorkspaceController`):** Owners: `desktop-app` + `cloud-data`. Implement `ProjectService` item/group APIs and pure-Python `WorkspaceController` (`Run` vs. `Save Revision`, `is_stale` hashing).
5. **Phase 4 (`WP-5` + `WP-6` — Sidebar Tree & Schema-Driven `WorkspaceHost`):** Owner: `desktop-app`. Persistent project tree with drag-and-drop reorder, context menu, and schema-driven `WorkspaceHost`/`InputForm` while keeping legacy workspaces until parity passes.
6. **Phase 5 (`WP-7` + `WP-8` + `WP-9` — Math Renderer, `DiagramSpec` & Trace Migration):** Owners: `desktop-app` + `calculation-engine`. Vendored offline KaTeX in Panel 3 (with packaging spike & fallback), `DiagramSpec` builders for C&C and Wood with input-reactive geometry, and `CalcStep` trace backfill across Day 13/14 modules with 100% numerical parity.
7. **Phase 6 (`WP-11` + `Day 15` & `Day 16` — Steel & Concrete/CMU Engines):** Owner: `calculation-engine` (+ `desktop-app` registry/diagrams, `qa-verifier`). Implement `core/aisc360/` (Bolts, Welds, Shear Tab incl. HSS wall checks, Angles, Base Plate, HSS-to-HSS) and `core/aci318/` + `core/tms402/` (Concrete Anchors, CMU Breakout, Embedded Steel Post) natively on the new contracts.
8. **Phase 7 (`WP-10` + `Day 18` — Ordered Multi-Item Reports & Exporter Completion):** Owner: `desktop-app`. Ordered multi-item PDF/XLSX export consuming `trace` and `DiagramSpec`, resilient multi-header CSV parsing, and HUS210-2 verification.
9. **Phase 8 (`Day 17` — Google Drive Raw-File Synchronization):** Owner: `cloud-data`. OAuth 2.0 + `keyring`, raw KB file sync, SHA-256 conflict preservation, non-blocking offline mode.
10. **Phase 9 (`Day 19` — Full QA & Windows Packaging):** Owner: `qa-verifier` + all owners. Execute all 8 QA categories and build/verify standalone PyInstaller Windows package on a clean environment.
11. **Phase 10 (`Day 20` — Final UAT & V1.0 Release Sign-Off):** Owner: `Primary Agent` + `qa-verifier` + User. Complete Section 16 Release Gate checklist, update docs, and tag V1.0.

---

# 17. ACCEPTANCE CRITERIA

The V1.0 application is complete only when all criteria in SAD Table 17 (`AC-01` to `AC-15`) and Section 16 of `proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md` are evidenced as PASS.

---

# 18. ARCHITECTURAL DECISIONS (`ADR-01` TO `ADR-18`)

| ID | Decision | Rationale |
|---|---|---|
| ADR-01 | Windows desktop application | Matches deployment platform |
| ADR-02 | Python + PySide6 (Frozen 4-Panel UI) | Maintainable desktop framework with locked engineering layout |
| ADR-03 | Deterministic Python Calculation Engine | Ensures reproducible engineering calculations |
| ADR-04 | CSV and Markdown remain primary Knowledge Base formats | Preserves verified reference library |
| ADR-05 | SQLite (Schema v2) for local project records | Local structured storage for projects, groups, ordered items, drafts & revisions |
| ADR-06 | Google Drive for raw Knowledge Base synchronization | Preserves raw `.csv`/`.md` files (`application/octet-stream`) |
| ADR-07 | Local cache for offline calculation | Prevents cloud availability from blocking engineering work |
| ADR-08 | Multi-item PDF/XLSX export consuming shared trace | Guarantees GUI, PDF, and Excel display identical equations and results |
| ADR-09 | No AI integration in V1 runtime | Keeps runtime 100% deterministic and offline-capable |
| ADR-10 | 8-category verification required before release | Establishes engineering and software quality gates |
| ADR-11 | Clean Architecture / `ReferenceDataPort` decoupling | Eliminates bidirectional `gui <-> core` and `core <-> app.services` coupling |
| ADR-12 | Single `ModuleRegistry` (`ModuleSpec`, `FieldSpec`) | Eliminates catalog drift across dialog, forms, dispatcher, and diagrams |
| ADR-13 | Structured `CalcStep` trace & restricted LaTeX math grammar | One calculation trace drives Panel 3, PDF, and XLSX |
| ADR-14 | Vendored offline KaTeX (`QWebEngineView`) + rich-text fallback (`D-1`) | True mathematical notation offline with measured packaging spike |
| ADR-15 | Blank required inputs (`INCOMPLETE` start) & zero silent sample defaults (`D-2`) | Prevents uncomputed sample numbers from appearing as real design outputs |
| ADR-16 | Separate `is_stale` flag (`D-3`) | Preserves the 5 locked SAD 8.4 statuses while flagging edited/outdated state |
| ADR-17 | Native Steel/Concrete implementation after `WP-2`/`WP-3` (`D-5`, `D-6`) | Avoids building new module-specific workspaces on legacy duplicated structure |
| ADR-18 | Local-authoritative SQLite vs. Raw KB Cloud Sync boundary (`D-7`) | Keeps project SQLite local while syncing raw KB reference files via Google Drive |

---

# 19. KEY RISKS AND MITIGATION

See Section 15 of `proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md` for the complete 12-item risk and mitigation register covering schema migration backups, UI freeze screenshot regression, compatibility shims, trace numerical parity, KaTeX packaging spikes, stale-force prevention, and environment provisioning.

---

# 20. FINAL ARCHITECTURE SUMMARY

- **Knowledge Base (`database/`, `procedures/`)** = Protected Engineering Reference (accessed via `ReferenceDataPort`)
- **Calculation Engine (`core/`)** = Pure Deterministic Engineering Mathematics & `CalcStep` Trace
- **Application Layer (`app/`)** = `ModuleRegistry`, `WorkspaceController`, Services & Rendering Projections
- **GUI (`gui/`)** = Frozen 4-Panel PySide6 User Interface
- **Storage (`storage/`)** = SQLite Schema v2 Local Project, Group, Draft & Immutable Revision Store
- **Cloud Sync (`cloud/`)** = Google Drive Raw Reference File Synchronization
- **Export Engine (`exporters/`)** = Ordered Multi-Item PDF & XLSX Deliverables

**Immediate Next Action:** Dispatch **Phase 0 (`WP-0`)** read-only baseline audit to `Primary Agent` and `qa-verifier`, followed sequentially by `Phase 1 (WP-0b)` through `Phase 10 (Day 20)`.
