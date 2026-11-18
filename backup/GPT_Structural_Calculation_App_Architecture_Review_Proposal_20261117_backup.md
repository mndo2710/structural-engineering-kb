# STRUCTURAL CALCULATION APP
## Architecture Review & Target Architecture Proposal

**Repository:** `mndo2710/structural-engineering-kb`  
**Branch reviewed:** `main`  
**Review snapshot:** 17 November 2026  
**Tree SHA:** `3daeb80bb841a8620a5b0eafd77201de04c9671c`  
**Review mode:** Read-only source and documentation review  
**Implementation status:** No repository files modified

---

## 1. Executive assessment

The current project has a sound foundation and should **not** be rewritten from scratch. The existing technology choices and main separation of responsibilities are appropriate for a deterministic Windows structural calculation application:

- Python + PySide6 desktop application.
- `core/` for deterministic engineering calculations.
- `app/services/` for application workflow orchestration.
- `database/` and `procedures/` for the engineering knowledge base.
- SQLite through `storage/repositories/` for project data and calculation revisions.
- `exporters/` for Excel and PDF deliverables.
- `tests/` for unit, benchmark, regression and end-to-end verification.

The main weakness is not the overall choice of architecture. It is that the **layer boundaries and data contracts are only partially enforced**. In several places, GUI, application services, calculation modules and reference-data access know too much about each other's internal structures.

### Main recommendation

Evolve the current layered architecture into a **lightweight Clean Architecture / Ports-and-Adapters structure**, incrementally. Keep the current PySide6 UI and the four-panel workspace exactly as approved. Introduce stable contracts for inputs, calculation steps, code references, visualization and summary data. Then make each panel a consumer of those contracts.

The target is a maintainable engineering application where:

1. Calculation logic is independent of the GUI and concrete storage implementation.
2. The same calculation result is the source of truth for the diagram, calculation sheet, summary and exported reports.
3. Equations and code references are structured data, not strings assembled by the GUI.
4. Calculation modules, UI templates and supported-module routing come from one registry.
5. Project history stores enough reference and software-version information to reproduce an earlier calculation.

---

## 2. UI requirements that are frozen

The approved calculation workspace is a **four-panel interface**. This is also confirmed by `gui/widgets/base_workspace.py` and `state_summary.txt`.

| Panel | Fixed responsibility | Required behavior |
|---|---|---|
| **Panel 1 – INPUTS** | Engineering inputs | Geometry, material properties, loads, boundary conditions, design method and units. Inputs must be typed and validated. |
| **Panel 2 – DIAGRAM** | Engineering visualization | Dynamic schematic showing geometry, dimensions, supports, loads, force directions and relevant calculated effects. |
| **Panel 3 – CALCULATION SHEET** | Equations and code traceability | Symbolic equation, mathematical rendering, substitution, result, limit/acceptance criterion and governing code reference together in the same calculation step. |
| **Panel 4 – SUMMARY** | Design outcome | Governing limit state, demand, capacity, DCR where applicable, status and limit-state table. |

### Non-negotiable UI constraints

- Do not change the four-panel arrangement, relative panel positions, navigation, dimensions, proportions, spacing, colors, typography, visual hierarchy or established interaction pattern.
- Panel 2 remains the top-right diagram panel.
- Panel 3 remains the calculation sheet panel. Governing code and references are combined with the applicable equation/check; do not create a separate fifth reference panel.
- Panel 4 remains the summary panel.
- Improve the internal data flow and rendering implementation behind the existing panels. Do not redesign the interface to accommodate the architecture.
- Do not modify the approved reference screenshots or replace them with a new visual design.

**Important distinction:** “Dynamic diagram” means that displayed geometry and actions must stay synchronized with the current input/calculation state. It does not authorize the diagram widget to implement its own engineering equations.

---

## 3. What exists today

The current repository is a functioning application skeleton with two completed vertical slices, not merely a knowledge-base repository.

### Current high-level structure

```text
main.py
app/
  services/
    calculation_service.py
    history_service.py
    knowledge_base_service.py
    project_service.py
    report_service.py
core/
  common/
  asce7/
  nds/
database/
procedures/
gui/
  main_window.py
  dialogs/add_calculation_dialog.py
  widgets/base_workspace.py
  widgets/cc_workspace.py
  widgets/wood_workspace.py
storage/
  repositories/project_repository.py
exporters/
tests/
config/
```

### Existing strengths to preserve

| Area | Existing implementation | Recommendation |
|---|---|---|
| Desktop foundation | PySide6 `MainWindow` and four-panel workspace | KEEP |
| Calculation result | Shared `CalculationResult` and `LimitStateResult` dataclasses | KEEP concept; REFACTOR contract incrementally |
| Calculation dispatch | `CalculationService` registry | KEEP; consolidate registry metadata |
| Knowledge-base integrity | Manifest, caching, SHA-256 verification | KEEP; add reference snapshots to calculation revisions |
| Project history | SQLite tables for projects, calculations, inputs, results and revisions | KEEP; finish wiring from GUI and enrich revision metadata |
| Engineering engines | ASCE 7 and NDS modules | KEEP; preserve verified behavior and benchmark results |
| Diagrams | Separate C&C and Wood custom-painted widgets | KEEP; change their data input to a typed visualization model |
| Exporters | Separate Excel and PDF builders | KEEP; make them consume the same structured calculation result |
| Engineering data | CSV database and Markdown procedures | PROTECT; do not reorganize or rewrite without explicit approval |

---

## 4. Findings and architecture risks

### 4.1 Dependency direction is violated in both directions — HIGH

The working rules require `gui/` to communicate through `app/services/` and prohibit direct GUI dependencies on `core/`. However:

- `gui/main_window.py` imports `DesignMethod` from `core.common.calculation_result`.
- `gui/widgets/base_workspace.py` imports `CalculationResult`, `CalculationStatus` and `DesignMethod` directly from `core/`.
- Specialized workspaces also import calculation result/domain types directly from `core/`.
- Conversely, calculation modules such as `core/asce7/wind/parapet.py` and `core/nds/fasteners/bolts.py` import the concrete `KnowledgeBaseService` from `app/services/`.

This creates a dependency in both directions: GUI knows the internal core model, while core knows an application-layer service implementation.

**Impact:** Changes to a domain result type or reference-data service can propagate into unrelated layers. It also makes isolated testing and alternative adapters harder.

**Recommendation:**

- Introduce neutral domain/application contracts that are not owned by the GUI or by a concrete service.
- Define a small reference-data port/protocol owned by the calculation/domain side, or pass normalized reference data into the engine. `KnowledgeBaseService` becomes an adapter implementing that contract.
- Expose an application-facing calculation request/response contract to the GUI.
- Migrate imports gradually and provide compatibility re-exports while old imports are being retired. Do not perform a large rename/rewrite in one step.

### 4.2 Panel 3 does not yet render LaTeX as mathematics — HIGH

`BaseCalculationWorkspace.display_results()` takes `LimitStateResult.equation_latex` and inserts it into a `<code>` element inside HTML sent to `QTextEdit.setHtml()`.

That displays the LaTeX source as text; it does not provide a full mathematical layout engine for fractions, aligned equations, Greek notation, nested subscripts/superscripts or equation formatting. The current `substitution_str` is also a free-form string.

**Impact:** The current data model and renderer cannot reliably deliver the approved calculation-sheet experience. The GUI is forced to format formulas itself and does not have structured variable/value/unit data.

**Recommendation:**

- Add an `EquationRenderer` behind the existing Panel 3 container.
- Use an offline-capable, locally packaged mathematical renderer (for example, bundled KaTeX/MathJax assets hosted locally inside the desktop app). Do not depend on an internet CDN at runtime.
- Feed it structured calculation-step data. LaTeX should be a rendering representation, not the only stored form of the calculation.
- Render each check as a coherent block: equation → substitution → numerical result → limit/criterion → DCR/status → code reference.
- Keep the existing panel card, title, code-basis banner, spacing and overall layout unchanged.

### 4.3 Panel 2 uses loosely structured dictionaries — HIGH

Both specialized workspaces currently construct diagram parameters by merging:

```python
diag_params = dict(result.input_parameters)
diag_params.update(result.intermediate_results)
```

The dictionary is then passed to the relevant diagram widget. This means each diagram implementation must know the internal names and meanings of calculation input/intermediate-result keys.

**Impact:** Renaming an intermediate variable or adding a module can silently break the diagram. The diagram has no stable contract describing geometry, dimensions, supports, load vectors and annotations.

**Recommendation:**

Add a `VisualizationModel` and a module-specific mapper:

```text
CalculationResult + InputModel
            |
            v
VisualizationMapper(module_id)
            |
            v
VisualizationModel
            |
            v
Existing Diagram Widget / Renderer
```

The model should contain typed collections for geometry, dimensions, supports, loads/force vectors, labels, annotations, units and view bounds. The diagram widget should only draw the supplied model; it must not calculate engineering demands/capacities.

### 4.4 Diagram updates are calculation-triggered, not truly input-reactive — HIGH

The current C&C and Wood workspaces connect the Run Calculation signal and update their diagram from `display_results()`. The editable input fields are not generally connected through `textChanged` to a unified input-state/visualization update flow.

**Impact:** A changed input can remain visually unreflected until Run Calculation is pressed. The current behavior is not sufficient for the intended live diagram interaction.

**Recommendation:**

- Maintain a typed `InputModel` as the single source of truth for the current form state.
- When a geometry/dimension field changes, update the diagram geometry immediately through the visualization mapper.
- Recalculate derived loads/forces through the same deterministic Calculation Engine, preferably with a short debounce to avoid recalculating on every keystroke.
- When inputs are invalid or a result is stale, show the appropriate state; do not leave an old force diagram looking current.
- Keep engineering calculations out of the widget and mapper. All numerical engineering values must originate from the calculation engine.

### 4.5 Calculation result is only partially structured — HIGH

`LimitStateResult` currently stores one LaTeX string, one substitution string, one clause string and numeric demand/capacity/DCR fields. `CalculationResult.intermediate_results` is a general `Dict[str, Any]`.

This is a reasonable first vertical-slice model, but it is too flat for a professional calculation sheet and future modules.

**Missing or weakly represented information:**

- Structured variables and their values/units.
- Distinction between symbolic equation, substitution operands and displayed result.
- Multiple references associated with one check (code section, equation, table, figure, reference-file identity and page when known).
- Typed result categories for checks that are not naturally DCR checks, such as drift, spacing, minimum edge distance or geometric applicability limits.
- A clear relationship between calculation steps and limit states.
- Reference-file SHA-256/version snapshot for historical reproducibility.

**Recommendation:** Introduce typed `CalculationStep`, `Quantity`, `CodeReference` and `ReferenceSnapshot` models. Keep `LimitStateResult` compatibility during migration. Do not force every engineering check into a demand/capacity ratio if its acceptance criterion is different.

### 4.6 Calculation module registry and UI templates are duplicated — HIGH

The project currently maintains module IDs separately in:

- `CalculationService._registry` and `list_supported_modules()`.
- `CCCalculationWorkspace.MODULE_CONFIGS`.
- `WoodCalculationWorkspace.MODULE_CONFIGS`.
- `AddCalculationDialog.TEMPLATES_DATA`.
- `MainWindow` page-index routing.

The existing `docs/review_audit_day14.md` already records mismatches between these lists. In addition, `MainWindow._on_add_calculation_clicked()` currently routes only by whether the template ID contains the string `wood`; other templates fall through to the C&C page. It appends a sidebar item but does not complete a unified module-selection/persistence workflow.

**Impact:** A selectable template may not have a matching engine/workspace, or may be routed to the wrong workspace.

**Recommendation:** Create one `ModuleDefinition` catalog. It should define:

- `module_id`, category and display metadata.
- Code family and edition.
- Supported design methods.
- Input schema and defaults/sample status.
- Engine registration key/function.
- Workspace/diagram renderer key.
- Availability state: `AVAILABLE`, `COMING_SOON`, `UNVERIFIED` or `DISABLED`.

The dialog, dispatcher, navigation and workspace selection should query the same catalog. Only a module that has an implemented and verified engine/workspace should be enabled for calculation.

### 4.7 Project revision persistence is not fully wired to the visible workspace flow — HIGH

`CalculationService.run_calculation()` supports optional revision persistence through `auto_save_revision=True` and a `calculation_id`. However, the current C&C/Wood workspace execution calls do not pass a calculation ID or enable that option.

The base workspace emits `saveRevisionRequested`, but the reviewed specialized workspace flow connects the calculate signal; a corresponding save-revision receiver is not evident in the current wiring. `MainWindow` also maintains a static in-memory calculation list and its Add Calculation path does not call `ProjectService.create_calculation()`.

**Impact:** The presence of SQLite history services does not by itself mean that interactive GUI calculations are consistently persisted as revisions.

**Recommendation:** Define explicit use cases:

- `CreateCalculationUseCase` – create a calculation container in the active project.
- `RunCalculationUseCase` – execute and return a result; optionally persist only when the workflow explicitly asks for it.
- `SaveCalculationRevisionUseCase` – create a new immutable revision with input/result/reference snapshots.
- `LoadCalculationRevisionUseCase` – load an earlier revision.

Do not silently overwrite prior revisions. A normal recalculation and a saved revision should be separate actions unless the approved UX explicitly says otherwise.

### 4.8 Default inputs can mask missing engineering inputs — HIGH

Several calculation functions use plausible numeric fallback values through `inputs.get(key, default)`. This is useful for sample/benchmark calculations, but dangerous if the same behavior is used for a real user calculation. A missing field can be silently replaced with a default and produce a numerical result instead of `INCOMPLETE` or `INVALID INPUT`.

**Recommendation:** Separate:

1. Engineering-required inputs.
2. Explicitly documented defaults permitted by the code/workflow.
3. Sample values used only for demonstration/benchmarking.

Each field definition must specify whether it is required, its unit, validation rules and whether a default is code-authorized. Missing required user input must not silently become a passing calculation.

### 4.9 Project roadmap components are not yet implemented — EXPECTED / TRACK

The current tree contains C&C and Wood calculation packages, but does not yet contain the target `core/aisc360/`, `core/aci318/`, `core/tms402/` and `cloud/` packages shown in the SAD roadmap. The Day 15–20 work is still listed as pending/ready in `state_summary.txt`.

The Add Calculation dialog already lists Steel and Concrete/CMU templates. These must be clearly treated as planned/unavailable until their engine modules, workspaces and verification tests are complete.

This is not a reason to create placeholder calculations. Keep the future module structure in the architecture plan, but do not represent incomplete modules as verified functionality.

### 4.10 Documentation and quality-gate drift — MEDIUM

- `README.md` describes the GUI as CustomTkinter in its directory tree, while the approved technology decision and actual source use PySide6.
- `docs/review_audit_day14.md` records test-environment issues: the reviewed VM lacked pytest and PySide6, preventing the full GUI/test suite from being exercised there. It reports the Wood unittest suite passing, but the UI check fell back to syntax parsing when PySide6 was unavailable.
- The review audit also records an Excel exporter issue where certain multi-header CSVs can be silently skipped, and a hardcoded HUS210-2 catalog special case.

These items should remain tracked. They are not reasons to change the approved UI or rewrite the application architecture.

---

## 5. Recommended target architecture

Use a small Clean Architecture / Ports-and-Adapters structure that fits the existing Python project. Do not introduce a heavy framework or reorganize the whole repository simply to match a textbook diagram.

### Target dependency direction

```text
┌────────────────────────────────────────────────────────────┐
│                  PRESENTATION / GUI                         │
│  MainWindow | Existing 4-Panel Workspace | Dialogs           │
│  Input View | Diagram Renderer | Equation Renderer | Summary │
└──────────────────────────────┬─────────────────────────────┘
                               │ app-facing request/response
┌──────────────────────────────▼─────────────────────────────┐
│                APPLICATION / USE CASES                      │
│  RunCalculation | CreateCalculation | SaveRevision          │
│  ModuleCatalog | InputValidation | VisualizationProjection  │
│  ReportPreparation | Project/History Workflows              │
└──────────────────────────────┬─────────────────────────────┘
                               │ domain ports/contracts
┌──────────────────────────────▼─────────────────────────────┐
│                  ENGINEERING DOMAIN / CORE                  │
│  ASCE 7 | NDS | AISC 360 | ACI 318 | TMS 402                │
│  Units | Load Combinations | Validation | Limit States      │
│  Deterministic calculation functions; no GUI/service imports│
└──────────────────────────────┬─────────────────────────────┘
                               │ ports implemented by adapters
┌──────────────────────────────▼─────────────────────────────┐
│                 INFRASTRUCTURE / ADAPTERS                   │
│  Knowledge Base CSV/MD | SHA-256 Manifest | SQLite           │
│  Excel/PDF Exporters | Local File Cache | Cloud Sync (future)│
└────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

| Layer | Owns | Must not own |
|---|---|---|
| GUI / Presentation | Rendering, user interaction, field widgets, panel updates | Engineering equations, CSV queries, SQLite SQL, cloud APIs |
| Application | Use-case orchestration, module selection, state transitions, revision workflow | Engineering formulas or direct drawing logic |
| Engineering Domain / Core | Engineering calculations, units, load combinations, limit-state logic | Qt widgets, UI formatting, concrete file/DB APIs |
| Ports / Contracts | Stable request/result/reference/persistence/visualization interfaces | Implementation-specific behavior |
| Infrastructure Adapters | CSV/MD parsing, SQLite, Excel/PDF generation, future Drive sync | UI layout or engineering acceptance logic |

**Dependency rule:** Dependencies point inward. `core/` must not import `app/services/`, GUI or concrete infrastructure. GUI must not import `core/` directly. Application services may depend on core contracts/use cases and call infrastructure through ports/adapters.

---

## 6. New contracts to introduce

The following models are the minimum useful set. They do not prescribe every implementation detail, but establish the stable data flow needed by the four panels.

### 6.1 InputParameterDefinition / InputModel

Each module should define inputs centrally:

- Key and display label.
- Data type and engineering quantity type.
- Unit and permitted unit display.
- Required/optional status.
- Authorized default (if any) and sample-only default (if any).
- Validation constraints and enumerated options.
- Group/section for the existing input form.
- Whether a change affects geometry, analysis, or both.

The workspace should render its existing form from this schema without changing its overall design.

### 6.2 CalculationRequest

A typed request should identify:

- `module_id`.
- `calculation_id` when attached to a saved project calculation.
- `design_method` (ASD or LRFD).
- `code_edition` / jurisdiction context.
- Validated input values and units.
- Calculation options and run context.

### 6.3 CalculationStep / Quantity / CodeReference

Each calculation step should carry enough data to render and verify a complete engineering check. A suggested conceptual shape:

```python
CalculationStep(
    step_id="S1",
    title="Parapet Cantilever Base Moment",
    equation_id="parapet_base_moment",
    equation_latex=r"M_{base}=\\frac{1}{2}w h_{par}^2",
    variables={
        "w": Quantity(value=..., unit="plf"),
        "h_par": Quantity(value=..., unit="ft"),
    },
    result=Quantity(value=..., unit="lb-ft"),
    acceptance=...,                 # optional, typed criterion
    dcr=...,                        # optional where applicable
    status="PASS",
    references=[CodeReference(...)],
)
```

This is illustrative, not a requirement to use these exact Python class names.

A `CodeReference` should support code family, edition, section, equation/table/figure, page if known, reference-file path/ID and SHA-256 snapshot. A calculation check may have more than one reference.

### 6.4 CalculationResult

Keep the common result concept, but enrich it to include:

- Original input snapshot and units.
- Assumptions and warnings.
- Ordered calculation steps.
- Typed intermediate quantities where useful.
- Limit-state/check results.
- Governing check and overall status.
- Reference snapshots including hashes.
- Calculation engine/software version.
- Timestamp and module version.

Do not make `intermediate_results: Dict[str, Any]` the only representation of all calculation logic. It can remain as a diagnostic/compatibility field during migration.

### 6.5 VisualizationModel

A stable visualization model should describe:

- Geometry primitives and connectivity.
- Dimension lines and labels.
- Supports, restraints and connection locations.
- Loads and forces as vectors with application points, magnitudes and units.
- Moment arrows/couples and distributed load symbols where relevant.
- Annotations, governing-case labels and view bounds.
- Input/result version or stale-state information.

Specialized mappers can translate C&C, Wood, Steel and Concrete result models into this common scene model. Specialized drawing remains allowed; duplicated engineering calculations inside drawing widgets are not.

### 6.6 SummaryViewModel

Panel 4 should receive an explicit summary model rather than independently interpreting core data. It should support DCR checks and non-DCR acceptance checks, multiple governing statuses, warnings, and incomplete/invalid input states.

---

## 7. Recommended runtime data flow

```text
User edits Panel 1
        |
        v
InputModel updated and validated
        |
        +------------------------------+
        |                              |
        v                              v
Geometry-only projection         Calculation request
        |                              |
        v                              v
Panel 2 immediate redraw          Application Use Case
                                       |
                                       v
                                Calculation Engine
                                       |
                                       v
                                CalculationResult
                                       |
                  +--------------------+-------------------+
                  |                    |                   |
                  v                    v                   v
          VisualizationMapper   CalculationSheetMapper  SummaryMapper
                  |                    |                   |
                  v                    v                   v
             Panel 2               Panel 3              Panel 4
```

### Synchronization rules

- Panel 1 is the source of current input values.
- Panel 2 geometry can update immediately from geometry inputs.
- Derived force/load values must come from a valid calculation result, not a second formula implementation in the GUI.
- If inputs change after a calculation, the prior calculation result must be marked stale until recalculated. Do not display old force values as if they apply to the new inputs.
- Panel 3 and Panel 4 must represent the same calculation-result version.
- Saving a revision is an explicit application use case. Merely refreshing a diagram or preview must not silently create a database revision.

---

## 8. Proposed file-level disposition

### KEEP

- `database/` and `procedures/` as protected engineering knowledge-base assets.
- `core/asce7/` and `core/nds/` calculation modules, subject to isolated refactoring and benchmark proof.
- `core/common/units.py`, load combinations, exceptions and validation foundations.
- `storage/repositories/project_repository.py` and the SQLite persistence approach.
- `exporters/` as separate output adapters.
- Existing four-panel composition and visual styling in `gui/widgets/base_workspace.py`.
- Existing specialized C&C/Wood diagram renderers as the initial drawing implementations.

### REFACTOR INCREMENTALLY

- `core/common/calculation_result.py`: evolve into a richer domain result/step/reference contract. Preserve compatibility while migrating.
- `core/*` calculation signatures: depend on a reference-data port/protocol or receive normalized data; remove concrete imports from `app/services/`.
- `app/services/calculation_service.py`: dispatch from the canonical module catalog; provide application-facing result mapping and explicit run/persist use cases.
- `app/services/knowledge_base_service.py`: remain the KB adapter; add resilient multi-header CSV parsing and reference snapshot access without changing protected CSV files.
- `gui/widgets/base_workspace.py`: preserve layout; delegate result transformation to panel-specific presentation mappers; add the real equation renderer behind Panel 3.
- `gui/widgets/cc_workspace.py` and `wood_workspace.py`: consume typed input/result/visualization models rather than merging arbitrary dictionaries.
- `gui/dialogs/add_calculation_dialog.py`: obtain module/template metadata from the canonical module catalog; keep its existing three-column visual design.
- `gui/main_window.py`: preserve navigation/layout; replace brittle template substring/page-index logic with catalog-driven workspace routing and connect project/calculation lifecycle use cases.
- `storage/repositories/project_repository.py`: extend revision persistence to include reference hashes and module/engine metadata, using a versioned/migrated schema.

### ADD (small, focused modules)

```text
app/
  contracts/
    calculation_request.py
    calculation_response.py
    input_schema.py
    module_definition.py
    visualization_model.py
    summary_model.py
  ports/
    reference_data_port.py
    project_repository_port.py
    report_export_port.py
  services/
    module_catalog_service.py
    visualization_service.py
    calculation_workflow_service.py

gui/
  presenters/                 # or viewmodels/; choose one convention
  renderers/
    equation_renderer.py
```

The exact folder names can be aligned with the actual code style. Avoid creating empty layers that have no clear responsibility.

### DEFER / KEEP ON ROADMAP

- Cloud Drive synchronization until its planned phase; preserve deterministic offline calculation as the V1 baseline.
- New Steel and Concrete/CMU engines until their calculation modules and benchmark suites are implemented.
- Large-scale folder reorganization. The SAD explicitly recommends incremental extension rather than deleting/recreating the repository structure.

---

## 9. Phased implementation plan for the coding agent

### Phase 0 — Read-only architecture baseline

- Read `AGENTS.md`, `rules.md`, `proposed.md`, `state_summary.txt` before any task.
- Map imports/dependencies and module/template IDs.
- Capture baseline UI screenshots using the existing approved screenshot procedure.
- Record existing test results and calculation benchmark outputs.
- Produce a file-level impact plan. **No file edits in this phase.**

### Phase 1 — Canonical contracts and module catalog

- Add typed contracts and `ModuleDefinition` catalog.
- Register each currently implemented module exactly once.
- Generate dialog/template availability and engine dispatch from the catalog.
- Mark unimplemented Steel/Concrete templates as coming soon/unavailable; do not route them to C&C.
- Add tests for catalog uniqueness, module availability and routing.

### Phase 2 — Dependency inversion and reference data port

- Remove concrete `app.services.KnowledgeBaseService` imports from `core/`.
- Keep reference lookup deterministic and preserve existing verified data.
- Add compatibility adapters so existing calculation functions can be migrated one module at a time.
- Verify numerical parity against all existing benchmark tests.

### Phase 3 — Structured calculation trace and reference snapshots

- Introduce typed calculation steps, quantities and code references.
- Preserve equation/substitution/result/limit/DCR traceability.
- Capture reference file IDs and SHA-256 values with each saved revision.
- Add tests for complete traceability and historical snapshot consistency.

### Phase 4 — Visualization model and live synchronization

- Add one visualization mapper per implemented module family.
- Update Panel 2 through the typed visualization model.
- Implement immediate geometry redraw from input changes and controlled recalculation of derived forces.
- Mark calculation/diagram state as stale when inputs change.
- Verify the visual design remains unchanged using screenshot regression.

### Phase 5 — Mathematical calculation-sheet renderer

- Add an offline renderer for LaTeX equations inside the existing Panel 3.
- Render equation, variable substitutions, units, results, limits and references in a consistent per-step layout.
- Ensure formula rendering does not require internet access.
- Add tests for special symbols, superscripts/subscripts, fractions, aligned equations, units and long expressions.

### Phase 6 — Persistence and workflow integration

- Wire Add Calculation to project creation/persistence and the canonical catalog.
- Wire Run Calculation and Save Revision to their explicit use cases.
- Confirm calculation IDs and revision IDs persist correctly.
- Ensure loading a prior revision restores its inputs and displays its original reference snapshot.

### Phase 7 — QA and release gate

- Run unit, benchmark, regression, GUI and E2E tests in a fully provisioned environment containing the pinned PySide6/pytest dependencies.
- Compare C&C and Wood results against existing verified baselines.
- Run screenshot regression for the frozen UI.
- Verify offline behavior and deterministic results.
- Do not mark a module available until its engine, UI route, traceability and tests are complete.

---

## 10. Priority matrix

| Priority | Issue | Required outcome |
|---|---|---|
| **P0** | Dependency inversion | GUI depends on application contracts; core no longer depends on concrete app services |
| **P0** | Module/template registry mismatch | One catalog controls dialog, dispatcher and workspace routing |
| **P0** | Incomplete input defaults | Missing required values produce INCOMPLETE/INVALID INPUT, not silent sample calculations |
| **P1** | LaTeX is not mathematically rendered | Offline equation renderer inside unchanged Panel 3 |
| **P1** | Unstructured diagram dictionaries | Typed VisualizationModel shared across diagrams |
| **P1** | Diagram updates only after Run Calculation | Input-reactive geometry plus synchronized calculated forces/stale-state handling |
| **P1** | Revision persistence not fully wired | Explicit create/run/save/load revision workflows |
| **P1** | Reference hash not snapshotted per calculation | Reproducible calculation revision with reference provenance |
| **P2** | README/architecture documentation drift | Documentation reflects PySide6 and current implementation status |
| **P2** | Exporter CSV parsing and hardcoded catalog exceptions | Track and resolve in separate, tested engineering-data tasks |

---

## 11. Acceptance criteria

The refactor is accepted only when all of the following are true:

### UI preservation

- The approved four-panel design is unchanged.
- No panel is added, removed, rearranged or visually redesigned.
- Existing navigation and approved interaction patterns remain intact.
- Screenshot regression does not show unintended visual changes.

### Architecture

- GUI modules do not import `core/` implementation modules directly.
- Core calculation modules do not import concrete `app/services/` implementations.
- Calculation dispatch and template metadata share one registry.
- A module cannot be selected as available unless its engine/workspace/tests are ready.

### Engineering calculation integrity

- Existing benchmark results remain numerically equivalent unless a separately reviewed engineering correction is approved.
- ASD and LRFD remain strictly separated.
- Units remain explicit and consistent with the US Customary project convention.
- Missing mandatory inputs cannot silently fall back to sample values.
- No engineering equation is implemented in a GUI widget or diagram renderer.

### Calculation traceability

- Every displayed formula has a structured calculation step.
- Equation, substitution, result, acceptance limit and reference are linked.
- References include edition/section and source-file provenance; saved revisions capture source hashes.
- PDF/XLSX and GUI use the same result model.

### Visualization and state

- Panel 2 uses a typed VisualizationModel.
- Geometry responds to relevant input changes.
- Derived forces are from the calculation engine.
- Stale/invalid calculation state is visible and cannot be mistaken for a current verified result.

### Persistence and QA

- Calculation creation, calculation execution and revision saving are correctly wired to SQLite.
- Previous revisions remain immutable and can be loaded.
- Automated unit, benchmark, regression and end-to-end tests pass in the supported environment.

---

## 12. Protected files and change-control requirements

The current review did not modify any file in the repository. The coding agent must preserve the project's established change-control rules:

- `rules.md` is locked and only the primary agent may update it with explicit user instruction.
- `proposed.md` is the authoritative SAD; only Section 2.1 may be updated under the existing synchronization rule. Do not rewrite other sections to introduce this proposal.
- `state_summary.txt` is owned by the primary agent/project coordinator.
- Existing verified CSV files in `database/` and procedure Markdown files in `procedures/` are protected. Do not modify, delete or reorganize them without explicit approval.
- Do not touch the approved UI reference screenshots or replace the agreed layout.
- Do not commit, push, create branches or modify repository files as part of an architecture-review-only task.

Treat this document as a **proposed architecture addendum and implementation brief**, not as permission to bypass the project's locked files or change-control requirements.

---

## 13. Copy-ready instruction for the coding agent

> You are the implementation agent for the Structural Engineering Calculation Application. First read `AGENTS.md`, `rules.md`, `proposed.md` and `state_summary.txt`. Review this Architecture Review & Target Architecture Proposal before making changes.
>
> **The approved PySide6 four-panel UI is frozen. Do not redesign or visually alter it.** Keep Panel 1 Inputs, Panel 2 Diagram (top right), Panel 3 Calculation Sheet (equations and code references together), and Panel 4 Summary in their existing positions and visual style. Do not add a separate reference panel.
>
> Do not rewrite the application from scratch. Refactor incrementally using lightweight Clean Architecture / Ports-and-Adapters principles. Preserve current verified C&C and Wood calculation results. Do not move, rewrite or delete protected CSV/Markdown knowledge-base files. Respect `rules.md`, `proposed.md` and `state_summary.txt` ownership/change-control rules.
>
> First complete Phase 0 as a read-only assessment and return: dependency map, module/template registry audit, calculation-result data-flow, UI event-flow, persistence wiring audit, file-level KEEP/REFACTOR/ADD/DEFER list, risks and test baseline. Do not edit any file during this assessment.
>
> After explicit implementation authorization, work phase by phase. Introduce typed application contracts, a canonical module catalog, a reference-data port, structured calculation steps/code references, a typed VisualizationModel and an offline equation renderer inside the existing Panel 3. Make Panel 2 responsive to input changes while deriving all engineering forces from the deterministic calculation engine. Wire project creation and immutable revision saving through explicit application use cases.
>
> Never put engineering equations in GUI or visualization code. Never allow core calculation modules to import GUI or concrete application services. Never silently use sample defaults for missing required user inputs. Never expose unimplemented or unverified modules as available.
>
> For every implementation phase, report exact files added/modified, tests run, benchmark comparisons, screenshot-regression outcome and any numerical differences. Stop and escalate if an engineering assumption, code reference or existing protected file needs to change without clear approval.

---

## 14. Source files reviewed

- [`AGENTS.md`](https://github.com/mndo2710/structural-engineering-kb/blob/main/AGENTS.md)
- [`README.md`](https://github.com/mndo2710/structural-engineering-kb/blob/main/README.md)
- [`rules.md`](https://github.com/mndo2710/structural-engineering-kb/blob/main/rules.md)
- [`proposed.md` – SAD v1.0](https://github.com/mndo2710/structural-engineering-kb/blob/main/proposed.md)
- [`state_summary.txt`](https://github.com/mndo2710/structural-engineering-kb/blob/main/state_summary.txt)
- [`docs/review_audit_day14.md`](https://github.com/mndo2710/structural-engineering-kb/blob/main/docs/review_audit_day14.md)
- [`core/common/calculation_result.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/core/common/calculation_result.py)
- [`app/services/calculation_service.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/app/services/calculation_service.py)
- [`app/services/knowledge_base_service.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/app/services/knowledge_base_service.py)
- [`app/services/project_service.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/app/services/project_service.py)
- [`storage/repositories/project_repository.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/storage/repositories/project_repository.py)
- [`gui/main_window.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/gui/main_window.py)
- [`gui/widgets/base_workspace.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/gui/widgets/base_workspace.py)
- [`gui/widgets/cc_workspace.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/gui/widgets/cc_workspace.py)
- [`gui/widgets/wood_workspace.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/gui/widgets/wood_workspace.py)
- [`gui/dialogs/add_calculation_dialog.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/gui/dialogs/add_calculation_dialog.py)
- [`core/asce7/wind/parapet.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/core/asce7/wind/parapet.py)
- [`core/nds/fasteners/bolts.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/core/nds/fasteners/bolts.py)
- [`exporters/excel_builder.py`](https://github.com/mndo2710/structural-engineering-kb/blob/main/exporters/excel_builder.py)
- [`requirements.txt`](https://github.com/mndo2710/structural-engineering-kb/blob/main/requirements.txt)

**Review limitation:** This was a static read-only review of repository files and the committed audit/state documents. The application was not launched, tests were not re-executed, and no commit or repository modification was made in this review.
