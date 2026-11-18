# ACP-001 — Architecture Change Proposal
## Project-Scoped Calculation Items, Structured Calculation Trace, and Schema-Driven Workspaces

**Project:** `structural-engineering-kb` (Standalone US Structural Engineering Calculation Application)
**Baseline:** `proposed.md` (SAD v1.0)
**Date:** November 17, 2026
**Status:** DRAFT. Not approved. Do not implement until the user approves in writing (see Section 7).
**Audience:** Primary Agent (Tech Lead), `desktop-app`, `calculation-engine`, `cloud-data`, `qa-verifier`

---

## 0. Agent Protocol

1. Read `rules.md`, `proposed.md`, and `state_summary.txt` before any task (AGENTS.md pre-work protocol).
2. This document does **not** modify `proposed.md`, `rules.md`, the Knowledge Base (`database/`, `procedures/`), or any locked file. It requests approval to amend specific SAD sections (Section 7).
3. Stay in your lane (AGENTS.md role table). Each work package in Section 4 names its owner. Escalate to the Primary Agent instead of guessing.
4. Every work package must report created/modified files and attach test evidence.
5. No engineering data, code provisions, or design assumptions may be invented. If a value is not in the KB or in an approved input, the calculation is `INCOMPLETE`.

---

## 1. Locked UI Design (UI Freeze)

The user has approved the mockup below. Implementation may change **internals only**. Visual structure, labels, and interactions must stay as listed.

| Area | Locked behavior |
|---|---|
| Header bar | Hamburger button, dynamic calculation title, segmented `ASD | LRFD` toggle on the right |
| Sidebar | Collapsible, 232 px expanded and 48 px rail, ~120 ms animation, hamburger toggle in header and rail |
| Sidebar (expanded) | Logo/subtitle, navigation (Dashboard, Projects, Reports, Settings), `PROJECT` label and name, blue full-width `+ Add Calculation`, calculation list grouped under user-defined group headers, each row showing name and DCR/status text, footer hint "Drag to reorder. Order reflects in reports." |
| Sidebar (rail) | Hamburger, nav icons, blue `+` button, divider, numeric badge chips (`01`, `02`, `03!`) with status underline, hover flyout (title, module, DCR, status) |
| Workspace | Four panels: (1) Inputs on the left, 280 to 380 px, with `Run Calculation` and `Save Revision` below; right column with (2) Diagram, (3) Calculation Sheet, (4) Summary; splitters between right-column panels |
| Panel 2 | Live diagram with dimension lines (symbols with subscripts and values), force arrows, amber warning pill when a detailing limit is violated |
| Panel 3 | Code-basis banner, then rows of `equation -> substitution -> result` with a right-aligned code-reference column. Governing code and references are merged here (there is no separate references panel). Symbols use true math notation with subscripts and superscripts |
| Panel 4 | Status pill (`PASS`, `FAIL`, `REQUIRES REVIEW`, `INCOMPLETE`, `INVALID INPUT`), governing limit state, DCR gauge, 7-column table (`Step`, `Limit state check`, `Governing clause`, `Demand`, `Capacity`, `DCR`, `Status`) |
| Add Calculation dialog | Three columns: categories (Recent, Loads, Wood, Steel, Concrete/CMU) | templates | preview with `Name`, `Group`, `Design method`, `Start from` (Blank or Duplicate); `Cancel` and `Add & Open` |
| Organization model | Option 1: user adds calculations and orders them freely. Material categories exist only as the dialog catalog, filters, and optional group-by view |

**Not locked:** any sample numbers, sample clause references, or sample text shown in the mockup. Those were illustrative only (see F-01).

---

## 2. Review of the Current Architecture

Scope of this pass: `README.md`, `AGENTS.md`, `rules.md`, `proposed.md`, `state_summary.txt`, `context_guide.txt`, `gui/main_window.py`, `gui/widgets/base_workspace.py`, `gui/widgets/wood_workspace.py`, `core/common/calculation_result.py`, `app/services/calculation_service.py`, `storage/repositories/project_repository.py`.
Not reviewed in this pass: `gui/dialogs/add_calculation_dialog.py`, `gui/widgets/cc_workspace.py`, `app/services/project_service.py`, `report_service.py`, `knowledge_base_service.py`, `exporters/`, `core/` engines, `tests/`. The Primary Agent should confirm findings against those files during WP-0.

### 2.1 What is sound and must be preserved

- Layering matches SAD Section 3: GUI calls services, services call `core/`, no equations in GUI code.
- `CalculationResult` is a single common contract with explicit statuses and `LimitStateResult` records.
- Immutable revisions (inputs, results, revision log) with atomic writes in SQLite.
- Knowledge Base is separate from project data, protected, and SHA-256 verified (92 files).
- Strict ASD/LRFD separation and a `design_method` stored per calculation.
- Passing suite of 69 tests with vertical slices for C&C and Wood.

### 2.2 Findings

| ID | Sev | Finding | Evidence | Impact |
|---|---|---|---|---|
| F-01 | P0 | Illustrative mockup content is hard-coded as production behavior: sample input values, a fully written sample calculation sheet, a sample limit-state table, `c_delta = 0.69` fallback, and a default warning note string. The sample clause numbers follow older NDS numbering while the KB and engine are NDS 2024. | `base_workspace.py`: `_populate_sample_inputs`, `_populate_sample_calc_sheet`, `_populate_sample_table`, `display_results` (`c_delta=0.69`); `wood_workspace.py`: `summary_note` default | A user can see numbers that were never computed. Violates "never invent engineering data" and traceability (SAD 6.7) |
| F-02 | P0 | Sidebar items are an in-memory hard-coded list. `+ Add Calculation` appends to that list only. Item IDs use `len(list)+1`. Nothing is persisted or loaded from `ProjectService`. | `main_window.py`: `self.calculations`, `_on_add_calculation_clicked` | Items disappear on restart. IDs collide after deletion |
| F-03 | P0 | One workspace instance per module type, routed by a hard-coded `page_index`. Workspaces hold their own state, so two items of the same module type cannot keep different inputs. Steel and Concrete pages are empty placeholders. | `main_window.py` stacked pages; `wood_workspace.py` `_input_edits` | The approved "many connections per project" workflow cannot work |
| F-04 | P1 | Storage has no ordering or grouping. Calculations are listed by `updated_at DESC`. There is no group table, no sort order, no draft inputs, and no schema version. The footer hint promises drag-to-reorder, which does not exist. | `project_repository.py`: `list_calculations_for_project`, schema DDL | User-controlled order and report order cannot be stored |
| F-05 | P1 | Calculation Sheet cannot render math. `equation_latex` is shown as raw text in `<code>`. `substitution_str` is a free string. `intermediate_results` is an unordered `key = value` dictionary. References are free-text clause strings with no link to KB reference IDs. | `base_workspace.py` `display_results`; `calculation_result.py` | Locked Panel 3 design cannot be met. Reports cannot reuse the same trace |
| F-06 | P1 | Three independent catalogs of calculation types: Add dialog templates, `MODULE_CONFIGS` in the wood workspace, and `CalculationService._registry` plus a separate `list_supported_modules`. Registry also contains duplicate aliases. | `calculation_service.py`, `wood_workspace.py`, `add_calculation_dialog.py` | Drift risk; every new module (Steel, Concrete) must be added in three places |
| F-07 | P1 | Inputs are free-text line edits with underscore labels (`F_yb`), no units, no KB-backed dropdowns, no field-level validation. | `wood_workspace.py` `MODULE_CONFIGS` and `_populate_sample_inputs` | Does not match the approved mockup (symbols, species dropdowns, units) |
| F-08 | P1 | Diagram code is bolt-specific in the base class and uses an `if` chain in the subclass. Geometry and drawing are coupled, so it cannot be tested without Qt or exported to PDF. Steel and Concrete placeholders inherit the bolt drawing. | `base_workspace.py` `DiagramWidget`; `wood_workspace.py` `WoodDiagramWidget` | Not extensible; warnings are hard-coded |
| F-09 | P1 | Code edition drift: window titles and banners say "NDS 2018" while the engine and KB are NDS 2024. Titles are hard-coded strings instead of values from `active_code_registry.json`. | `main_window.py` titles; `rules.md`; `state_summary.txt` | Wrong code edition shown to the engineer |
| F-10 | P2 | GUI imports `core.common.calculation_result` directly. AGENTS.md says GUI talks only to `app/services/`. | `main_window.py`, `base_workspace.py` imports | Layer rule violated; use DTOs in `app/models/` |
| F-11 | P2 | Status bar text is hard-coded ("66 Tables / 26 Procedures", project name). | `main_window.py` `_setup_status_bar` | Can show stale or false integrity status |
| F-12 | P2 | Hidden widgets kept "for backward compatibility with existing tests" (`radio_asd`, `radio_lrfd`, `ref_text`). | `base_workspace.py` | Dead UI state; update tests instead |
| F-13 | P2 | Navigation icons are emoji glyphs; the Drive copy of `main_window.py` shows corrupted bytes in those strings. | `main_window.py` `nav_items`, `rail_icons` | Verify UTF-8 handling; replace with bundled SVG icons |
| F-14 | P2 | Documentation drift: `README.md` still says CustomTkinter; `context_guide.txt` lists outdated Drive file IDs for `state_summary.txt`, `rules.md`, `proposed.md`. | `README.md`, `context_guide.txt` | Agents may load the wrong file |
| F-15 | P2 | Project-level defaults are missing (design method, code editions). The ASD/LRFD toggle acts on the active page only and is not persisted per item. | `main_window.py` `set_active_design_method`; repository schema | Inconsistent method per item |

---

## 3. Target Architecture

### 3.1 Principles

1. Additive to SAD v1.0. Existing tables, `CalculationResult` fields, and the 69 tests keep working.
2. One source of truth for each concept: module catalog (registry), calculation trace, diagram geometry, item ordering.
3. GUI is a thin view. All state transitions live in `app/` (pure Python, no PySide imports) so they can be tested without Qt.
4. Revisions remain immutable. Ordering, grouping, and drafts are mutable metadata.

### 3.2 Component View

```text
gui/                              app/                               core/ + KB
------------------------------    -------------------------------    ------------------------
SidebarWidget (tree + rail)  -->  ProjectService (items, groups)      CalculationResult
WorkspaceHost                -->  WorkspaceController (per item)      CalcStep trace (new)
  WorkspaceView (4 panels)        ModuleRegistry (ModuleSpec)         calc functions (existing)
    InputForm (schema)            CalculationService                  KnowledgeBaseService
    DiagramCanvas            <--  diagram builders -> DiagramSpec     (CSV + manifest, locked)
    CalcSheetView (KaTeX)    <--  rendering/ (math markup renderers)
    SummaryPanel                  ReportService (ordered items)
AddCalculationDialog         -->  ModuleRegistry.catalog()
```

### 3.3 Data Model and Migration (cloud-data)

Use `PRAGMA user_version` (current implied v1, target v2). Migrations are additive and must run on an existing database without touching `calculation_inputs`, `calculation_results`, `calculation_revisions`.

```sql
CREATE TABLE IF NOT EXISTS calculation_groups (
  group_id     TEXT PRIMARY KEY,
  project_id   TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  sort_order   INTEGER NOT NULL,
  is_collapsed INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);

ALTER TABLE calculations ADD COLUMN group_id TEXT REFERENCES calculation_groups(group_id) ON DELETE SET NULL;
ALTER TABLE calculations ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE calculations ADD COLUMN item_number INTEGER;          -- monotonic per project, never reused
ALTER TABLE calculations ADD COLUMN draft_inputs_json TEXT;       -- autosaved working inputs
ALTER TABLE calculations ADD COLUMN draft_updated_at TEXT;
ALTER TABLE calculations ADD COLUMN last_dcr REAL;                -- cache of latest run, non-authoritative
ALTER TABLE calculations ADD COLUMN last_input_hash TEXT;         -- hash of inputs + method + defaults + KB manifest
ALTER TABLE calculations ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0;  -- soft delete

CREATE TABLE IF NOT EXISTS project_settings (
  project_id              TEXT PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
  default_design_method   TEXT NOT NULL DEFAULT 'ASD',
  code_registry_json      TEXT,   -- snapshot of editions in force for this project
  updated_at              TEXT NOT NULL
);
```

Rules:
- Display label (`C-01`, `C-02`, ...) is computed from list position at render time. `item_number` is the stable audit identifier. Reports print the display label and may print `item_number` in the revision block.
- Deleting an item is a soft delete with confirmation. Revisions are retained.
- Existing databases are backed up to `storage/backups/` before migration.

### 3.4 Services (desktop-app)

`ProjectService` additions (all return DTOs from `app/models/`):

```python
list_items(project_id) -> list[ItemSummary]            # ordered by group.sort_order, item.sort_order
list_groups(project_id) -> list[GroupSummary]
add_item(project_id, module_id, title, group_id=None, start_from=None) -> ItemSummary
duplicate_item(item_id) -> ItemSummary                  # copies draft inputs, not revisions
move_item(item_id, group_id, index) -> None            # single transaction, renumbers sort_order
rename_item(item_id, title) -> None
delete_item(item_id) -> None                           # soft delete
create_group(project_id, name) -> GroupSummary
rename_group(group_id, name) / move_group(group_id, index) / set_group_collapsed(group_id, bool)
get_project_defaults(project_id) / set_project_defaults(project_id, defaults)
```

`WorkspaceController` (new, `app/controllers/`, pure Python):

```python
load(item_id) -> WorkspaceViewModel
edit_field(key, raw_text) -> WorkspaceViewModel          # parse, validate, update diagram, autosave draft (debounced)
set_design_method(method) -> WorkspaceViewModel
run() -> WorkspaceViewModel                              # CalculationService, no revision created
save_revision(change_notes) -> WorkspaceViewModel        # immutable revision
```

`WorkspaceViewModel` contains: item metadata, form state (values, units, per-field validation messages), `DiagramSpec`, calculation sheet rows (from `CalcStep`), summary (status, governing limit state, DCR, limit-state rows), flags (`is_dirty`, `is_stale`, `warnings`).

**Stale flag:** SAD 8.4 fixes the status list (`PASS`, `FAIL`, `REQUIRES REVIEW`, `INCOMPLETE`, `INVALID INPUT`). Do not add an `OUTDATED` status. Represent it as `is_stale = (last_input_hash != current_hash)`; the sidebar shows a small marker next to the DCR.

### 3.5 ModuleRegistry (desktop-app)

One registry replaces the dialog catalog, `MODULE_CONFIGS`, `_registry`, and `list_supported_modules`.

```python
@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str                 # plain text
    symbol: str | None         # math markup, e.g. "t_{m}"
    unit: str | None           # validated by core.common.units
    kind: Literal["float", "int", "enum", "bool", "text"]
    section: str               # "Fastener", "Main member", ...
    enum_source: EnumSource | None   # KB-backed (table + column) or literal tuple
    required: bool = True
    default: Any = None        # see policy below
    default_ref: str | None = None   # code reference when a code-stated default is allowed
    diagram_bind: bool = False
    visible_if: str | None = None

@dataclass(frozen=True)
class ModuleSpec:
    module_id: str
    aliases: tuple[str, ...]
    category: Literal["loads", "wood", "steel", "concrete_cmu"]
    title: str
    description: str
    code_family: str                 # e.g. "NDS", resolved to edition via active_code_registry
    calc_fn: Callable[..., CalculationResult]
    fields: tuple[FieldSpec, ...]
    diagram_id: str | None
    procedure_md: str                # path in procedures/, must exist in reference_manifest
    maturity: Literal["verified", "preview"]
```

**Default policy:** geometry, material, and demand inputs have no silent defaults. A new item starts `INCOMPLETE`. A default is allowed only when the code states one and `default_ref` cites it. This is an open decision (D-2).

Registry consistency test: every `procedure_md` and every `enum_source` table exists in `config/reference_manifest.json`; every `module_id` and alias is unique.

### 3.6 Calculation Trace and Math Markup (calculation-engine, desktop-app)

Extend `CalculationResult` additively with `trace: list[CalcStep]`. Keep `equation_latex` and `substitution_str` for backward compatibility; renderers fall back to them when `trace` is empty.

```python
@dataclass(frozen=True)
class RefSpec:
    code: str            # "NDS"
    edition: str         # "2024"
    kind: Literal["table", "section", "equation", "figure"]
    locator: str         # "12.3.3"
    kb_reference_id: str | None   # resolves to manifest entry and CSV when a table exists

@dataclass(frozen=True)
class CalcStep:
    step_id: str
    stage: Literal[1, 2, 3, 4]    # Rule 5 load-path stage
    title: str
    symbolic: str                 # math markup
    substituted: str              # math markup with numbers
    value: float
    unit: str | None
    refs: tuple[RefSpec, ...]
    note: str = ""
```

Engines emit steps as they compute. The UI and exporters never recompute or reformat numbers.

**Math markup** is a restricted LaTeX subset: `_`, `^`, `\frac`, `\sqrt`, `\cdot`, `\times`, `\leq`, `\geq`, `\phi`, `\Omega`, `\Delta`, `\theta`, `\lambda`, `\parallel`, `\prime`, `\text{}`, `\left( \right)`. A parser in `core/common/math_markup.py` validates strings at construction. Renderers (`app/rendering/`):

| Target | Output |
|---|---|
| Calc Sheet (Qt) | KaTeX HTML (fractions and roots stacked) |
| PDF (ReportLab) | Paragraph markup with `<sub>` and `<super>`; fractions as `(a)/(b)` |
| XLSX (openpyxl) | Rich-text runs with real subscript/superscript, Rule 6 style: roots as `(a)^(1/2)`, multiplication as `.` |

### 3.7 Diagram Specification (desktop-app)

```python
DIAGRAM_BUILDERS: dict[str, Callable[[dict, CalculationResult | None], DiagramSpec]]
# DiagramSpec = shapes + dimensions + force arrows + notes; model units only, no Qt types
```

- `DiagramCanvas` (QPainter) draws any `DiagramSpec` with schematic scale: member thickness is clamped for legibility while labels show true values.
- Dimension labels use math markup (`t_{m} = 1.5 in` style), so subscripts match the Calc Sheet.
- Warning pill content comes from `result.warnings` and limit-state flags. No hard-coded notes or factors.
- The same `DiagramSpec` can render to ReportLab for the PDF.
- Modules with no builder show an empty-state message, never another module's drawing.

### 3.8 GUI Composition (desktop-app)

```text
gui/
  main_window.py              shell only: header, sidebar, host, status bar
  sidebar/                    sidebar_widget.py, project_tree_view.py, project_tree_model.py, rail_widget.py
  workspace/                  workspace_host.py, workspace_view.py, input_form.py,
                              diagram_canvas.py, calc_sheet_view.py, summary_panel.py
  dialogs/                    add_calculation_dialog.py, reference_popup.py
  assets/                     icons/*.svg, katex/ (vendored, offline)
```

- `ProjectTreeModel` (QStandardItemModel or custom) with `InternalMove` drag and drop. Drops call `ProjectService.move_item`; the model refreshes from the service result, never from local state. Rail chips are generated from the same model.
- `WorkspaceHost` keeps one `WorkspaceView` and swaps item state through `WorkspaceController.load(item_id)`. No per-module workspace subclasses are needed. `cc_workspace.py` and `wood_workspace.py` are retired after parity tests pass.
- `CalcSheetView` uses `QWebEngineView` with vendored KaTeX and `QWebChannel`. Clicking a reference opens `ReferencePopup` with the KB table preview and file hash from `KnowledgeBaseService`. Fallback: if QtWebEngine is unavailable, render sub/superscripts with `QTextEdit` rich text (no stacked fractions). Decision D-1.
- Status bar values come from `KnowledgeBaseService` manifest audit and `ProjectService`.
- GUI imports only `app/` (services, controllers, models). Icons are bundled SVG files.

### 3.9 Item Lifecycle

```text
Add (Blank/Duplicate) -> draft inputs autosaved -> Run (in-memory result, last_dcr cached)
   -> Save Revision (immutable revision) -> edit inputs/method/defaults/KB change -> is_stale = true
```

`Run` never creates a revision. `Save Revision` does. Switching ASD/LRFD updates the item's `design_method`, marks it stale, and re-runs; it never mixes methods in one check.

### 3.10 Reports

`ReportService` accepts an ordered list of item IDs (tree order by default, with checkboxes in the Reports page). The PDF/XLSX builders consume `trace` for formulas and `DiagramSpec` for figures. Order, display labels, and revision numbers appear in the table of contents.

---

## 4. Work Packages

| WP | Owner | Scope | Depends on | Deliverables and acceptance |
|---|---|---|---|---|
| WP-0 | Primary Agent | Governance and cleanup. Obtain approval (Section 7). Confirm findings on files not yet reviewed. Fix F-14 doc drift. | none | Signed-off ACP-001; `state_summary.txt` updated; README and context guide corrected |
| WP-0b | desktop-app | P0 hotfix for F-01: remove all sample values, sample sheet, sample table, `c_delta` fallback, and default notes. Fresh workspace shows blank inputs, `INCOMPLETE`, empty sheet. | WP-0 | No numeric engineering literals rendered before a run; test proves it |
| WP-1a | cloud-data | Schema v2 migration (3.3) with backup and `user_version`. | WP-0 | Migration test from a v1 fixture preserves all revisions byte for byte; idempotent |
| WP-1b | desktop-app | `ProjectService` item/group APIs (3.4), DTOs in `app/models/`. | WP-1a | Unit tests for add, duplicate, move across groups, reorder, soft delete, renumbering, concurrency |
| WP-2 | calculation-engine | `CalcStep`, `RefSpec`, `math_markup` parser, additive `CalculationResult.trace`. | WP-0 | Parser tests; existing 69 tests unchanged |
| WP-3 | desktop-app | `ModuleRegistry`, `ModuleSpec`, `FieldSpec`; migrate Day 13/14 modules; remove duplicate catalogs. | WP-0 | Registry consistency test; `CalculationService` dispatch via registry; aliases preserved |
| WP-4 | desktop-app | `WorkspaceController`, view model, draft autosave, stale flag. | WP-1b, WP-3 | Controller tests without Qt; stale flag test |
| WP-5 | desktop-app | Sidebar tree and rail, `ProjectTreeModel` drag and drop, context menu (Rename, Duplicate, Move to group, Delete), Add dialog from registry; header title from item. | WP-1b, WP-3 | pytest-qt tests; items persist across restart; visuals match Section 1 |
| WP-6 | desktop-app | Schema-driven `InputForm`, `WorkspaceHost`, `SummaryPanel`; retire `cc_workspace.py` and `wood_workspace.py` after parity. | WP-4, WP-5 | Existing vertical-slice tests ported and green |
| WP-7 | desktop-app | `app/rendering/` renderers, `CalcSheetView` with vendored KaTeX, `ReferencePopup`. | WP-2 | Golden tests for the three renderers; reference IDs resolve via manifest |
| WP-8 | desktop-app | `DiagramSpec`, builders (wood bolt first, then remaining Wood and C&C), `DiagramCanvas`. | WP-3 | Builder unit tests without Qt; warning pill driven by result |
| WP-9 | calculation-engine | Emit `trace` in Day 13/14 modules. Numerical outputs and benchmark tests must not change. | WP-2 | Benchmark and regression tests unchanged; every step has resolvable `refs` |
| WP-10 | desktop-app | Reports consume ordered items, `trace`, and `DiagramSpec`; XLSX per Rule 6; PDF per SAD 11.3. | WP-7, WP-8, WP-9 | Export of a 3-item project matches tree order; subscripts correct in both formats |
| WP-11 | calculation-engine | Day 15 (AISC) and Day 16 (ACI/TMS) modules written natively with `trace`, registered through `ModuleSpec`. Can start engine work after WP-2. | WP-2, WP-3 | Benchmarks per SAD 12.2; no GUI work needed beyond registry entries |
| WP-12 | qa-verifier | Read-only verification across all WPs; maintains the test checklist (Section 5). | continuous | Report per WP with evidence |

Suggested order: WP-0, WP-0b, then WP-1a, WP-2 and WP-3 in parallel, then WP-1b, WP-4, WP-5, WP-6, then WP-7, WP-8, WP-9, then WP-10; WP-11 follows WP-2 and WP-3. Steel and Concrete should be implemented on the new rails, not on the old workspace classes.

---

## 5. Acceptance Criteria and Test Checklist

| ID | Criterion |
|---|---|
| ACP-AC-01 | Items, groups, and order persist across application restarts |
| ACP-AC-02 | Two items of the same module type hold different inputs and results simultaneously |
| ACP-AC-03 | Drag and drop reorders items and moves them between groups; report order equals tree order |
| ACP-AC-04 | Duplicate copies draft inputs and creates no revision history |
| ACP-AC-05 | A fresh item shows no numeric engineering values and status `INCOMPLETE` |
| ACP-AC-06 | Calc Sheet shows math with subscripts and superscripts; every row lists its code references; each reference resolves through `reference_manifest.json` |
| ACP-AC-07 | PDF and XLSX render the same trace with correct sub/superscripts |
| ACP-AC-08 | Diagram for each module comes from its `DiagramSpec`; no module shows another module's drawing |
| ACP-AC-09 | Editing inputs, design method, project defaults, or KB manifest marks an item stale; statuses stay within the SAD 8.4 list |
| ACP-AC-10 | Migration v1 to v2 preserves all revisions; DB backup is created |
| ACP-AC-11 | UI matches Section 1 (screenshots attached by `qa-verifier`) |
| ACP-AC-12 | GUI modules import nothing from `core/` or `cloud/`; static test enforces it |
| ACP-AC-13 | Existing 69 tests pass, then ported where retired widgets are removed |

Test types: unit (`app/`, parser, registry), migration fixtures, pytest-qt with `QT_QPA_PLATFORM=offscreen`, golden-file tests for renderers, benchmark and regression for engines (unchanged numbers), end-to-end for `Add -> Input -> Run -> Save Revision -> Export`.

---

## 6. Protected Items and Constraints

- Do not modify `database/`, `procedures/`, `config/reference_manifest.json` (except via the KB curator and the five-step verification), `rules.md`, or `proposed.md` outside Section 2.1.
- US Customary units only; code and files in US structural engineering English; user chat in Vietnamese.
- No AI or LLM dependency at runtime. KaTeX and any other web assets are vendored locally; no CDN or network at runtime.
- GUI never calls `core/` equations or Google Drive APIs.
- Before replacing any file on Google Drive, back it up to `backup/` per Rule 3.

---

## 7. SAD Impact and Approval Request

Approval is requested to amend these sections of `proposed.md` after the user confirms. Until then this document is a proposal only.

| SAD section | Proposed change |
|---|---|
| 6.4 Calculation Result Standard | Add optional `trace` field (additive) |
| 8.1 and 8.2 Main Interface and Initial Modules | Sidebar shows the project tree; module categories move to the Add Calculation catalog |
| 8.3 Calculation Workspace | Rename panels to Inputs, Diagram, Calculation Sheet (with references), Summary |
| 9.2 and 9.3 Storage | SQLite is authoritative for project data; document schema v2 (3.3). The folder layout in 9.2 is an export layout |
| 15 Repository Structure | Add `app/registry/`, `app/controllers/`, `app/rendering/`; replace module-named GUI folders with `gui/sidebar/`, `gui/workspace/`, `gui/dialogs/`, `gui/assets/` |
| 18 Architectural Decisions | Add ADR-11 to ADR-14 below |

Proposed ADRs:

| ID | Decision | Rationale |
|---|---|---|
| ADR-11 | Project-scoped, user-ordered calculation items with optional groups | Matches engineering workflow and report order |
| ADR-12 | Structured calculation trace with a single math markup rendered to UI, PDF, and XLSX | One computation, three outputs; traceable references |
| ADR-13 | Module registry as the single source of truth for catalog, forms, dispatch, and diagrams | Removes drift; Steel and Concrete need only registry entries |
| ADR-14 | QtWebEngine with vendored KaTeX for the Calculation Sheet, with a rich-text fallback | True math notation offline |

---

## 8. Decisions Needed from the User

| ID | Decision | Recommendation |
|---|---|---|
| D-1 | Calculation Sheet renderer: QtWebEngine and KaTeX (adds roughly 100 MB or more to the PyInstaller build) or QTextEdit-only (no stacked fractions) | QtWebEngine and KaTeX |
| D-2 | Input defaults: blank required inputs (item starts `INCOMPLETE`) versus pre-filled sample values | Blank, except code-stated defaults with a citation |
| D-3 | Stale marker: separate `is_stale` flag versus adding `OUTDATED` to SAD 8.4 statuses | Separate flag |
| D-4 | Authorization to amend the SAD sections in Section 7 | Approve after review |
| D-5 | Sequencing of Day 15 and Day 16 against this work | Start engine work after WP-2 and WP-3; do not build new workspace classes |

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| QtWebEngine packaging size and PyInstaller hooks | Spike in WP-7 before committing; keep the rich-text fallback |
| Math markup grammar grows without control | Parser rejects unknown commands; additions require a QA-reviewed change |
| Retiring old workspaces breaks the 69 tests | Parity tests first, then port tests, then delete |
| Drag and drop and ordering races | Single-transaction `move_item`; model refreshes from service results |
| Trace backfill alters numbers | WP-9 acceptance requires unchanged benchmark outputs |
| Hidden demo values reappear | ACP-AC-05 test on every new module |
