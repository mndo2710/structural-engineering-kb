# STRUCTURAL ENGINEERING CALCULATION APPLICATION
## Consolidated Architecture Review, Change Proposal & V1.0 Completion Roadmap

**Repository:** `mndo2710/structural-engineering-kb`  
**Baseline:** `proposed.md` — Software Architecture Document (SAD v1.0)  
**Review snapshot:** 17 November 2026  
**Branch:** `main`  
**Review mode:** Read-only review; no repository files changed  
**Proposal status:** DRAFT — implementation requires explicit approval  
**Primary objective:** Complete the application from the current Day 14 / pre-Day 15 state to a verified, packaged V1.0 release while preserving the approved UI exactly.

---

# 0. Executive decision

## 0.1 Overall conclusion

The current application has a sound technical foundation. **Do not rewrite it from scratch, do not change the technology stack, and do not redesign the approved user interface.** Continue with Python + PySide6, the deterministic Python calculation engine, the existing engineering Knowledge Base, SQLite project storage, and the existing Excel/PDF exporters.

The central issue is that the current implementation has progressed through two vertical slices (Components & Cladding and Wood) before all the application-wide workflows and data contracts have been completed. The result is a working foundation, but not yet a complete project-oriented calculation application.

The consolidated recommendation is to evolve the current layered architecture into a **lightweight Clean Architecture / Ports-and-Adapters design**, incrementally, with six foundations:

1. A persistent, project-scoped calculation-item model with independent inputs and results for each item.
2. One authoritative Module Registry for the calculation catalog, input schemas, calculation dispatch, supported status and diagram selection.
3. A structured calculation trace and reference model shared by the GUI, PDF and XLSX.
4. A schema-driven workspace and typed visualization model behind the existing four-panel UI.
5. Explicit application use cases for create, load, edit, run, save revision, duplicate, reorder and export.
6. A staged engineering verification and release process covering all V1 modules, offline operation, cloud reference synchronization and Windows packaging.

## 0.2 What must not change

The approved PySide6 UI is **FROZEN**. Only internal architecture, data flow, rendering implementation and persistence behavior may change.

The following are non-negotiable:

- Keep the existing header, sidebar, navigation, four-panel workspace, Add Calculation dialog composition, established labels and interactions.
- Keep Panel 1 on the left; Panel 2 at the top-right; Panel 3 in the middle-right; Panel 4 at the bottom-right.
- Keep code basis and code references integrated into Panel 3 with the relevant calculation steps. Do not introduce a separate Reference Panel or a fifth panel.
- Keep the approved colors, typography, spacing, dimensions, proportions, visual hierarchy, sidebar behavior and panel positions.
- Do not replace PySide6 with another UI framework.
- Do not place engineering equations in GUI widgets, renderers or diagram code.
- Do not modify protected Knowledge Base data or locked governance files without the required approval.
- Do not introduce AI/LLM APIs as V1 runtime dependencies. Runtime calculation must remain deterministic and offline-capable.

## 0.3 Implementation principle

**Stabilize the data and application workflows first; then connect the unchanged UI to those workflows.** Do not build more module-specific workspaces on top of the existing duplicated structure. Complete the shared architecture rails first, then implement Steel and Concrete/CMU on those rails.

---

# 1. Current project position and definition of 100% completion

## 1.1 Current position from the repository state

The repository `state_summary.txt` identifies the following baseline:

| Workstream | Current documented status | Consolidated interpretation |
|---|---|---|
| SAD v1.0 and repository architecture baseline | Established | Preserve as the current governing baseline until approved amendments are made |
| Engineering Knowledge Base | Day 1–10 marked complete: 66 CSV tables and 26 Markdown procedures | Keep protected; verify integrity before release |
| Architecture foundation | Day 11–12 marked complete | Preserve and extend; do not rebuild |
| Components & Cladding vertical slice | Day 13 marked complete | Preserve calculation results; refactor integration incrementally |
| Wood Connections & Lateral vertical slice | Day 14 marked complete | Preserve calculation results; refactor integration incrementally |
| Steel connections | Day 15 marked ready / not implemented in current tree | Implement after Module Registry and structured trace foundations |
| Concrete / CMU anchorage | Day 16 pending | Implement after shared foundations |
| Google Drive synchronization | Day 17 pending | Implement after local/offline data workflows are stable |
| Full exporters | Day 18 pending | Complete against the common structured calculation trace |
| Full QA and Windows packaging | Day 19 pending | Run all verification levels and build/install test |
| Final UAT and V1.0 release | Day 20 pending | Release only after acceptance criteria are met |

The current repository tree contains `core/asce7/` and `core/nds/`, but not the planned `core/aisc360/`, `core/aci318/`, `core/tms402/` or `cloud/` packages. Steel and Concrete/CMU must therefore be considered unavailable for real calculation until their respective engines and verification tests are complete.

## 1.2 What “100% complete” means

The application is complete only when all of the following are delivered and verified:

1. All V1 calculation categories and their approved module scope are implemented, exposed through the catalog and independently benchmarked.
2. Project-scoped calculation items can be created, edited, duplicated, moved, reordered, soft-deleted and reopened after application restart.
3. Two or more calculation items of the same module type can hold different inputs, results, methods and revision histories at the same time.
4. The four-panel workspace displays the correct item state and remains visually identical to the approved mockup.
5. Panel 2 uses a typed diagram model; geometry responds to relevant input changes and calculated actions are from the deterministic engine.
6. Panel 3 displays true mathematical notation and traceable code references in the same calculation rows.
7. Panel 4 correctly displays status, governing checks and DCR where applicable, without forcing every engineering check into a DCR-only model.
8. Run and Save Revision are separate, reliable operations; saved revisions are immutable and reproducible.
9. PDF and XLSX consume the same calculation trace as the GUI and preserve report order from the project calculation list.
10. Knowledge Base integrity, reference provenance, offline functionality and Google Drive raw-file synchronization are verified.
11. All unit, reference-data, benchmark, regression, integration, GUI and end-to-end tests pass in the supported development environment.
12. The standalone Windows package installs and starts on a clean Windows environment and operates without internet access for local calculations.
13. Documentation, agent rules, dependency versions, release notes and known limitations match the actual released application.

A module is not “complete” merely because it appears in the Add Calculation dialog. It must have a supported input schema, deterministic calculation engine, references, diagram support where applicable, calculation trace, project workflow integration, reports and passing tests.

---

# 2. Consolidated review findings

This section combines the source review with the findings in `CLAUDE_ACP-001_architecture_change_proposal.md` and the existing `docs/review_audit_day14.md`.

Finding labels:

- **CONFIRMED:** Directly visible in the reviewed repository source or current project documentation.
- **REPORTED — VERIFY WP-0:** Identified in ACP-001 or the prior Day 14 audit; confirm against the complete current source before changing it.
- **EXPECTED ROADMAP GAP:** Not yet implemented by design according to the current state summary.

## 2.1 P0 — Correctness, persistence and workflow blockers

| ID | Finding | Evidence / current behavior | Required resolution |
|---|---|---|---|
| F-01 | Demonstration data can appear as real calculation output. **CONFIRMED** | `gui/widgets/base_workspace.py` contains sample form fields, a sample calculation sheet and sample limit-state table. Its `display_results()` passes a fixed `c_delta=0.69` to the base diagram update. `wood_workspace.py` builds a summary note from result values but includes a default presentation path. | A newly created calculation must start with blank required fields, `INCOMPLETE`, no numerical calculation sheet and no invented diagram actions. Sample values may remain only in explicit test/benchmark fixtures or a clearly separated demonstration mode. Remove fixed engineering fallback values from live display paths. |
| F-02 | Sidebar calculation items are not yet project-persistent. **CONFIRMED** | `gui/main_window.py` keeps `self.calculations` as an in-memory list. The Add Calculation handler appends to this list and assigns IDs from list length. It does not create a project calculation through `ProjectService`. | Replace the in-memory list as the source of truth with the project item APIs and SQLite persistence. Use stable identifiers; never derive identity from current list length. |
| F-03 | Workspace instances are organized by module family/page, not by individual calculation item. **CONFIRMED** | `MainWindow` contains one C&C workspace and one Wood workspace, routed by hard-coded `page_index`. The workspace keeps its own `_active_module_id` and `_input_edits`. | Implement a project-scoped item lifecycle and a workspace host that loads a selected item's saved draft/state. Multiple same-type items must remain independent. |
| F-04 | Add Calculation does not complete the project workflow. **CONFIRMED** | The current handler routes by a template-ID substring (`"wood"`) and appends a sidebar item. It does not persist the calculation container or explicitly select the corresponding module through a canonical catalog. | Create the item through `ProjectService`; resolve the module through the Module Registry; open the item by stable item ID; initialize it as blank or duplicate according to the dialog selection. |
| F-05 | Run and Save Revision are not fully connected to the visible item workflow. **CONFIRMED / VERIFY complete receiver wiring in WP-0** | `CalculationService.run_calculation()` supports optional persistence when given `calculation_id` and `auto_save_revision=True`, but the reviewed C&C/Wood execution calls do not pass a saved calculation ID. `BaseCalculationWorkspace` emits `saveRevisionRequested`; a complete active receiver is not evident in the reviewed path. | Implement separate `RunCalculation` and `SaveCalculationRevision` use cases. Run returns an in-memory result and does not create a revision. Save Revision writes an immutable revision explicitly. |
| F-06 | New input state can be masked by sample or fallback defaults. **CONFIRMED pattern; module-by-module audit required** | Several core engines use `inputs.get(key, numeric_default)`. Workspace inputs are currently line edits and can parse an invalid value back as a string. | Introduce a schema-driven required/default policy. Missing required user inputs must result in `INCOMPLETE` or `INVALID INPUT`. Only code-authorized defaults with an explicit reference may be applied silently. Preserve benchmark fixtures separately. |

## 2.2 P1 — Architecture and calculation presentation blockers

| ID | Finding | Evidence / current behavior | Required resolution |
|---|---|---|---|
| F-07 | Dependency direction is not consistently enforced. **CONFIRMED** | `gui/main_window.py` and GUI widgets import `DesignMethod`, `CalculationResult` and related types directly from `core.common.calculation_result`, despite `AGENTS.md` requiring GUI-to-service communication. Conversely, `core/asce7/wind/parapet.py` and `core/nds/fasteners/bolts.py` import the concrete `KnowledgeBaseService` from `app.services`. | GUI must depend only on application-facing models/services/controllers. Core must not import concrete application services. Introduce stable contracts and a reference-data protocol/port; keep `KnowledgeBaseService` as an adapter. |
| F-08 | Calculation Sheet displays raw LaTeX rather than rendered mathematics. **CONFIRMED** | `base_workspace.py` places `equation_latex` inside a `<code>` element and calls `QTextEdit.setHtml()`. `substitution_str` is a free-form string. | Add a renderer inside the existing Panel 3 and introduce ordered structured calculation steps, variables, quantities, acceptance criteria and references. Use a local/offline renderer. |
| F-09 | Calculation trace is too flat for cross-output reuse. **CONFIRMED** | `LimitStateResult` has a single equation string, substitution string and clause string. `intermediate_results` is `Dict[str, Any]`. | Add `CalcStep`, `Quantity`, `RefSpec`/`CodeReference` and an optional additive `CalculationResult.trace`. Keep existing fields during migration. |
| F-10 | Diagram inputs are loosely structured dictionaries. **CONFIRMED** | C&C and Wood workspaces merge `input_parameters` and `intermediate_results` and pass the dictionary to their diagram widgets. The base diagram is bolt-specific. | Introduce `DiagramSpec`/`VisualizationModel` and module-specific mappers. Diagram drawing code must not contain engineering equations. |
| F-11 | Diagram behavior is calculation-triggered rather than consistently input-reactive. **CONFIRMED in reviewed workspace flow** | Diagram updates are called from `display_results()` after calculations; no unified input-edit state/controller updates geometry and stale state. | Geometry must redraw immediately from current geometry input state. Derived forces must be calculated by the engine; old force results must be marked stale when inputs change. |
| F-12 | Calculation templates, engine dispatch and workspace module configs are duplicated. **CONFIRMED** | Module IDs exist in `AddCalculationDialog.TEMPLATES_DATA`, `CCCalculationWorkspace.MODULE_CONFIGS`, `WoodCalculationWorkspace.MODULE_CONFIGS`, `CalculationService._registry`, `list_supported_modules()` and MainWindow routing. `docs/review_audit_day14.md` records specific Wood template mismatches. | Introduce one `ModuleRegistry`/`ModuleCatalog` as the single source of truth for catalog, fields, engine dispatch, availability, code family and diagram builder. |
| F-13 | Input controls are not yet schema-driven. **CONFIRMED** | Current specialized workspaces create `QLineEdit` controls from local module configuration tuples; labels and parsing are duplicated. Units, KB-backed enum sources and conditional field behavior are not described by a common field schema. | Use `FieldSpec` definitions to drive labels, symbols, units, widgets, choices, validation, defaults and conditional visibility without changing the approved form layout. |
| F-14 | Code edition and reference labels may drift. **REPORTED — VERIFY WP-0** | ACP-001 reports `NDS 2018` in some MainWindow titles/banners while the active registry and calculation modules use NDS 2024. Current `active_code_registry.json` identifies NDS v2024. | Resolve displayed editions from the active code registry and the calculation item's project snapshot. Never hard-code a stale edition into the GUI. |
| F-15 | Workspace base class owns too many presentation responsibilities. **CONFIRMED** | `BaseCalculationWorkspace` builds the form, generic diagram, calculation sheet, summary, status/DCR and calculation event handling. | Preserve the composition and layout, but delegate input-state mapping, diagram projection, calculation-sheet rendering and summary projection to focused presenters/renderers. |

## 2.3 P2 — Consistency, maintainability and quality risks

| ID | Finding | Evidence / current behavior | Required resolution |
|---|---|---|---|
| F-16 | Sidebar group ordering and calculation ordering are not stored. **REPORTED — VERIFY DDL in WP-0** | ACP-001 reports no group table, order fields, draft input storage or schema version in the present SQLite schema. The visible footer says order can be dragged and is reflected in reports. | Add schema-v2 project groups, item ordering, draft persistence and migration/version control. |
| F-17 | Project-level defaults are not fully represented. **REPORTED — VERIFY WP-0** | ACP-001 reports no `project_settings` model for default design method and code-edition snapshot. The ASD/LRFD toggle currently affects the active workspace/page. | Add project defaults for new items, while storing the effective design method and code context independently on each calculation item/revision. |
| F-18 | Status bar may contain static status/project information. **REPORTED — VERIFY WP-0** | ACP-001 identifies hard-coded table/procedure counts and project name. | Obtain status from `KnowledgeBaseService` integrity audit and `ProjectService`; never show stale or fabricated counts. |
| F-19 | Hidden compatibility widgets remain in the UI class. **CONFIRMED** | Hidden ASD/LRFD radio buttons and hidden reference text are retained for old tests. | Replace UI-internal compatibility dependencies with tests against the approved public view behavior. Remove only after regression tests have been migrated. |
| F-20 | Navigation icons and text encoding need review. **REPORTED — VERIFY WP-0** | ACP-001 reports emoji glyphs and possible encoding corruption in a Drive copy. | Verify the current Git source and Windows packaging. Use locally bundled SVG assets only if necessary to preserve the approved icon appearance. |
| F-21 | Documentation has implementation drift. **REPORTED — VERIFY WP-0** | ACP-001 reports README CustomTkinter wording and outdated IDs in `context_guide.txt`. Actual source uses PySide6. | Correct user-facing developer documentation after baseline and scope are approved. Do not alter locked architecture sections without approval. |
| F-22 | Test suite status is not yet independently confirmed in the current review environment. **REPORTED / VERIFY WP-0** | State summary and ACP-001 refer to 69 tests; the Day 14 audit records missing pytest/PySide6 in its sandbox and only 8 Wood tests running in that environment. | Establish a pinned/provisioned test environment and rerun the full suite. Do not claim 69/69 passing until current test evidence exists. |

## 2.4 Findings already recorded in the Day 14 audit

These issues should be added to the project QA backlog, independently from the UI/architecture refactor:

1. **Excel database-tab CSV parsing:** the prior audit reports that `ExcelBuilder` can silently skip multi-header CSVs after `pandas.read_csv()` raises a parser error inside a broad exception handler. Fix the CSV parsing path so errors are visible and all required referenced source data is represented, without modifying the protected source CSVs.
2. **Simpson HUS210-2 hard-coded special case:** the prior audit reports a hard-coded capacity branch compensating for a catalog/nailing-schedule mismatch. Verify against the authoritative Simpson source and benchmark procedure. Do not edit the protected catalog CSV or reference manifest without the KB curator's verification and explicit authorization.
3. **Default empty-input FAIL states:** the prior audit reports that two C&C modules can produce red FAIL badges when opened with empty/fallback inputs. A new blank calculation must instead show `INCOMPLETE`; only an actual validated input set may produce PASS/FAIL.
4. **Test environment gaps:** provision the declared development dependencies and rerun tests rather than relying on syntax parsing as a substitute for GUI testing.

## 2.5 Important nuance: retain the good parts

Keep the existing `CalculationResult` concept, immutable revision approach, SQLite repository, SHA-256 Knowledge Base manifest, unit conversion foundations, ASD/LRFD distinction, C&C and Wood calculation functions, PDF/XLSX builders and four-panel layout. Refactor their contracts and integration; do not replace them wholesale.

---

# 3. Frozen UI specification

The interface requirements in ACP-001 and the previous UI review are consistent. The following are treated as locked.

## 3.1 Main window shell

| Area | Locked design / behavior |
|---|---|
| Header | Hamburger button, dynamic calculation title, segmented `ASD | LRFD` toggle at the right |
| Sidebar expanded | 232 px width; logo/subtitle; Dashboard, Projects, Reports and Settings navigation; current Project label/name; blue full-width `+ Add Calculation`; calculation items grouped under user-defined group headers; item name and DCR/status; footer hint about drag-to-reorder and report order |
| Sidebar collapsed | 48 px rail; hamburger; navigation icons; blue `+` add button; separator; numbered item chips and status underline; hover flyout with title/module/DCR/status |
| Sidebar animation | Approximately 120 ms, preserve existing toggle interaction |
| Add Calculation dialog | Three columns: category list, template list, detail/preview with Name, Group, Design method and Start from (Blank/Duplicate); Cancel and Add & Open |

Material categories (Loads, Wood, Steel, Concrete/CMU) are catalog categories and filters. They are not a forced project hierarchy. Users may freely create, group and order calculation items.

## 3.2 Four-panel calculation workspace

| Panel | Position | Locked responsibility |
|---|---|---|
| Panel 1 — INPUTS | Left; approximately 280–380 px | Schema-driven engineering input form; units and validation; Run Calculation and Save Revision below the form |
| Panel 2 — DIAGRAM | Top-right | Dynamic engineering schematic; true dimension symbols/subscripts and values; geometry, supports and load/force arrows; amber warning pill for detailing/applicability warning when applicable |
| Panel 3 — CALCULATION SHEET | Middle-right | Code-basis banner; ordered calculation rows showing equation → substitution → result and right-aligned code references; true mathematical notation with subscript/superscript. References are combined here, not in a separate panel |
| Panel 4 — SUMMARY | Bottom-right | Status pill, governing limit state/check, DCR gauge where applicable and seven-column table: Step, Limit state check, Governing clause, Demand, Capacity, DCR, Status |

The existing base workspace already describes this 4-panel layout. The proposal does not authorize any new panel or rearrangement.

## 3.3 What may change internally

Allowed after approval:

- Replace sample values with actual blank/validated inputs.
- Replace raw-HTML formula text with a real mathematical renderer inside Panel 3.
- Replace dictionary-based diagram parameters with a typed `DiagramSpec` while retaining the same drawing area and visual design.
- Replace static sidebar items with a persistent project tree while keeping the same visual layout.
- Replace duplicated module-specific form configurations with a registry-backed form while preserving the displayed form layout.

Not allowed:

- Changing the panel order, panel positions, overall visual design, sidebar geometry, button placement, header, labels or dialog's three-column composition.
- Adding a separate code/reference panel, a fifth panel or a different navigation model.
- Replacing the approved reference mockups/screenshots with a different visual concept.

---

# 4. Target architecture

## 4.1 Architectural style

Adopt lightweight Clean Architecture / Ports-and-Adapters, compatible with the current Python codebase. Avoid adding layers that do not have a clear responsibility. The goal is enforceable dependency direction and reusable application contracts, not a large framework migration.

## 4.2 Target dependency model

```text
┌──────────────────────────────────────────────────────────────┐
│ PRESENTATION / GUI — PySide6 (existing UI frozen)              │
│ MainWindow | Sidebar | Add Dialog | Workspace Host             │
│ Input Form | Diagram Canvas | Calc Sheet | Summary             │
└───────────────────────────────┬──────────────────────────────┘
                                │ app-facing DTOs and commands
┌───────────────────────────────▼──────────────────────────────┐
│ APPLICATION LAYER                                              │
│ Use Cases | WorkspaceController | ModuleRegistry               │
│ Project/Item Services | Calculation Workflow | Report Workflow  │
│ Input Validation | View-model/projection mapping                │
└───────────────┬───────────────────────────────┬───────────────┘
                │ domain request/result         │ ports
┌───────────────▼────────────────┐   ┌──────────▼────────────────┐
│ ENGINEERING DOMAIN / CORE      │   │ INFRASTRUCTURE ADAPTERS   │
│ ASCE 7 | NDS | AISC 360       │   │ KnowledgeBaseService     │
│ ACI 318 | TMS 402             │   │ SQLite repositories      │
│ Units | Combinations | Checks │   │ PDF/XLSX exporters       │
│ Calculation trace             │   │ Local cache / Cloud Sync │
│ Reference-data protocol/port  │   │ Settings / filesystem     │
└────────────────────────────────┘   └───────────────────────────┘
```

**Dependency rules:**

- GUI imports application-facing DTOs, controllers and services only; no `core/` implementation imports and no direct database/Google Drive calls.
- Application coordinates use cases and adapters; it does not contain structural engineering equations.
- Core contains deterministic engineering rules and calculations. It must not import PySide6, GUI modules or concrete `app.services` implementations.
- Core may depend on a narrow reference-data protocol/port that it owns (or receive normalized reference data explicitly). `KnowledgeBaseService` implements the port as an adapter.
- Infrastructure implements persistence, reference-data access, export and cloud synchronization. It does not make engineering acceptance decisions.
- Renderers and diagram canvases draw supplied structured data; they do not recalculate engineering demand/capacity.

## 4.3 Recommended package additions (incremental)

```text
app/
  models/                 # application DTOs and workspace view models
  registry/               # ModuleSpec, FieldSpec, catalog/registry
  controllers/             # WorkspaceController; pure Python, no Qt imports
  ports/                   # application-side persistence/export ports if needed
  services/                # existing services + focused use cases
  rendering/               # calculation-sheet projection / renderer orchestration

core/
  common/
  ports/                   # reference-data protocol or narrow domain-owned port
  ... existing and future engineering families ...

gui/
  main_window.py           # shell; keep current file initially
  dialogs/
  widgets/                 # keep current widgets through parity migration
  assets/                  # local SVG/KaTeX assets as required

storage/
  repositories/             # existing SQLite repository
  migrations/               # versioned database migrations, if preferred

exporters/                  # existing PDF/XLSX adapters; consume common result model
```

Do not perform a broad physical folder reorganization as part of the first refactor. Add only the focused packages needed, migrate incrementally and retire old modules after parity evidence exists.

---

# 5. Canonical data contracts

The following are required conceptual contracts. Exact names and module placement may be adjusted during WP-0, but there must be one authoritative representation for each concept.

## 5.1 Module Registry — one source of truth

Replace the independent lists in the dialog, workspaces, `CalculationService` and `MainWindow` with one `ModuleRegistry`.

Suggested `ModuleSpec`:

```python
@dataclass(frozen=True)
class ModuleSpec:
    module_id: str
    aliases: tuple[str, ...]
    category: str                  # loads, wood, steel, concrete_cmu
    title: str
    description: str
    code_family: str               # edition resolved from active/project code registry
    calculation_callable: object
    fields: tuple["FieldSpec", ...]
    diagram_id: str | None
    procedure_md: str | None
    maturity: str                  # verified, preview, coming_soon, unavailable
    supported_methods: tuple[str, ...]
```

Suggested `FieldSpec`:

```python
@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    symbol: str | None             # e.g. t_{m}, F_{yb}
    quantity_type: str | None
    unit: str | None
    value_type: str                # float, int, enum, bool, text
    section: str
    required: bool
    default_value: object | None
    default_reference: str | None
    enum_source: str | None        # KB reference ID or declared literal set
    validation: dict
    visible_if: str | None
    affects_geometry: bool
    affects_analysis: bool
```

Registry requirements:

- The Add Calculation dialog, input form, calculation dispatcher, title/code banner, workspace selection and diagram builder all query the same registry.
- Every `module_id` and alias is unique and resolves to one calculation implementation.
- Each module declares maturity. An unimplemented Steel/Concrete module may be visible as a coming-soon catalog item but cannot execute or display a false PASS.
- Each `procedure_md` and KB-backed enum table must exist in `reference_manifest.json` when it is declared as a manifest-backed asset.
- Code editions are resolved from `active_code_registry.json` plus the project's stored code-edition snapshot, not from hard-coded GUI strings.
- Preserve existing public IDs as aliases during migration where practical; do not break saved project references.

## 5.2 Calculation lifecycle and input policy

A project calculation item has:

- Stable `calculation_id` / item identity.
- `module_id`.
- User-defined title and optional group.
- Independent draft input values.
- Effective design method (ASD or LRFD).
- Effective code-edition/jurisdiction snapshot.
- Last calculation result metadata and stale flag.
- Immutable revision history.

Input policy:

1. Required engineering inputs start blank on a new item.
2. A missing mandatory input yields `INCOMPLETE`; invalid units/types/ranges yield `INVALID INPUT`.
3. A default is allowed only when it is explicitly approved by the governing code/workflow and carries its reference (`default_reference`).
4. Sample values are test/benchmark fixtures, not live user defaults.
5. A blank or invalid input set must never produce a numerical result that appears to be an actual verified design check.
6. Existing engine numeric defaults must be audited per field and migrated to explicit input policy; do not remove defaults blindly if a benchmark intentionally calls the function with a controlled fixture.

## 5.3 Calculation request, result and structured trace

Keep the existing `CalculationResult` concept and its current fields for compatibility. Extend it additively with an ordered `trace` field. Existing engines can migrate in stages; the UI/exporter must fall back to current `LimitStateResult` data until each module emits full trace data.

Suggested reference model:

```python
@dataclass(frozen=True)
class RefSpec:
    code: str
    edition: str
    kind: str                  # section, equation, table, figure, procedure, catalog
    locator: str               # e.g. 12.3.3, Eq. 12.3-1
    kb_reference_id: str | None
    source_path: str | None
    sha256: str | None
```

Suggested calculation step:

```python
@dataclass(frozen=True)
class CalcStep:
    step_id: str
    stage: int                  # Rule 5 load-path stage 1–4 where applicable
    title: str
    symbolic: str               # restricted LaTeX/math markup
    substituted: str            # same notation with evaluated inputs
    variables: dict             # typed quantities and values
    result_value: float | str | None
    result_unit: str | None
    acceptance: object | None   # typed limit/criterion; not DCR-only
    dcr: float | None
    status: str
    refs: tuple[RefSpec, ...]
    note: str = ""
```

A calculation step must support Equation → Substitution → Result → Limit/Acceptance → DCR (when applicable) → Status → Code reference. Non-DCR checks such as drift, spacing, edge distance and dimensional limits must be represented without inventing a DCR.

Reference requirements:

- Store code family, edition, locator and source provenance.
- Use `kb_reference_id` when the file exists in the KB manifest.
- A code clause citation that is not represented by a local KB file may still be recorded as a code reference, but it must not be falsely claimed to resolve to a manifest entry.
- All manifest-backed references must resolve to the correct manifest entry and snapshot SHA-256.
- Do not invent page numbers, equations, tables or references that are not supported by the source.

## 5.4 Math markup and rendering

Use a restricted, validated LaTeX subset for engineering formula display. At minimum consider `_`, `^`, `\\frac`, `\\sqrt`, `\\cdot`, `\\times`, `\\leq`, `\\geq`, `\\phi`, `\\Omega`, `\\Delta`, `\\theta`, `\\lambda`, `\\parallel`, `\\prime`, `\\text{}`, `\\left(` and `\\right)`.

- Validate/normalize math strings before sending them to the renderer.
- Do not treat an arbitrary free-form string as trusted HTML.
- The GUI renderer must not evaluate engineering formulas; it only formats already-computed trace data.
- Recommended renderer: locally bundled KaTeX hosted inside `QWebEngineView`, with no CDN/network dependency. `QWebChannel` is needed only if interactive page-to-Python actions (for example reference selection) are required; it is not mandatory for static formula rendering.
- Run a packaging spike before finalizing the renderer. ACP-001 estimates QtWebEngine may add 100 MB or more to the packaged build; treat that as an estimate to measure, not a verified package-size figure.
- Retain a graceful rich-text fallback for environments where QtWebEngine cannot be shipped; document that stacked fractions may be limited in fallback mode.

## 5.5 Visualization model

Introduce `DiagramSpec` / `VisualizationModel` independent of Qt types. It should describe:

- Geometry primitives and connectivity.
- Supports/restraints and connection locations.
- Dimension lines and math-formatted labels.
- Loads, force vectors, moments and distributed-load symbols (application point, direction, magnitude and unit).
- Annotations, warnings, governing case labels and view bounds.
- Result/input version and stale-state information.

The calculation engine and/or application projection layer creates the values. A module-specific mapper converts typed inputs/results to the shared diagram model. The current QPainter widgets draw the supplied model; they do not compute loads, moments, capacities or DCR.

Panel 2 synchronization:

- Geometry-affecting input changes redraw geometry immediately.
- Derived action arrows and numerical forces must come from a fresh deterministic calculation result.
- When inputs change after a run, mark derived results/force arrows stale and prevent the prior result from looking current.
- Recalculation may be debounced for a responsive live preview, but must not create a revision automatically.
- Warnings and amber pills must be driven by actual result warnings/limit flags, never hard-coded notes.
- Modules without a diagram builder must show a clear empty-state illustration/message within the existing panel; never show another module's diagram.

## 5.6 Summary model

Panel 4 should receive a `SummaryViewModel` projected from the same result version as Panel 3 and Panel 2. It should support:

- All existing statuses: `PASS`, `FAIL`, `REQUIRES REVIEW`, `INCOMPLETE`, `INVALID INPUT`.
- Governing limit state/check and clause.
- Demand/capacity/DCR when meaningful.
- Non-DCR acceptance checks.
- Warnings, stale flag and incomplete reasons.

Do not introduce `OUTDATED` as a new calculation status. Use a separate `is_stale` flag, as recommended by ACP-001, while keeping the SAD status list unchanged.

---

# 6. Project data model and SQLite schema v2

## 6.1 SQLite remains authoritative for local project data

SQLite remains the local source of truth for projects, calculation items, drafts and immutable revisions. The existing project/calculation/input/result/revision structure is retained and migrated additively.

The Knowledge Base (`database/`, `procedures/`, `config/reference_manifest.json`) remains separate from project data. The Google Drive synchronization phase must preserve raw KB files and offline cache. Do not assume project SQLite databases are automatically synchronized to Google Drive; that is a separate data-sync decision and must be explicitly scoped.

## 6.2 Required project calculation item behavior

- A project can contain many calculation items of any module category.
- Users can create a user-defined group, rename a group, reorder groups, collapse/expand groups and move an item between groups.
- Items can be ordered freely within a group and across the ungrouped area.
- Add from Blank creates a new empty calculation item.
- Add from Duplicate copies the selected source item's draft input values and relevant item settings but does not copy its immutable revision history.
- Rename, duplicate, move and delete operations act on one stable item identity.
- Delete is soft delete with confirmation; saved revisions remain retained for audit/history.
- Display labels such as C-01/C-02 may be generated from visible order; stable identity must not depend on display number or row position.
- Two items with the same `module_id` must not share input-widget state or calculation results.

## 6.3 Proposed schema-v2 additions

The exact DDL must be authored and migration-tested by the cloud-data/storage owner. ACP-001 proposes the following additive model:

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

Additional implementation rules:

- Use `PRAGMA user_version` and an explicit v1→v2 migration.
- Back up the existing database to `storage/backups/` before migration.
- Migration must be transactional, idempotent and safe to rerun.
- Existing `calculation_inputs`, `calculation_results` and `calculation_revisions` must remain intact; migration tests must verify all existing revisions and serialized payloads are preserved.
- `item_number` is a stable monotonic per-project audit identifier and is never reused after deletion.
- Visible label is computed from order; do not use list length to create the stable primary key.
- Add indexes and uniqueness constraints after verifying existing data compatibility.
- `last_dcr` is only a cache/display value; the authoritative result remains in the saved calculation result/revision.
- Soft deletion must not delete immutable revisions.

## 6.4 Draft, Run, Revision and stale-state lifecycle

```text
Add (Blank / Duplicate)
        ↓
Draft created and autosaved
        ↓
Edit inputs / design method / code context
        ↓
Validate and update workspace state
        ↓
Run Calculation (in-memory; no revision)
        ↓
Display Panels 2, 3 and 4 from the same result version
        ↓
Save Revision (explicit immutable snapshot)
        ↓
Further edits mark result stale until next run
```

- `Run` does not create a revision.
- `Save Revision` persists inputs, result, trace, code context, module/software version and reference hash snapshot.
- Duplicate copies draft data, not the source item's revision history.
- Editing inputs, design method, relevant project defaults or reference manifest marks the last result stale.
- A stale result remains available for comparison/history but must not appear as the current valid output.
- Stale detection should be based on a deterministic hash of normalized inputs + design method + effective code/jurisdiction context + applicable project defaults + module/calculation version + reference-manifest snapshot. Define the canonical serialization before hashing.
- The ASD/LRFD toggle changes the selected item's method; a project default is only the starting method for new items. No method mixing is permitted.

---

# 7. Application workflows and service responsibilities

## 7.1 WorkspaceController

Introduce a pure-Python `WorkspaceController` in `app/controllers/`. It must not import PySide6. It coordinates a selected calculation item and returns a `WorkspaceViewModel`.

Suggested operations:

```python
load(item_id) -> WorkspaceViewModel
edit_field(item_id, key, raw_value) -> WorkspaceViewModel
set_design_method(item_id, method) -> WorkspaceViewModel
run(item_id) -> WorkspaceViewModel
save_revision(item_id, change_notes) -> WorkspaceViewModel
load_revision(item_id, revision_number) -> WorkspaceViewModel
```

The view model includes:

- Item identity/title/group/order and module metadata.
- Schema-driven input field values, units, validation and conditional visibility.
- Current design method and code edition.
- DiagramSpec.
- Ordered calculation sheet rows.
- Summary projection.
- `is_dirty`, `is_stale`, `is_running`, `warnings` and incomplete reasons.

## 7.2 ProjectService / item APIs

Extend existing project services with item/group operations; do not duplicate the SQLite logic in GUI:

```text
list_items(project_id)
list_groups(project_id)
add_item(project_id, module_id, title, group_id, start_from)
duplicate_item(item_id)
move_item(item_id, group_id, new_index)
rename_item(item_id, title)
delete_item(item_id)                 # soft delete
create_group(project_id, name)
rename_group(group_id, name)
move_group(group_id, new_index)
set_group_collapsed(group_id, collapsed)
get_project_defaults(project_id)
set_project_defaults(project_id, defaults)
```

The GUI refreshes from service-returned state after each mutation. It must not maintain a competing local source of truth for item order or persistence.

## 7.3 Explicit use cases

At minimum, separate these actions:

- Create calculation item.
- Load calculation item / draft.
- Edit and autosave draft.
- Run calculation.
- Save immutable revision.
- Load prior revision.
- Duplicate item.
- Reorder/move item and group.
- Prepare/export ordered report package.

This separation makes the Run/Save Revision semantics unambiguous and testable without Qt.

---

# 8. UI integration plan — no visual redesign

## 8.1 MainWindow and Sidebar

`MainWindow` becomes a shell that composes the existing header, navigation, sidebar and workspace host. It must stop owning a hard-coded `self.calculations` list as the authoritative project model.

Use a project-tree model (for example `QStandardItemModel` or a custom Qt model) backed by `ProjectService` results:

- Expanded view: user groups and ordered calculation items.
- Collapsed rail: the same items as numbered status chips.
- Drag/drop: internal move calls `ProjectService.move_item()` and refreshes from service response.
- Context actions: Rename, Duplicate, Move to group, Delete.
- Sidebar group collapse state is persisted.
- Add dialog loads template categories and metadata from ModuleRegistry.
- Header title is derived from the selected item.
- Project name and status come from the active project service, not hard-coded demo content.

The drag-and-drop operation must be atomic in SQLite and protected against stale indexes/concurrent updates.

## 8.2 Single Workspace Host and schema-driven forms

The target is one `WorkspaceHost` and one `WorkspaceView` composition for all module types. The active calculation item determines:

- Which `ModuleSpec` is loaded.
- Which `FieldSpec` inputs are shown.
- Which diagram builder is selected.
- Which calculation result/trace/summary are projected.

The existing `cc_workspace.py` and `wood_workspace.py` should not be deleted at the beginning. Keep them as migration references and compatibility implementations until:

1. Schema-driven UI can reproduce the approved visible layout.
2. C&C and Wood module forms have parity.
3. All existing vertical slice and GUI tests pass against the replacement.
4. Screenshot regression confirms the visual freeze.

Only then may old specialized workspace classes be retired.

## 8.3 Panel behavior

- Panel 1 form widgets are created from `FieldSpec`; symbols and units are rendered from schema values. KB-backed choices query the KB service through the application layer.
- Panel 2 uses the common DiagramSpec and an existing-compatible QPainter canvas.
- Panel 3 uses the structured trace and local KaTeX renderer. A click on a KB-backed reference may open a compact reference preview without creating another panel.
- Panel 4 uses SummaryViewModel and retains its seven columns and status list.
- A newly added blank item shows no sample values and status `INCOMPLETE` until required inputs are entered and a valid calculation is run.

## 8.4 Status bar and dynamic metadata

Project name, item count, KB table/procedure counts, SHA-256 verification and sync state must come from their services. Avoid literal counts or sample project labels in production display.

---

# 9. Reporting and exporter integration

## 9.1 One source of truth

PDF, XLSX and the GUI must consume the same `CalculationResult.trace` and reference snapshot. Exporters must never independently recalculate an engineering equation.

## 9.2 Ordered multi-item report

`ReportService` must accept a project and an ordered list of calculation item IDs. Default order is the project's group/item tree order. Users may select a subset in the Reports page, but order remains explicit and reproducible.

The report package should include:

- Project and calculation item identifiers/titles.
- Display order and group information.
- Effective code editions and design methods.
- Input assumptions and units.
- Ordered calculation trace and code references.
- Limit-state/summary outcomes.
- Relevant diagram output where available.
- Revision number, calculation/software version and reference source snapshot.

## 9.3 XLSX and PDF requirements

- XLSX continues to follow `rules.md` and its locked workbook layout (17 columns A–Q, Arial 10 pt, baseline-aligned text, `Source_Audit` and required reference tabs).
- PDF follows SAD's 12-section report organization, retaining the mandatory 7-section engineering calculation procedure structure.
- Equations, symbols, units and references must correspond to the same trace values used in the GUI.
- Export formatting is presentation only; no additional engineering calculations in the exporter.
- Fix multi-header CSV reading with a resilient reader and explicit error reporting; do not silently skip a required source table.
- Track HUS210-2 as a separate reference-data verification task; do not hard-code unverified capacities or alter protected CSVs without authorization.

---

# 10. Engineering implementation roadmap: Day 15 through Day 20 and cross-cutting ACP work packages

This is the recommended implementation order from the current repository state to V1.0. The WP numbers refer to ACP-001; the Day 15–20 milestones refer to `state_summary.txt` and SAD roadmap. They are consolidated into one dependency-aware sequence.

## Phase 0 — WP-0: Governance, full baseline audit and approval gate

**Owner:** Primary Agent / Tech Lead; QA Verifier assists.  
**Status:** NEXT. Read-only.  
**Must complete before implementation.**

Tasks:

1. Re-read `AGENTS.md`, `rules.md`, `proposed.md`, `state_summary.txt` and the consolidated proposal.
2. Verify all findings F-01 through F-22 against current source. Specifically inspect `add_calculation_dialog.py`, `cc_workspace.py`, `project_service.py`, `report_service.py`, `knowledge_base_service.py`, all exporters, all engine modules and tests.
3. Map all imports/dependency directions and detect any `core -> app.services`, `gui -> core`, `gui -> storage/cloud` edges.
4. Audit all module IDs/aliases across templates, engine dispatch, workspace configs, test fixtures, procedure mapping and code registry.
5. Map the full user event flow: Add Calculation → select item → edit → preview diagram → Run → Save Revision → reload → export.
6. Audit the existing SQLite schema and create a v1 DB fixture from the actual deployed schema.
7. Capture baseline screenshots for header, expanded/collapsed sidebar, Add Calculation dialog and each existing calculation workspace. Use approved existing screenshots as visual references.
8. Run baseline tests in a correctly provisioned environment. Record exact commands, environment versions and test counts. Do not accept an incomplete test run as a passing baseline.
9. Record numerical baseline outputs for all current C&C and Wood modules in ASD and LRFD.
10. Produce a final file-level plan: KEEP / REFACTOR / ADD / DEFER and exact owners/dependencies.
11. Reconcile documentation drift such as README framework wording and context guide IDs only after verifying the current source of truth.

Deliverables:

- Read-only architecture/dependency map.
- Current database schema and v1 migration fixture.
- Module ID/catalog audit.
- UI and persistence event-flow audit.
- Test and numerical baseline report.
- Approved implementation backlog, owners and dependency order.

**Gate 0:** No repository file is modified. Primary Agent presents the audit and receives written approval before moving to implementation. Any SAD changes beyond Section 2.1 require explicit user approval under the current `rules.md` change-control policy.

## Phase 1 — WP-0b: P0 live-data safety hotfix

**Owner:** desktop-app.  
**Dependency:** Phase 0 approval.  
**Priority:** Critical.

Tasks:

1. Remove hard-coded sample input values from production new-item paths.
2. Remove the sample calculation sheet and sample summary table from any newly created real calculation item.
3. Remove fixed engineering fallbacks such as `c_delta=0.69` from live diagram output.
4. Remove hard-coded/default warning notes that imply an actual design check.
5. Ensure a new blank item displays `INCOMPLETE`, empty calculation rows and no numerical demand/capacity/DCR.
6. Ensure invalid input shows `INVALID INPUT` with field-level reason; missing required input shows `INCOMPLETE`.
7. Keep sample data in tests/benchmarks or a clearly separated sample/demo fixture only.
8. Add a regression test that constructs a fresh item and proves no numerical engineering values are displayed before a valid run.

Acceptance:

- No real/new item can show sample numerical values or a fabricated PASS/FAIL.
- Existing benchmark fixtures still run with their explicit, controlled inputs.
- UI screenshot still matches the approved layout.

## Phase 2 — WP-1a + WP-2 + WP-3: Foundational architecture work (parallelizable)

These packages can proceed in parallel after Phase 0, with one integration owner coordinating shared interfaces.

### Phase 2A — WP-1a: SQLite schema v2

**Owner:** cloud-data / storage engineer.

Tasks:

1. Add versioned migration using `PRAGMA user_version`.
2. Create `calculation_groups` and `project_settings`.
3. Add group/order/item number/draft/stale/delete metadata to calculations.
4. Add indexes/constraints only after checking the real v1 schema and legacy rows.
5. Back up the live DB before applying migration.
6. Migrate transactionally and idempotently.
7. Preserve existing revisions, input JSON and result JSON exactly.
8. Add migration tests for old DBs with existing records, rollback, re-run/idempotence, foreign keys and soft-delete behavior.

**Acceptance:** An existing v1 database upgrades to v2 without loss or alteration of historical revisions; a second migration run is a no-op; backup exists.

### Phase 2B — WP-2: Structured calculation trace

**Owner:** calculation-engine.

Tasks:

1. Define `Quantity`, `RefSpec`/`CodeReference`, `CalcStep` and optional `CalculationResult.trace`.
2. Include stage 1–4 where Rule 5 load-path sequencing applies.
3. Support more than one reference per calculation step.
4. Support non-DCR acceptance results and optional DCR.
5. Implement a restricted math markup validator/parser.
6. Keep current `equation_latex`, `substitution_str`, `LimitStateResult` and `intermediate_results` during compatibility migration.
7. Add serialization/deserialization tests for SQLite and exporters.
8. Do not change any numerical calculation result in this phase.

**Acceptance:** Existing tests still pass; trace models are deterministic, serializable and reject unsupported markup; no ungrounded references are emitted.

### Phase 2C — WP-3: Module Registry and schema definitions

**Owner:** desktop-app, coordinated with calculation-engine.

Tasks:

1. Define `ModuleSpec` and `FieldSpec`.
2. Register all existing C&C and Wood modules with their canonical IDs and aliases.
3. Move template labels, categories, field definitions, enum sources, code family, maturity and diagram IDs into registry metadata.
4. Make `CalculationService` dispatch through the registry.
5. Remove the separate manually maintained `list_supported_modules()` source or derive it from the registry.
6. Make Add Calculation dialog catalog data query the registry while keeping the existing three-column dialog UI.
7. Mark Steel and Concrete templates `COMING_SOON`/unavailable until implementation and QA complete.
8. Add uniqueness/consistency tests for IDs, aliases, procedures and enum table references.

**Acceptance:** One catalog defines templates, engine mapping and diagram association; all current IDs still resolve; unavailable modules cannot run.

## Phase 3 — WP-1b + WP-4: Project item services and WorkspaceController

**Owners:** desktop-app + cloud-data/storage.  
**Dependencies:** Phase 2A and Phase 2C (WP-2 contract can be developed in parallel).

### Phase 3A — ProjectService item/group APIs

Tasks:

1. Implement list/create/duplicate/rename/move/delete calculation-item methods.
2. Implement group CRUD, ordering and collapse-state persistence.
3. Implement project defaults for initial design method and effective code registry snapshot.
4. Implement draft input autosave and stable item numbering.
5. Ensure duplicate copies draft values/settings only, not prior revision history.
6. Implement soft delete and report/list filters.
7. Implement atomic reorder/move transactions.
8. Ensure the same module can have multiple independent calculation items.

### Phase 3B — WorkspaceController

Tasks:

1. Create a pure-Python controller with no PySide imports.
2. Implement load, edit field, set method, validate, run, save revision and load revision.
3. Build `WorkspaceViewModel` containing item metadata, input state, diagram model, calculation steps, summary, dirty/stale flags and warnings.
4. Implement stale hashing using canonical normalized serialization of inputs, method, code context, defaults, module version and KB manifest hash.
5. Keep Run non-persistent and Save Revision explicitly persistent.
6. Unit test controller behavior without instantiating Qt.

Acceptance:

- Add, duplicate, edit, reorder, move and soft-delete operations persist through restart.
- Different same-type items have independent inputs/results.
- Run does not create a revision; Save Revision creates exactly one immutable revision.
- Prior revision can be loaded and reproduced.

## Phase 4 — WP-5 + WP-6: Sidebar tree, Add dialog integration and schema-driven workspace

**Owner:** desktop-app.  
**Dependencies:** Phase 3 and Module Registry.

### Phase 4A — Sidebar and main window integration

Tasks:

1. Replace `MainWindow.self.calculations` as source of truth with project-service-backed state.
2. Create the project tree model for groups and calculation items.
3. Preserve the exact expanded/collapsed sidebar design, item chips, hover flyouts and dimensions.
4. Wire drag/drop to persistent `move_item()` operations.
5. Add context actions: Rename, Duplicate, Move to group, Delete.
6. Wire Add Calculation to `ModuleRegistry` + `ProjectService.add_item()` and select the newly created item.
7. Resolve page/workspace routing by module metadata, not string matching or hard-coded `page_index`.
8. Derive title, project name, item status and status bar from service data.

### Phase 4B — WorkspaceHost and schema-driven InputForm

Tasks:

1. Build one `WorkspaceHost` / shared `WorkspaceView` composition for all module types.
2. Create Panel 1 controls from `FieldSpec`, including units, symbol formatting, enum sources and conditional fields.
3. Bind input changes to `WorkspaceController` and autosave drafts.
4. Keep the existing form card, scroll behavior, action row, panel splitters and style.
5. Migrate C&C and Wood forms to schema definitions.
6. Keep existing specialized classes until visual and functional parity is proven.
7. Retire `cc_workspace.py`/`wood_workspace.py` only after all C&C/Wood modules pass parity and screenshot regression.

Acceptance:

- Add → open → edit → close → reopen retains draft values.
- Two items with the same module type show independent inputs/results.
- Sidebar drag-and-drop is persistent and report order is the same as visible order.
- Screenshots match the approved UI within agreed pixel/layout tolerance.

## Phase 5 — WP-7 + WP-8 + WP-9: Math renderer, diagram model and current-engine trace migration

**Owners:** desktop-app + calculation-engine.  
**Dependencies:** Phase 2B, Phase 2C and Phase 3B.

### Phase 5A — WP-7: Calculation Sheet renderer

Tasks:

1. Prototype local KaTeX rendering in the existing Panel 3 using QtWebEngine.
2. Measure installed package size, startup time, memory and PyInstaller compatibility.
3. Decide whether QWebChannel is needed for clickable reference interactions; do not add it for static rendering without a need.
4. Vendor required assets locally; prohibit CDN/runtime network access.
5. Render ordered step cards/rows with symbolic equation, substitutions, units, result, criterion, DCR/status and code references.
6. Preserve the current code-basis banner and panel layout.
7. Add golden tests for fractions, subscripts, superscripts, Greek symbols, roots, inequalities, long equations and reference labels.
8. Add a graceful fallback for environments without the web renderer and document its limitations.

### Phase 5B — WP-8: DiagramSpec and diagram builders

Tasks:

1. Define the Qt-independent `DiagramSpec`/`VisualizationModel`.
2. Build/test the Wood bolt diagram builder first.
3. Migrate remaining implemented Wood diagrams and all C&C diagrams.
4. Render the model using the existing diagram panel/canvas.
5. Implement immediate geometry redraw on input changes.
6. Recompute derived force vectors only via the deterministic engine; use debounced preview where appropriate.
7. Drive warning pills from real warning/limit-state data.
8. Add an empty state for modules without a verified diagram.
9. Reuse DiagramSpec in PDF when appropriate.

### Phase 5C — WP-9: Emit structured trace from C&C and Wood engines

Tasks:

1. Update Day 13/14 calculation modules to emit structured trace steps as part of their results.
2. Populate actual equations, substitutions, units, code references and source IDs where available.
3. Capture reference-file hash snapshots at revision time.
4. Keep numerical values identical to current verified baselines.
5. Add trace completeness and provenance tests for every module.

Acceptance:

- Panel 3 renders true math and references per step.
- Panel 2 updates with current geometry and valid derived results.
- Panel 2/3/4 correspond to the same run/version.
- All existing C&C/Wood benchmarks remain numerically equivalent.

## Phase 6 — WP-11 + Day 15 and Day 16: Complete Steel and Concrete/CMU engines

**Owner:** calculation-engine; desktop-app supports registry and view integration; QA verifies.  
**Dependencies:** WP-2 structured trace, WP-3 Module Registry, test harness and reference-data verification.

### Day 15 — Steel Connections (AISC)

Implement the approved V1 Steel calculation scope in `core/aisc360/` using native deterministic functions and the same contracts:

- Bolted connection checks.
- Welded connection checks.
- Shear tab/single-plate connection including applicable supporting HSS wall checks.
- Single/double angle connection checks.
- Column base plate and anchor rod checks within the approved module scope.
- HSS-to-HSS connection checks.

For each module:

1. Confirm the associated existing procedure and reference data.
2. Define input schema and required/default values.
3. Implement validation, intermediate calculations, limit states and ASD/LRFD paths.
4. Emit structured trace and CodeReference records.
5. Register module and diagram builder.
6. Create unit, reference-data, benchmark, ASD/LRFD regression and end-to-end tests.
7. Do not expose as verified until all required checks and references pass.

### Day 16 — Concrete and CMU Anchorage (ACI/TMS)

Implement the approved V1 Concrete/CMU scope in `core/aci318/` and `core/tms402/`:

- Cast-in/post-installed concrete anchors within the existing approved procedure scope.
- Concrete tension/shear interaction and applicable Chapter 17 limit states.
- CMU anchorage and out-of-plane breakout within the existing TMS procedure scope.
- Embedded/cantilever steel post workflow where defined by the protected procedure.

For each module follow the same 7-step process as Steel: verify source data, schema, engine, trace, registry, diagram, tests and QA. If any required reference or assumption is missing, the module remains incomplete rather than inventing a value.

Acceptance:

- All approved Day 15/16 modules have complete calculation engines, field schemas, registry entries, calculation traces, diagram status, reports and passing benchmark suites.
- Steel and Concrete/CMU appear as available only after verification.
- No unverified placeholder page or sample numeric output is presented as a real check.

## Phase 7 — WP-10 + Day 18: Full project reports and exporter completion

**Owner:** desktop-app/exporters; calculation-engine supplies trace; QA verifies.

Tasks:

1. Update ReportService to accept project ID and ordered item IDs.
2. Build multi-item PDF/XLSX packages in project tree order or explicit user-selected order.
3. Consume the same `CalculationResult.trace`, `DiagramSpec`, SummaryViewModel and reference snapshots as the GUI.
4. Preserve the locked XLSX format (17 columns, Arial 10 pt, required tabs/source audit) and PDF 12-section structure.
5. Verify superscripts/subscripts in both output formats using supported renderer/export methods.
6. Ensure one calculation item export and a multi-item project package both work.
7. Test incomplete/stale/invalid modules: reports must disclose status and must not imply a verified PASS.
8. Fix resilient CSV parsing; required source rows must not be silently skipped.
9. Resolve HUS210-2 catalog/workflow mismatch only after authoritative source verification and required approval for protected reference changes.
10. Run PDF/XLSX regression for C&C, Wood, Steel and Concrete/CMU modules.

Acceptance:

- A 3-item project exports in the same order as the sidebar.
- The PDF/XLSX results match the UI trace.
- Source_Audit includes all relevant reference provenance.
- Exporters do not recalculate engineering results.

## Phase 8 — Day 17: Google Drive raw-file synchronization and offline cache

**Owner:** cloud-data; QA verifies.

Implement the existing SAD Google Drive sync scope after local Knowledge Base and project workflows are stable.

Tasks:

1. Implement OAuth 2.0 through the agreed Google Drive API workflow.
2. Keep raw `.csv`, `.md`, `.py`, `.json` and `.txt` files as raw files; do not convert them into Google Docs/Sheets.
3. Use local cache and SHA-256 checks for each synchronized reference file.
4. Detect missing files, modified files, manifest mismatches and concurrent conflicts.
5. Preserve previous files/versions on conflict; do not overwrite silently.
6. Secure credentials using the approved OS credential store (e.g. keyring) and never write tokens into source/config files.
7. Support offline startup, local calculations, local reports and an explicit sync status.
8. Test disconnected, reconnect, interrupted sync, conflict and corrupted/missing-file cases.
9. Ensure cloud availability never blocks local deterministic calculations.
10. Do not synchronize the SQLite project database to Drive unless project-data cloud sync is explicitly included and separately designed/approved.

Acceptance:

- The app can run and calculate offline from a verified local KB cache.
- Sync verifies integrity, reports conflicts and preserves recoverability.
- No runtime AI service is required.

## Phase 9 — Day 19: Full QA, regression, Windows packaging and clean-machine verification

**Owner:** qa-verifier coordinates; all implementation owners fix assigned issues.

### Required test levels

| Level | Required coverage | Evidence |
|---|---|---|
| L1 — Unit | Units, validation, load combinations, formulas, trace models, math parser, registry, diagram builders, controller and services | pytest report and coverage summary |
| L2 — Reference Data | Manifest integrity, SHA-256, KB lookups, enums and table parsing | 92/92 expected reference files verified in the release cache, with 0 unexplained missing/mismatch |
| L3 — Benchmark | Each module compared with approved worked examples/reference calculations | Recorded expected vs actual values and tolerances |
| L4 — Regression | ASD/LRFD separation, historical C&C/Wood benchmarks, trace, migration and export regression | Full regression results and numerical comparison |
| L5 — End-to-End | Add → input → validate → diagram → run → save revision → reopen → duplicate/reorder → export | E2E evidence per module family and project workflow |
| GUI — Visual | Main window, expanded/collapsed sidebar, Add dialog, each panel and module state | Before/after screenshots with no unauthorized visual change |
| Offline — Runtime | Start, open project, use local KB, calculate and export without internet | Clean offline test evidence |
| Packaging | Build and install standalone Windows app | Installer/build log and clean-machine launch evidence |

### Test environment requirements

1. Provision `requirements.txt` dependencies in a clean, reproducible environment.
2. Pin a tested set of compatible package versions for release; current lower-bound-only declarations are not a sufficient release lock.
3. Ensure pytest and PySide6 (plus the selected Qt test plugin if used) are actually installed.
4. Run the complete test suite using its intended runner; do not use `unittest discover` as a substitute for pytest tests.
5. Run GUI tests offscreen and separately run smoke tests with a real Windows display/session.
6. Record exact Python, PySide6, Qt, OS and dependency versions.
7. Run all engine modules for ASD and LRFD where supported; record unsupported applicability statuses explicitly.

### Windows packaging

1. Build using PyInstaller per SAD.
2. Include local KaTeX assets and all required CSV/MD/JSON resources.
3. Verify paths work from the frozen executable, not only from the source checkout.
4. Verify credential storage and Google OAuth callback handling in the packaged environment.
5. Install on a clean Windows machine or clean VM with no development Python environment.
6. Verify first launch, project creation, calculation, report export, offline operation and shutdown.

Acceptance:

- No unexplained test failures.
- No numerical differences from approved benchmark baselines unless separately reviewed and authorized as engineering corrections.
- UI screenshot regression passes.
- Standalone build starts and works in a clean Windows environment.

## Phase 10 — Day 20: Final UAT, documentation and V1.0 release sign-off

**Owner:** Primary Agent / Tech Lead; QA and user acceptance required.

Tasks:

1. Execute UAT using representative C&C, Wood, Steel and Concrete/CMU calculation items.
2. Verify same-module multiple-item behavior and project organization.
3. Verify Add Blank, Add Duplicate, draft autosave, Run, Save Revision, revision restore and report order.
4. Verify ASD/LRFD switching and per-item method persistence.
5. Verify code-edition and reference snapshots in historical revisions.
6. Verify no stale or incomplete result is presented as current PASS.
7. Verify offline and cloud sync behavior.
8. Verify report content against UI calculation trace.
9. Update README, developer setup, user guide, troubleshooting, release notes and known limitations.
10. Update `state_summary.txt` and permitted SAD status section under the assigned primary-agent/change-control process.
11. Tag/build V1.0 only after user sign-off and QA report approval.

Acceptance:

- All V1 modules are marked with correct maturity/availability.
- All project workflow and engineering QA criteria pass.
- User approves the final UI and engineering workflow.
- V1.0 build, test evidence and documentation are archived.

---

# 11. Integrated work-package dependency matrix

| WP / Phase | Main owner | Depends on | Can run in parallel with | Main gate |
|---|---|---|---|---|
| WP-0 / Phase 0 audit | Primary Agent + QA | None | None | Written approval to implement |
| WP-0b sample-data hotfix | desktop-app | WP-0 approval | Schema/contract design after approval | Fresh item has no fabricated numbers |
| WP-1a schema v2 | cloud-data/storage | WP-0 | WP-2, WP-3 | Migration preserves v1 records |
| WP-2 trace + math grammar | calculation-engine | WP-0 | WP-1a, WP-3 | Backward-compatible structured trace |
| WP-3 Module Registry | desktop-app | WP-0 | WP-1a, WP-2 | Catalog, dispatch and template consistency |
| WP-1b item/group APIs | desktop-app + storage | WP-1a, WP-3 | WP-2 | Persistent project items |
| WP-4 WorkspaceController | desktop-app | WP-1b, WP-2, WP-3 | Some engine implementation after contracts | Controller unit tests without Qt |
| WP-5 sidebar/tree/dialog | desktop-app | WP-1b, WP-3, WP-4 | WP-7/8 design | Frozen UI plus persistence |
| WP-6 schema-driven workspace | desktop-app | WP-4, WP-5 | WP-7/8 backend work | C&C/Wood visual and functional parity |
| WP-7 equation rendering | desktop-app | WP-2 | WP-8, WP-9 | KaTeX offline/package spike and golden tests |
| WP-8 DiagramSpec/builders | desktop-app | WP-3, WP-4 | WP-7, WP-9 | Qt-independent diagram tests |
| WP-9 C&C/Wood trace migration | calculation-engine | WP-2 | WP-7/8 | Numerical parity and trace completeness |
| WP-11 Day 15/16 engines | calculation-engine | WP-2, WP-3 and verified references | WP-5/6/7/8 where contracts are stable | Module-specific benchmark and regression pass |
| WP-10 reports | desktop-app/exporters | WP-7, WP-8, WP-9, WP-11 | Day 17 cloud sync preparation | Ordered multi-item exports match GUI |
| Day 17 cloud sync | cloud-data | Stable KB cache/manifest and local workflows | Day 18 exporter finalization | Verified offline/cloud sync |
| Day 19 full QA/package | QA + all owners | All implementation phases | Fixes may be parallelized | All required tests and clean Windows build pass |
| Day 20 UAT/release | Primary Agent + user + QA | Day 19 | Documentation cleanup | V1.0 sign-off |

Recommended order mirrors the dependency graph: WP-0 → WP-0b → (WP-1a + WP-2 + WP-3) → (WP-1b + WP-4) → (WP-5 + WP-6) → (WP-7 + WP-8 + WP-9) → WP-11 / Steel + Concrete engines → WP-10 → Day 17 Cloud Sync → Day 19 QA/package → Day 20 UAT/release. Some engine work can proceed in parallel once its trace and registry contracts are stable; do not develop new module-specific UI workspaces.

---

# 12. File-level disposition

## 12.1 KEEP — preserve responsibility and verified behavior

- `database/` — protected CSV source tables.
- `procedures/` — protected engineering procedures.
- `config/reference_manifest.json` — protected integrity manifest; updates only through the authorized KB-curator verification process.
- `core/asce7/` and `core/nds/` — preserve verified calculation functionality and numerical outputs.
- `core/common/units.py`, load combinations, validation and exception foundations.
- `storage/repositories/project_repository.py` and SQLite persistence approach; extend through migrations.
- `app/services/` existing services; refine interfaces and workflow responsibilities.
- `exporters/` existing PDF/XLSX adapters; update them to consume the common trace.
- Existing four-panel layout and design tokens/styles in GUI source.
- Existing C&C/Wood diagram implementations as migration references until replacement parity is proven.

## 12.2 REFACTOR — internal changes after approval

- `core/common/calculation_result.py`: add structured trace/reference support; preserve compatibility.
- `core/asce7/**`, `core/nds/**`: remove concrete application-service dependency, add trace output and typed reference usage without changing benchmark values.
- `app/services/calculation_service.py`: dispatch through Module Registry; separate run from revision save.
- `app/services/knowledge_base_service.py`: implement reference-data port; improve resilient CSV reading and reference snapshots.
- `app/services/project_service.py`, `history_service.py`: project item/group APIs, drafts, revisions and project defaults.
- `storage/repositories/project_repository.py`: additive schema-v2 migration and project ordering/group/draft state.
- `gui/main_window.py`: service-backed project tree, no hard-coded calculation source list or substring routing.
- `gui/widgets/base_workspace.py`: retain layout, replace demo output and delegate presentation mappings/rendering.
- `gui/widgets/cc_workspace.py`, `wood_workspace.py`: use common controller/view-model/diagram contracts; retire only after parity.
- `gui/dialogs/add_calculation_dialog.py`: read catalog from Module Registry while retaining the existing three-column UI.
- `exporters/excel_builder.py`, `pdf_builder.py`: consume trace and ordered project item data; robustly load required KB tables.
- `README.md`, `context_guide.txt`: correct verified implementation drift, with current identifiers and PySide6 setup.

## 12.3 ADD — focused packages / modules

- `app/registry/` — ModuleSpec, FieldSpec and ModuleRegistry.
- `app/models/` — DTOs and WorkspaceViewModel.
- `app/controllers/` — pure Python WorkspaceController and use-case orchestration.
- `app/rendering/` — math/rendering projection and calculation-sheet data mapping.
- `core/ports/` — reference-data protocol/port if used by calculation modules.
- `storage/migrations/` — schema version migration scripts, if adopted.
- `gui/assets/` — locally bundled SVG icons and KaTeX runtime assets.
- Shared `DiagramSpec`/builder modules and tests.

## 12.4 DEFER / conditional removal

- Retire `cc_workspace.py` and `wood_workspace.py` only after schema-driven workspace parity and test migration.
- Do not implement project-cloud sync unless the user explicitly includes it in V1 scope; the current SAD cloud phase is raw KB sync.
- Do not reorganize the protected Knowledge Base folder structure.
- Do not add Steel/Concrete placeholder calculations that return fabricated results.

---

# 13. Governance, approvals and protected assets

## 13.1 Current governance rules remain active

- `AGENTS.md` pre-work protocol remains mandatory: read `rules.md`, `proposed.md` and `state_summary.txt` before work.
- `rules.md` remains locked unless the user explicitly instructs the Primary Agent to update it.
- `proposed.md` remains authoritative. Existing `rules.md` permits only the established Section 2.1 status synchronization without explicit user approval; the broader SAD amendments in ACP-001 must therefore be separately approved before editing.
- `state_summary.txt` is owned by the Primary Agent/Tech Lead.
- `database/` and `procedures/` are protected and must not be modified, deleted or reorganized without explicit approval and the five-step KB verification.
- `config/reference_manifest.json` may be updated only through the authorized KB-curator verification process.
- Every work package reports exact added/modified files, test commands/results, benchmark evidence and deviations.
- Agents stay within their assigned roles; avoid concurrent edits to the same file.
- Any missing engineering information is escalated; no agent invents engineering data, code clauses, capacities or assumptions.

## 13.2 SAD sections potentially affected by ACP-001

After user approval only, the Primary Agent may prepare controlled SAD amendments covering:

- Section 6.4 — additive structured calculation trace.
- Sections 8.1–8.3 — project tree/item behavior and the locked four-panel workspace responsibilities.
- Sections 9.2–9.4 — SQLite project item/group/draft schema v2 and revision lifecycle.
- Section 15 — incremental addition of registry/controller/rendering packages.
- Section 18 — new ADRs for project-scoped ordered calculation items, structured trace, unified module registry and offline math rendering.

This proposal does not itself amend the SAD, `rules.md` or any protected file.

---

# 14. Decisions required from the user before implementation

| Decision | Consolidated recommendation | Why it matters |
|---|---|---|
| D-1 — Math renderer | Use vendored KaTeX within QtWebEngine, with a packaging spike and a rich-text fallback. Add QWebChannel only if reference-click interactions require it. | Meets real math notation while remaining offline; package size and startup impact must be measured. |
| D-2 — Input defaults | Blank required engineering inputs; code-authorized defaults only with a reference; sample values only in tests/demo fixtures. | Prevents fabricated numerical design outputs. |
| D-3 — Stale state | Separate `is_stale` flag; do not add `OUTDATED` to the SAD status list. | Preserves the existing five statuses and clearly distinguishes an old result from a failed check. |
| D-4 — SAD amendments | Do not edit `proposed.md` beyond current permitted status synchronization until the user explicitly approves the identified sections. | Respects repository change-control rules. |
| D-5 — Day 15/16 sequencing | Build Steel and Concrete/CMU engines after WP-2 and WP-3 contracts/registry are stable; do not build new module-specific workspaces. | Avoids duplicating the current architecture problem. |
| D-6 — Workspace migration | Move toward one schema-driven WorkspaceHost, but retain current C&C/Wood workspace classes until parity tests and screenshot regression pass. | Limits risk to the approved UI and working vertical slices. |
| D-7 — Project/cloud data boundary | SQLite is authoritative for local project items and revisions; initial Google Drive sync remains the raw KB sync described in SAD. Project DB cloud sync is out of scope unless separately approved. | Avoids ambiguous conflict semantics and accidental synchronization of project records. |
| D-8 — Implementation authorization | Approve Phase 0 read-only audit first; approve implementation only after its exact file-level plan and risks are presented. | Keeps the proposal draft and prevents premature changes to protected/locked files. |

---

# 15. Risks and mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Schema migration damages or loses historical data | High | Backup, transaction, version number, v1 fixture and byte-for-byte revision preservation tests |
| UI redesign occurs unintentionally during refactor | Critical | UI Freeze checklist, baseline screenshots, pixel/layout regression and explicit prohibition in agent brief |
| Legacy tests depend on internal widgets/types | Medium | Compatibility layer and migrate tests before retiring old classes |
| Structured trace changes numeric engine behavior | Critical | Additive model first, benchmark parity, no formula edits bundled with presentation refactor |
| Math renderer increases package size or startup time | Medium | Early QtWebEngine/KaTeX packaging spike; fallback path; measure actual bundle/runtime cost |
| Live diagram displays stale force values | High | Separate geometry projection from calculated force projection; stale flag and version correlation |
| Module catalogs drift again | High | Registry uniqueness and manifest consistency tests; no secondary hand-maintained list |
| Module is shown as available before it is verified | High | Maturity/availability state in ModuleSpec gates execution and catalog affordances |
| Code edition/reference snapshot drifts over time | High | Active registry resolution plus per-project/per-revision code/reference snapshot |
| Google Drive unavailable or conflicting | Medium | Offline local cache, hash checks, preserve both versions and explicit conflict resolution |
| Current test count is assumed rather than proven | High | Provision correct environment and record full fresh test report before declaring baseline/release pass |
| Protected reference data requires correction | High | KB-curator workflow, authoritative source verification and explicit approval before data/manifest mutation |

---

# 16. Final acceptance checklist — V1.0 release gate

The Primary Agent may recommend V1.0 only when every applicable line is evidenced as PASS.

## Project and item management

- [ ] Project selection and active project state persist.
- [ ] Calculation items persist across restart.
- [ ] Multiple items of the same module type keep independent inputs/results.
- [ ] Blank and Duplicate flows work as specified.
- [ ] Group creation, rename, collapse, ordering and move work.
- [ ] Item drag/drop order persists and controls report order.
- [ ] Rename, soft delete and restore/history behavior are verified.
- [ ] Stable item IDs/item numbers never collide or get reused.

## Calculation and engineering trace

- [ ] All approved C&C, Wood, Steel and Concrete/CMU modules are implemented and correctly registered.
- [ ] Every required input is typed and validated; missing inputs cannot become fake default results.
- [ ] ASD/LRFD are strictly separated and stored per item/revision.
- [ ] Every result has reproducible input/code/reference/software context.
- [ ] Every supported calculation check emits structured trace with applicable criterion and references.
- [ ] C&C/Wood existing benchmark numbers remain equivalent unless separately approved as engineering corrections.
- [ ] No GUI/diagram/exporter contains engineering equations.

## UI and visualization

- [ ] Header, sidebar, rail, Add dialog and four-panel UI match frozen design.
- [ ] Panel 1 is schema-driven and shows units/validation without changing visual layout.
- [ ] Panel 2 uses DiagramSpec; geometry redraws from inputs; forces are engine-derived and stale-safe.
- [ ] Panel 3 displays actual mathematical notation and code references together.
- [ ] Panel 4 shows correct status/governing check/DCR and seven-column table.
- [ ] UI cannot show sample numerical values for a fresh real item.
- [ ] Screenshot regression passes for expanded/collapsed sidebar and representative modules.

## Storage, references and exports

- [ ] SQLite schema-v2 migration preserves v1 revision data.
- [ ] Drafts autosave and saved revisions are immutable.
- [ ] Reference and code-edition snapshots are retained per revision.
- [ ] All manifest-backed references resolve; expected KB cache integrity passes.
- [ ] PDF/XLSX use the same trace/result data as the GUI.
- [ ] Multi-item exports follow visible project order.
- [ ] Exporter does not silently omit required CSV tables.
- [ ] Source audit and report revision metadata are correct.

## Cloud, offline, QA and release

- [ ] Raw KB Drive sync and conflict handling work.
- [ ] Offline calculation, project access and report export work from local data.
- [ ] Full unit/reference/benchmark/regression/integration/E2E/GUI tests pass.
- [ ] Windows package builds and launches on a clean environment.
- [ ] No runtime AI/LLM dependency exists.
- [ ] Documentation and dependency lock match the shipped application.
- [ ] QA report, benchmark evidence, package artifact and UAT sign-off are archived.
- [ ] User approves V1.0 release.

---

# 17. Copy-ready instruction to the coding agent

> You are the implementation agent for `mndo2710/structural-engineering-kb`.
>
> Read `AGENTS.md`, `rules.md`, `proposed.md` and `state_summary.txt` before any task. Treat this Consolidated Architecture Review, Change Proposal & V1.0 Completion Roadmap as the proposed implementation baseline, subject to explicit user approval.
>
> **The approved PySide6 UI is frozen.** Preserve the header, sidebar expanded/collapsed behavior, navigation, Add Calculation dialog's three-column layout and the four-panel workspace exactly. Panel 1 remains Inputs on the left; Panel 2 remains the top-right dynamic Diagram; Panel 3 remains the middle-right Calculation Sheet with equations and code references integrated; Panel 4 remains the bottom-right Summary. Do not add another panel, rearrange panels, change visual styling or replace the UI framework.
>
> Do not rewrite the project from scratch. Preserve the current C&C and Wood calculation behavior and benchmark results. Keep the existing Knowledge Base files protected. Keep `rules.md`, `proposed.md` and `state_summary.txt` under the ownership/change-control rules in `AGENTS.md` and `rules.md`.
>
> **First execute Phase 0 only, read-only.** Verify the findings against the entire current repository; map imports, module IDs, calculation/item lifecycle, SQLite schema, UI event flow, exporters and tests; establish the actual fresh test and numerical baseline; capture the approved UI screenshots; and return the file-level KEEP/REFACTOR/ADD/DEFER plan. Do not edit, delete, move, rename, commit or push any repository file in Phase 0.
>
> After the user explicitly authorizes implementation, follow the dependency order in Sections 10 and 11. Implement schema v2, structured calculation trace, Module Registry, WorkspaceController, project item persistence, schema-driven workspace, offline math renderer, DiagramSpec, C&C/Wood trace migration, Steel and Concrete/CMU engines, ordered reports, Google Drive raw KB sync, full QA and Windows packaging.
>
> Never put engineering equations in GUI, diagram or exporter code. Never allow `core/` to import GUI or a concrete application service. Never allow the GUI to import `core/` implementation modules. Never use sample engineering values as live defaults for a real item. Missing required information must result in `INCOMPLETE` or `INVALID INPUT`. Do not make an unimplemented/unverified module look available.
>
> `Run Calculation` must not create a saved revision. `Save Revision` must create an immutable revision. Drafts may autosave. Editing inputs, design method or code/reference context marks the prior result stale. Keep the existing five calculation statuses; use a separate stale flag.
>
> For every work package, report exact files added/modified, owner, test commands and results, benchmark comparisons, UI screenshot-regression outcome, migration evidence, and any deviation. Stop and escalate when an engineering assumption, reference, protected Knowledge Base file, locked governance file or SAD amendment requires approval.
>
> Do not claim 100% completion until the entire V1.0 checklist in Section 16 is evidenced as PASS and the user signs off.

---

# 18. Source basis and review limitations

This consolidated proposal is based on:

1. `CLAUDE_ACP-001_architecture_change_proposal.md` (uploaded for this review): project-scoped calculation items, structured calculation trace, schema-driven workspaces, SQLite schema v2, service APIs, Module Registry, DiagramSpec, work packages WP-0 through WP-12, acceptance criteria and decisions D-1 through D-5.
2. `Structural_Calculation_App_Architecture_Review_Proposal.md` (previous review): source-level dependency findings, CalculationResult and visualization contract recommendations, input/default risks, project workflow/persistence wiring, exporter and migration recommendations, phased target architecture and frozen UI constraints.
3. Repository source on `main` as inspected on 17 November 2026: `AGENTS.md`, `README.md`, `rules.md`, `proposed.md`, `state_summary.txt`, `docs/review_audit_day14.md`, `gui/`, `app/services/`, `core/`, `storage/`, `exporters/`, `config/` and `tests/`.

Limitations:

- This is a static read-only architecture review and consolidated proposal.
- The application was not launched during this consolidation.
- The full automated test suite was not rerun during this consolidation.
- Findings explicitly marked REPORTED — VERIFY WP-0 must be confirmed against the complete current source before code changes.
- Package-size, QtWebEngine and PyInstaller impacts are proposed for measurement; they are not presented as tested results.
- This document does not authorize changes to the GitHub repository or any protected file.

**Final recommendation:** Approve the consolidated architecture direction, commission Phase 0 as a read-only verification task, then authorize implementation by work package with the UI freeze and engineering QA gates enforced throughout.
