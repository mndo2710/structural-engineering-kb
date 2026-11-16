# SOFTWARE ARCHITECTURE DOCUMENT (SAD)
## Structural Engineering Calculation Application

**Project:** `structural-engineering-kb`  
**Product:** Standalone Structural Engineering App  
**Document Version:** 1.0 – Proposed Architecture  
**Date:** November 13, 2026  
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
3. **Separation of concerns:** Knowledge Base, Calculation Engine, GUI, cloud synchronization, and report generation must remain independent modules.
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

The existing project has completed all 10 days of Phase 1 Knowledge Base development (66 verified CSV lookup tables and 26 verified 7-section Markdown calculation procedures), Day 11 (Phase 2 Architecture Foundation Part 1), and Day 12 (Phase 2 Architecture Foundation Part 2: SQLite Storage & PySide6 4-Panel GUI Workspace).

The current repository includes:

- `database/` (`asce_7/`, `ibc_cbc/`, `nds_wood/`, `aisc_360/`, `aci_318_tms_402/`, `manufacturer_catalogs/` — 66 verified CSVs with SHA-256 integrity validation)
- `procedures/` (`01_loads_and_seismic/`, `02_wood_design/`, `03_steel_design/`, `04_concrete_masonry_foundation/`, `05_plan_check_responses/`, `06_components_and_cladding/` — 26 verified MD procedures)
- `core/` (`common/`: `calculation_result.py`, `units.py`, `load_combinations.py`, `validation.py`, `exceptions.py`; `asce7/`, `nds/`, `aisc360/`, `aci318/`, `tms402/`)
- `app/` (`services/`: `knowledge_base_service.py`, `project_service.py`, `history_service.py`)
- `storage/` (`repositories/project_repository.py` managing 8 SQLite tables for projects, calculations, inputs, results, and immutable revisions)
- `gui/` (`main_window.py` with expandable/collapsible 48px rail sidebar, segmented ASD/LRFD toggle; `widgets/base_workspace.py` 4-panel grid workspace with interactive diagram and right-aligned code citations; `dialogs/add_calculation_dialog.py` 3-column template selector)
- `exporters/` (`excel_builder.py`, `audit_logger.py`)
- `cloud/`
- `config/` (`app_settings.json`, `active_code_registry.json`, `reference_manifest.json` with 92 verified SHA-256 checksums)
- `tests/` (53 passing unit tests covering units, load combinations, validation, KnowledgeBaseService, SQLite storage, and PySide6 GUI)
- `logs/`
- `docs/`
- `backup/`
- `rules.md`
- `state_summary.txt`
- `main.py`
- `requirements.txt`
- `README.md`

The 10-day Phase 1 Knowledge Base roadmap is 100% completed (synchronized with `state_summary.txt` and `rules.md` as of November 14, 2026).

| Work Package | Status |
|---|---|
| Day 1 – ASCE 7-22 Basic C&C Wind: Parapet and Roof Overhang | Completed |
| Day 2 – C&C Wind/Seismic: Awning, Trellis, Guardrail and Load Combinations | Completed |
| Day 3 – NDS 2024 Fasteners: Nails, Screws, Lag Screws and Simpson SDS | Completed |
| Day 4 – NDS 2024 Bolts and Connection Limit States | Completed |
| Day 5 – Wood Lateral Systems (SDPWS Diaphragms, Shear Walls & Simpson C-C-2026 Connectors) | Completed |
| Day 6 – AISC 360-22 Connections Part 1 (Bolts, Welds & AISC DG1 Base Plates) | Completed |
| Day 7 – AISC 360-22 Connections Part 2 (Shear Tabs, Single/Double Angles, Eccentric Bolt Groups & Ch. K HSS) | Completed |
| Day 8 – ACI/TMS Anchorage (ACI 318-19 Ch. 17 Concrete Anchors, TMS 402-22 CMU Breakout & Embedded Steel Posts) | Completed |
| Days 9–10 – End-to-End C&C Sub-Assembly Procedures & Master Plan Check Response Library | Completed |

## 2.2 Locked Engineering Data Conventions

The following rules are mandatory and must not be changed without an explicit project decision.

### Language and Units

- User-facing communication: Vietnamese.
- CSV, Markdown, Python code, variable names, class names, and filenames: US Structural Engineering English.
- Unit system: US Customary.
- Design methods: ASD and LRFD.

### CSV Standard

- Filename convention: `[Code]_[TableNumber].csv`.
- Encoding: `utf-8-sig`.
- Preserve exact source row and column order.
- Preserve exact mathematical symbols.
- Include complete verbatim footnotes at the bottom.
- Perform five-step verification against the applicable TCUS reference PDFs.

### Procedure Markdown Standard

Every engineering procedure must follow this seven-section Plan Check structure:

1. Assumptions & Load Path
2. Load Combos & Internal Forces
3. Primary Member Checks
4. Sequential Connection Limit States
5. Supporting Substrate Checks
6. Mandatory Detailing Notes
7. Summary Checklist Table

### Google Drive File Standard

CSV, Markdown, and TXT files must remain raw files.

The existing workflow uses direct file uploads with:

- `base64_content="file:///..."`
- `mime_type="application/octet-stream"`

The application must not convert these files into Google Sheets or Google Docs.

### State Summary

`/structural-engineering-kb/state_summary.txt` remains the central project progress record.

It must be updated every three development turns with:

- Completed work.
- Current progress.
- Active file IDs.
- Pending work.
- Next steps.

---

# 3. SYSTEM OVERVIEW

## 3.1 High-Level Architecture

The application will use a layered architecture.

```text
┌──────────────────────────────────────────────────────┐
│                 WINDOWS DESKTOP APP                   │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │                  GUI LAYER                      │  │
│  │  Project | Inputs | Results | Reports | Settings│ │
│  └───────────────────────┬────────────────────────┘  │
│                          │                           │
│  ┌───────────────────────▼────────────────────────┐  │
│  │             APPLICATION SERVICE LAYER          │  │
│  │  Workflow | Validation | Project | Calculation │  │
│  └───────────────┬───────────────────┬────────────┘  │
│                  │                   │               │
│  ┌───────────────▼────────┐  ┌───────▼────────────┐  │
│  │  CALCULATION ENGINE   │  │ KNOWLEDGE BASE     │  │
│  │                      │  │                    │  │
│  │ ASCE 7                │  │ CSV Tables         │  │
│  │ NDS                   │  │ Procedure MD       │  │
│  │ AISC 360              │  │ Code References    │  │
│  │ ACI 318               │  │ Manufacturer Data  │  │
│  │ TMS 402               │  │ Metadata           │  │
│  └───────────────┬───────┘  └──────────┬─────────┘  │
│                  │                     │            │
│  ┌───────────────▼─────────────────────▼─────────┐  │
│  │               DATA & STORAGE LAYER            │  │
│  │ Local Cache | Project Database | File Storage│  │
│  └───────────────────────┬───────────────────────┘  │
│                          │                           │
│  ┌───────────────────────▼───────────────────────┐  │
│  │              CLOUD SYNC SERVICE               │  │
│  │               Google Drive                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │                 EXPORT ENGINE                  │  │
│  │              XLSX | PDF | CSV                  │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

## 3.2 Architectural Layers

| Layer | Responsibility |
|---|---|
| GUI Layer | User interaction and presentation |
| Application Service Layer | Coordinates workflows and application operations |
| Calculation Engine | Performs engineering calculations |
| Knowledge Base | Stores engineering tables and procedures |
| Data & Storage Layer | Stores projects, calculation records, and local reference files |
| Cloud Sync Service | Synchronizes raw files with Google Drive |
| Export Engine | Generates calculation reports and supporting files |

Each layer must communicate through defined interfaces. The GUI must not directly implement engineering equations or read Google Drive files.

---

# 4. TECHNOLOGY STACK

## 4.1 Recommended Technologies

| Component | Recommended Technology | Purpose |
|---|---|---|
| Programming Language | Python 3.x | Main application language |
| Desktop GUI | PySide6 | Native Windows desktop interface |
| Calculation Engine | Python | Deterministic engineering calculations |
| Numerical Operations | NumPy / SciPy, when needed | Numerical calculations |
| Reference Database | CSV / JSON | Engineering lookup tables |
| Procedure Files | Markdown | Engineering workflows |
| Project Database | SQLite | Project and calculation records |
| Excel Export | openpyxl / XlsxWriter | XLSX report generation |
| Excel Desktop Integration | xlwings, optional | Interacting with installed Excel |
| PDF Export | ReportLab | Calculation report generation |
| Testing | pytest | Unit and regression testing |
| Version Control | Git | Source code and change tracking |
| Application Packaging | PyInstaller | Windows executable |
| Cloud Storage | Google Drive API | Remote file synchronization |

The final package versions should be pinned in the project's dependency configuration and tested together before release.

## 4.2 Technology Selection Rationale

**PySide6**

Provides a desktop GUI suitable for engineering forms, tables, calculation result panels, navigation trees, and report previews.

**Python Calculation Engine**

Allows engineering equations to be implemented as explicit, testable functions. It also provides a consistent environment for ASD/LRFD calculations.

**CSV and Markdown**

Preserves the existing Knowledge Base format. The application does not need to migrate the current reference library into a proprietary database format.

**SQLite**

Stores project-specific information without requiring a separate database server.

**Google Drive API**

Provides cloud synchronization while preserving the raw files and existing folder structure.

---

# 5. KNOWLEDGE BASE ARCHITECTURE

## 5.1 Purpose

The Knowledge Base is the engineering reference layer.

It provides the source data required by the Calculation Engine but does not itself perform calculations.

The existing `database/` and `procedures/` folders remain the primary source of engineering reference content.

## 5.2 Knowledge Base Structure

```text
structural-engineering-kb/
│
├── database/
│   ├── asce_7/
│   │   └── v7_22/
│   │
│   ├── ibc_cbc/
│   │   └── v2024_ibc_v2025_cbc/
│   │
│   ├── nds_wood/
│   │   └── v2024/
│   │       └── sdpws/
│   │
│   ├── aisc_360/
│   │   └── v2022/
│   │
│   ├── aci_318_tms_402/
│   │
│   └── manufacturer_catalogs/
│       └── simpson_strong_tie/
│
├── procedures/
│   ├── 01_loads_and_seismic/
│   ├── 02_wood_design/
│   ├── 03_steel_design/
│   ├── 04_concrete_masonry_foundation/
│   ├── 05_plan_check_responses/
│   └── 06_components_and_cladding/
│
└── state_summary.txt
```

The structure above preserves the existing project organization. Additional version-specific folders may be introduced when new code editions are added.

## 5.3 Knowledge Base Data Access

The application will use a dedicated `KnowledgeBaseService`.

Its responsibilities include:

- Locate a requested CSV table.
- Load CSV data.
- Validate file encoding and structure.
- Identify the applicable code edition.
- Retrieve procedure Markdown.
- Read reference metadata.
- Report missing or outdated reference files.

The Calculation Engine must not hardcode engineering table values when those values are intended to come from the Knowledge Base.

## 5.4 Proposed Metadata Standard

A metadata file should be introduced to identify each reference file.

Suggested structure:

```json
{
  "reference_id": "NDS-2024-Table-12A",
  "file_name": "NDS-2024_Table_12A.csv",
  "code": "NDS",
  "edition": "2024",
  "reference_type": "design_table",
  "unit_system": "US_Customary",
  "encoding": "utf-8-sig",
  "verification_status": "pending",
  "source_reference": "TCUS",
  "last_verified": null,
  "revision": "1.0"
}
```

This metadata is an application-level addition. It does not replace the existing CSV content or its formatting requirements.

## 5.5 Reference Data Integrity

The application should maintain:

- File name.
- Code edition.
- Reference identifier.
- Revision.
- Verification status.
- Source reference.
- Last synchronization timestamp.
- File checksum.

A reference file should be flagged if its checksum changes after local verification.

The application must not silently replace a verified local reference file with an unverified version.

---

# 6. CALCULATION ENGINE ARCHITECTURE

## 6.1 Core Responsibility

The Calculation Engine is the central engineering component.

It converts the calculation procedures in Markdown into executable, deterministic Python functions.

The Markdown procedure remains the documented engineering workflow. The Python implementation performs the actual calculations.

**Important:** A Markdown procedure is not an executable calculation module. The engineering logic must be implemented and tested separately in Python.

## 6.2 Calculation Engine Structure

```text
core/
│
├── common/
│   ├── units.py
│   ├── load_combinations.py
│   ├── material_properties.py
│   ├── calculation_result.py
│   ├── validation.py
│   └── exceptions.py
│
├── asce7/
│   ├── wind/
│   │   ├── velocity_pressure.py
│   │   ├── c_and_c_pressure.py
│   │   ├── parapet.py
│   │   ├── roof_overhang.py
│   │   ├── awning.py
│   │   └── trellis.py
│   │
│   └── seismic/
│       └── seismic_loads.py
│
├── nds/
│   ├── fasteners/
│   │   ├── nails.py
│   │   ├── screws.py
│   │   ├── lag_screws.py
│   │   └── bolts.py
│   │
│   ├── lateral/
│   │   ├── shear_walls.py
│   │   └── diaphragms.py
│   │
│   └── connections/
│
├── aisc360/
│   ├── bolts.py
│   ├── welds.py
│   ├── shear_tab.py
│   ├── single_angle.py
│   ├── base_plate.py
│   └── hss_connections.py
│
├── aci318/
│   └── anchors/
│
└── tms402/
    └── masonry_anchors/
```

The directory structure may be expanded as calculation modules are implemented.

## 6.3 Calculation Module Design

Each calculation module should follow a consistent structure:

1. Input definition.
2. Input validation.
3. Reference data retrieval.
4. Intermediate calculations.
5. Limit-state calculations.
6. Governing result selection.
7. ASD/LRFD evaluation.
8. Calculation output generation.

Example:

```python
def calculate_nds_bolt_connection(inputs, knowledge_base):
    """
    Calculate an NDS bolt connection.

    Returns:
        CalculationResult
    """

    validate_inputs(inputs)

    reference_data = knowledge_base.get_nds_bolt_tables(
        edition="2024"
    )

    limit_states = calculate_bolt_limit_states(
        inputs,
        reference_data
    )

    governing_result = determine_governing_limit_state(
        limit_states
    )

    return build_calculation_result(
        inputs=inputs,
        limit_states=limit_states,
        governing_result=governing_result
    )
```

This is an architectural example, not a completed engineering implementation.

## 6.4 Calculation Result Standard

All calculation modules should return a common result object.

Proposed fields:

| Field | Description |
|---|---|
| `calculation_id` | Unique calculation identifier |
| `module_id` | Calculation module |
| `code_edition` | Applicable code edition |
| `design_method` | ASD or LRFD |
| `input_parameters` | Original user inputs |
| `assumptions` | Calculation assumptions |
| `intermediate_results` | Intermediate calculations |
| `limit_states` | Individual limit-state results |
| `governing_limit_state` | Controlling limit state |
| `demand` | Applied demand |
| `capacity` | Available capacity |
| `dcr` | Demand-to-capacity ratio, when applicable |
| `status` | Pass, fail, or requires review |
| `reference_files` | Referenced CSV and Markdown files |
| `software_version` | Calculation module version |
| `warnings` | Calculation warnings |

## 6.5 ASD and LRFD Handling

ASD and LRFD must be explicitly identified in the calculation input.

The application must not mix ASD and LRFD values in the same design check.

The calculation engine should:

- Identify the applicable design method.
- Retrieve the correct design values.
- Apply the applicable adjustment or resistance factors.
- Calculate demand and capacity consistently.
- Display the applicable acceptance criteria.
- Identify the governing limit state.

Where both methods are available, the application should allow the user to run both methods and compare the results.

## 6.6 Units and Numerical Precision

All calculations will use US Customary units.

The application should use a consistent internal unit convention for each calculation module.

Requirements:

- Validate units at input.
- Prevent accidental mixing of incompatible units.
- Keep full numerical precision during calculations.
- Apply display rounding only when presenting results.
- Identify units beside every input and output.
- Record the unit convention in the calculation report.

The unit system should be handled centrally rather than implemented independently in each GUI form.

## 6.7 Calculation Traceability

Every calculation should be reproducible.

The application must retain:

- Original input values.
- Calculation date.
- Code edition.
- Reference file revision.
- Calculation module version.
- Intermediate values.
- Governing limit state.
- Final result.

A calculation report should show the engineering logic, not only the final DCR.

---

# 7. APPLICATION SERVICE LAYER

## 7.1 Purpose

The Application Service Layer connects the GUI, Calculation Engine, Knowledge Base, project database, and Export Engine.

It controls the application workflow without containing engineering equations.

## 7.2 Main Services

| Service | Responsibility |
|---|---|
| `ProjectService` | Create, open, save, and manage projects |
| `CalculationService` | Execute calculation modules |
| `KnowledgeBaseService` | Retrieve reference data and procedures |
| `ValidationService` | Validate user inputs and application data |
| `ReportService` | Prepare calculation reports |
| `CloudSyncService` | Synchronize files with Google Drive |
| `SettingsService` | Manage application settings |
| `HistoryService` | Maintain calculation revisions and history |

The GUI should communicate with these services rather than calling calculation functions directly.

---

# 8. GUI ARCHITECTURE

## 8.1 Main Interface

The Windows application should use a navigation-based layout.

```text
┌─────────────────────────────────────────────────────┐
│ STRUCTURAL ENGINEERING CALCULATION APP               │
├───────────────┬─────────────────────────────────────┤
│               │                                     │
│ Dashboard     │  Project Information                │
│               │                                     │
│ Projects      │  Recent Calculations                │
│               │                                     │
│ C&C Loads     │  Quick Access                       │
│               │                                     │
│ Wood          │  Synchronization Status             │
│ Connections   │                                     │
│               │                                     │
│ Steel         │  Reference Database Status          │
│ Connections   │                                     │
│               │                                     │
│ Concrete      │                                     │
│ Anchors       │                                     │
│               │                                     │
│ Reports       │                                     │
│               │                                     │
│ Settings      │                                     │
└───────────────┴─────────────────────────────────────┘
```

## 8.2 Initial Modules

The initial application scope should prioritize the following modules.

### A. Components & Cladding

- Parapet wind pressure.
- Roof overhang wind pressure.
- Awning and canopy loads.
- Trellis wind and seismic loads.
- Guardrail and handrail loads.
- Applicable wind and seismic load combinations.

### B. Wood Connections

- Nail connections.
- Wood screw connections.
- Lag screw connections.
- Bolt connections.
- Simpson SDS connections.
- Wood connection limit states.

### C. Steel Connections

- Bolt connections.
- Weld connections.
- Shear tab.
- Single-angle connections.
- Base plates.
- HSS connections.

### D. Concrete and Masonry Anchorage

- Cast-in anchors.
- Post-installed anchors.
- Concrete anchor limit states.
- CMU anchorage.
- Embedded posts.

The interface may display future modules as unavailable until their corresponding calculation modules are implemented and verified.

## 8.3 Calculation Workspace

Each calculation screen should have four main areas:

1. **Input Panel:** User-defined parameters.
2. **Reference Panel:** Applicable code tables and assumptions.
3. **Calculation Panel:** Intermediate equations and results.
4. **Summary Panel:** Governing limit state, DCR, and status.

The user should be able to inspect the calculation steps before exporting a report.

## 8.4 Calculation Status

The application should use explicit statuses:

- `PASS`
- `FAIL`
- `REQUIRES REVIEW`
- `INCOMPLETE`
- `INVALID INPUT`

A missing input or unsupported condition must never be reported as a passing calculation.

---

# 9. PROJECT AND DATA STORAGE

## 9.1 Storage Strategy

The application will use two storage categories.

**A. Engineering Knowledge Base**

- CSV files.
- Markdown procedures.
- Reference metadata.
- Manufacturer reference files.

**B. Project Data**

- Project information.
- Calculation inputs.
- Calculation results.
- Calculation revisions.
- Report references.
- Project settings.

The Knowledge Base and project records must remain separate.

## 9.2 Proposed Project Folder Structure

```text
Projects/
│
├── Project_001/
│   ├── project.json
│   ├── calculations/
│   │   ├── C&C/
│   │   ├── Wood_Connections/
│   │   ├── Steel_Connections/
│   │   └── Anchors/
│   │
│   ├── reports/
│   │   ├── PDF/
│   │   └── XLSX/
│   │
│   └── attachments/
│
└── Project_002/
```

## 9.3 SQLite Database

SQLite should store structured project information.

Proposed database tables:

| Table | Purpose |
|---|---|
| `projects` | Project information |
| `calculations` | Calculation records |
| `calculation_inputs` | Original input parameters |
| `calculation_results` | Final and intermediate results |
| `calculation_revisions` | Calculation history |
| `reference_files` | Reference file metadata |
| `sync_history` | Cloud synchronization records |
| `application_settings` | Application preferences |

The actual schema should be finalized during implementation.

## 9.4 Revision Management

A calculation must not be silently overwritten.

When inputs change, the application should create a new revision or clearly record the change.

Each revision should retain:

- Previous input values.
- New input values.
- Previous calculation results.
- New calculation results.
- Revision date.
- Software version.

---

# 10. CLOUD-CONNECTED ARCHITECTURE

## 10.1 Cloud Operation

Google Drive will serve as the remote storage and synchronization platform for the engineering Knowledge Base.

The application will maintain a local copy of the required reference files.

This allows the application to:

- Access reference files locally.
- Perform calculations without a continuous internet connection.
- Synchronize updated CSV and Markdown files.
- Detect remote changes.
- Maintain synchronization history.

Cloud connectivity is a data synchronization capability, not an AI integration.

## 10.2 Proposed Synchronization Architecture

```text
              GOOGLE DRIVE
                   │
                   │
           Google Drive API
                   │
                   ▼
          CloudSyncService
                   │
          ┌────────┴────────┐
          │                 │
          ▼                 ▼
     Download Files     Upload Files
          │                 │
          └────────┬────────┘
                   │
                   ▼
             Local Cache
                   │
          ┌────────┴────────┐
          │                 │
          ▼                 ▼
     Knowledge Base    File Validation
          │
          ▼
     Calculation Engine
```

## 10.3 Synchronization Rules

The application should support:

- Manual synchronization.
- Synchronization on application startup, when enabled.
- Synchronization before application shutdown, when enabled.
- Detection of changed files.
- File checksum verification.
- Synchronization error reporting.
- Local cache preservation.

The application should not overwrite a locally modified file without checking its revision.

## 10.4 Conflict Management

A conflict occurs when the local and remote copies of the same file have both changed.

Proposed behavior:

1. Detect the conflict.
2. Preserve both copies.
3. Identify local and remote modification timestamps.
4. Display the conflict to the user.
5. Require an explicit resolution.
6. Record the resolution in synchronization history.

Automatic merging of CSV or Markdown files should not be enabled in V1.

## 10.5 Cloud Security

The application should use Google OAuth 2.0 for user authorization.

Security requirements:

- Do not hardcode access tokens or client secrets in source code.
- Store credentials using an appropriate Windows secure credential store.
- Request only the Google Drive permissions required by the application.
- Do not transmit project calculations unless explicitly configured.
- Provide a visible synchronization status.
- Handle expired credentials and revoked access gracefully.

## 10.6 Offline Behavior

| Function | Internet Required |
|---|---|
| Open local project | No |
| Perform calculations | No |
| Read local CSV files | No |
| Read local Markdown procedures | No |
| Generate PDF report | No |
| Generate Excel report | No |
| Download updated Knowledge Base | Yes |
| Upload updated Knowledge Base | Yes |
| Check cloud synchronization status | Yes |

Cloud synchronization must not block the Calculation Engine from operating on valid local data.

---

# 11. EXPORT ENGINE

## 11.1 Purpose

The Export Engine generates engineering deliverables from calculation results.

It must not independently recalculate engineering equations.

## 11.2 Supported Outputs

| Format | Purpose |
|---|---|
| PDF | Formal calculation report |
| XLSX | Detailed calculation workbook |
| CSV | Structured calculation output |

## 11.3 PDF Report Structure

Proposed report layout:

1. Project Information.
2. Calculation Title.
3. Design Criteria and Code References.
4. Assumptions and Load Path.
5. Input Parameters.
6. Load Combinations and Internal Forces.
7. Primary Member Checks.
8. Connection Limit States.
9. Supporting Substrate Checks.
10. Detailing Notes.
11. Summary Checklist.
12. Calculation References and Revision Information.

The seven-section procedure structure should remain the engineering basis for the report. Additional cover and project information may be included without changing the procedure standard.

## 11.4 Excel Report Structure

The Excel report should provide:

- Input sheet.
- Calculation sheet.
- Limit-state summary.
- Reference data.
- Design summary.

Where applicable, the workbook should display:

`Equation → Substitution → Result → Limit → DCR`

The exported workbook should preserve the numerical results and traceability of the calculation performed by the application.

---

# 12. ENGINEERING VERIFICATION AND QUALITY CONTROL

## 12.1 Testing Philosophy

Engineering verification is a mandatory development requirement.

A calculation module is not ready for release merely because its Python code runs without errors.

## 12.2 Testing Levels

### Level 1 – Unit Testing

Test individual calculation functions.

Examples:

- Wind pressure calculation.
- Bolt yield limit equations.
- Wood fastener adjustment factors.
- Weld strength.
- Concrete anchor limit states.

### Level 2 – Reference Data Testing

Verify:

- CSV encoding.
- Expected column names.
- Expected row counts.
- Required footnotes.
- Reference edition.
- File checksum.
- Data retrieval behavior.

### Level 3 – Benchmark Testing

Compare application outputs against independently verified engineering calculations.

Each benchmark should include:

- Input data.
- Applicable code edition.
- Reference source.
- Hand calculation or trusted calculation reference.
- Expected result.
- Accepted numerical tolerance.
- Verification status.

### Level 4 – Regression Testing

When a calculation function changes, previously verified benchmark cases must be rerun.

A change in one calculation module must not silently affect unrelated modules.

### Level 5 – End-to-End Testing

Test the complete workflow:

`Input → Validation → Reference Retrieval → Calculation → Result → Report`

## 12.3 Calculation Module Release Criteria

A module may be released only when:

- Inputs are validated.
- Applicable code references are identified.
- Engineering equations are documented.
- ASD/LRFD handling is verified, where applicable.
- Limit states are checked.
- Benchmark tests pass.
- Regression tests pass.
- Calculation output is traceable.
- Engineering review is completed.

## 12.4 Engineering Responsibility

The application is a calculation aid.

It does not replace engineering judgment, review of project-specific conditions, verification of applicable code editions, or professional responsibility.

The software must clearly distinguish between a completed calculation and an engineering-approved design.

---

# 13. ERROR HANDLING AND APPLICATION LOGGING

## 13.1 Error Categories

| Error Category | Example | Application Response |
|---|---|---|
| Input Error | Missing bolt diameter | Request valid input |
| Unit Error | Incompatible units | Stop calculation and identify issue |
| Reference Error | Required CSV missing | Stop affected calculation |
| Data Error | Invalid CSV structure | Flag reference file |
| Calculation Error | Unsupported design condition | Return requires review |
| Cloud Error | Google Drive unavailable | Continue using valid local cache |
| Export Error | PDF generation failure | Preserve calculation record |
| Internal Error | Unexpected Python exception | Log error and show user-friendly message |

## 13.2 Logging

The application should maintain local logs.

Suggested structure:

```text
logs/
├── application.log
├── calculation.log
├── cloud_sync.log
└── error.log
```

Logs should include timestamps, module identifiers, and error descriptions.

Sensitive credentials must never be written to log files.

---

# 14. SECURITY AND DATA INTEGRITY

The application should implement the following controls:

- OAuth-based cloud authentication.
- Secure local credential storage.
- Local file integrity checks.
- Input validation.
- Controlled file synchronization.
- Calculation revision history.
- Application error logging.
- Backup and recovery for project records.
- Clear separation between reference files and user project files.

The application should not execute code embedded in CSV or Markdown files.

Markdown files must be treated as reference content, not executable instructions.

---

# 15. PROPOSED REPOSITORY STRUCTURE

The following structure extends the existing repository skeleton while preserving the existing `database/` and `procedures/` conventions.

```text
structural-engineering-kb/
│
├── database/
│   ├── asce_7/
│   ├── ibc_cbc/
│   ├── nds_wood/
│   ├── aisc_360/
│   ├── aci_318_tms_402/
│   └── manufacturer_catalogs/
│
├── procedures/
│   ├── 01_loads_and_seismic/
│   ├── 02_wood_design/
│   ├── 03_steel_design/
│   ├── 04_concrete_masonry_foundation/
│   ├── 05_plan_check_responses/
│   └── 06_components_and_cladding/
│
├── core/
│   ├── common/
│   ├── asce7/
│   ├── nds/
│   ├── aisc360/
│   ├── aci318/
│   └── tms402/
│
├── app/
│   ├── services/
│   ├── models/
│   ├── repositories/
│   └── controllers/
│
├── gui/
│   ├── main_window/
│   ├── dashboard/
│   ├── projects/
│   ├── components_and_cladding/
│   ├── wood_connections/
│   ├── steel_connections/
│   ├── concrete_anchors/
│   ├── reports/
│   └── settings/
│
├── exporters/
│   ├── pdf/
│   ├── excel/
│   └── csv/
│
├── cloud/
│   ├── google_drive/
│   ├── sync/
│   └── authentication/
│
├── storage/
│   ├── local_cache/
│   ├── projects/
│   └── backups/
│
├── config/
│   ├── app_settings.json
│   └── reference_manifest.json
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── benchmark/
│   ├── regression/
│   └── end_to_end/
│
├── logs/
│
├── docs/
│   ├── architecture/
│   ├── engineering_standards/
│   └── development/
│
├── state_summary.txt
├── main.py
├── requirements.txt
└── README.md
```

This is the proposed target structure. Existing folders should be retained and reorganized incrementally rather than deleted and recreated.

---

# 16. DEVELOPMENT ROADMAP

Development should proceed in phases. The existing 10-day Knowledge Base roadmap remains intact.

## Phase 1 – Complete Engineering Knowledge Base

**Objective:** Finish the existing Day 5–10 roadmap.

| Task | Deliverable |
|---|---|
| Day 5 | Wood lateral systems and associated connections |
| Day 6 | AISC bolts, welds, and base plates |
| Day 7 | Steel connection procedures |
| Day 8 | Concrete and masonry anchorage |
| Day 9 | C&C sub-assembly procedures – Part 1 |
| Day 10 | C&C sub-assembly procedures – Part 2 |

**Milestone:** Engineering reference content is sufficiently complete for the selected initial calculation workflows.

## Phase 2 – Architecture Foundation

**Objective:** Implement the application infrastructure.

Tasks:

- Establish Python package structure.
- Implement application settings.
- Implement KnowledgeBaseService.
- Implement local file storage.
- Implement reference metadata.
- Implement SQLite database.
- Implement calculation result data model.
- Implement logging and error handling.

**Milestone:** The application can load, validate, and manage engineering reference files.

## Phase 3 – Calculation Engine

**Objective:** Convert selected Markdown procedures into deterministic Python modules.

Recommended implementation order:

1. C&C wind pressure.
2. Parapet.
3. Roof overhang.
4. Awning/canopy.
5. Trellis.
6. Guardrail/handrail loads.
7. NDS nail/screw/lag screw connections.
8. NDS bolt connections.
9. AISC bolt/weld connections.
10. Concrete and masonry anchorage.

**Milestone:** Selected workflows can calculate independently of the GUI.

## Phase 4 – Desktop GUI

**Objective:** Build the Windows desktop interface.

Tasks:

- Main window.
- Project management.
- Calculation module navigation.
- Input forms.
- Reference display.
- Calculation result display.
- Calculation history.
- Settings.

**Milestone:** Users can perform calculations through the desktop interface.

## Phase 5 – Cloud Synchronization

**Objective:** Connect the application to Google Drive.

Tasks:

- OAuth authentication.
- Google Drive folder mapping.
- File download.
- File upload.
- Checksum validation.
- Conflict detection.
- Sync history.
- Offline cache.

**Milestone:** The application can synchronize raw engineering reference files without converting their formats.

## Phase 6 – Export and Reporting

**Objective:** Generate engineering calculation deliverables.

Tasks:

- PDF calculation reports.
- Excel calculation workbooks.
- CSV calculation summaries.
- Project and revision information.
- Calculation reference traceability.

**Milestone:** A complete calculation can be exported as an engineering deliverable.

## Phase 7 – Verification and Deployment

**Objective:** Prepare the application for controlled use.

Tasks:

- Unit testing.
- Benchmark testing.
- Regression testing.
- End-to-end testing.
- Windows packaging.
- Installation testing.
- Backup and recovery testing.
- User acceptance testing.

**Milestone:** A verified Windows desktop application is available for controlled engineering use.

---

# 17. ACCEPTANCE CRITERIA

The V1 application will be considered functionally complete when the following criteria are satisfied.

| ID | Acceptance Criteria |
|---|---|
| AC-01 | Application launches as a Windows desktop application |
| AC-02 | Existing CSV and Markdown files can be loaded |
| AC-03 | CSV files preserve the required encoding and content |
| AC-04 | Calculation modules retrieve reference data from the Knowledge Base |
| AC-05 | ASD and LRFD calculations are handled consistently |
| AC-06 | Calculation results include intermediate values and governing limit states |
| AC-07 | Calculation results are reproducible from saved inputs and versions |
| AC-08 | User can create and manage projects |
| AC-09 | User can save calculation records and revisions |
| AC-10 | Application can operate with a valid local reference cache |
| AC-11 | Application can synchronize raw files with Google Drive |
| AC-12 | Cloud conflicts do not silently overwrite local files |
| AC-13 | PDF and XLSX reports can be generated |
| AC-14 | Benchmark and regression tests pass for released modules |
| AC-15 | Application contains no AI Agent or AI API dependency in V1 |

---

# 18. ARCHITECTURAL DECISIONS

The following decisions are proposed as the baseline for V1.

| ID | Decision | Rationale |
|---|---|---|
| ADR-01 | Windows desktop application | Matches the selected deployment platform |
| ADR-02 | Python + PySide6 | Provides a maintainable desktop application framework |
| ADR-03 | Deterministic Python Calculation Engine | Ensures reproducible engineering calculations |
| ADR-04 | CSV and Markdown remain primary Knowledge Base formats | Preserves the existing project workflow |
| ADR-05 | SQLite for project records | Provides local structured storage without a database server |
| ADR-06 | Google Drive for cloud synchronization | Preserves the current cloud file organization |
| ADR-07 | Local cache for offline calculation | Prevents cloud availability from blocking engineering work |
| ADR-08 | PDF/XLSX export | Supports common engineering deliverables |
| ADR-09 | No AI integration in V1 | Keeps the calculation workflow deterministic and independent |
| ADR-10 | Benchmark and regression testing required | Establishes calculation verification before release |

---

# 19. KEY RISKS AND MITIGATION

| Risk | Potential Impact | Mitigation |
|---|---|---|
| Incorrect reference table | Incorrect calculation result | Five-step CSV verification and file integrity checks |
| Incorrect Python implementation | Incorrect engineering result | Benchmark testing and engineering review |
| Code edition mismatch | Incorrect design criteria | Explicit code edition selection and reference metadata |
| ASD/LRFD mixing | Invalid design check | Centralized design method validation |
| Cloud synchronization conflict | Loss or inconsistency of reference files | Preserve both versions and require resolution |
| Missing engineering assumptions | Incomplete calculation | Explicit assumptions and warnings |
| Excessive coupling between modules | Difficult maintenance | Layered architecture and defined interfaces |
| Unverified calculation modules | Unreliable output | Release criteria and controlled module status |

---

# 20. FINAL ARCHITECTURE SUMMARY

The proposed application will consist of:

- A Windows desktop interface built with PySide6.
- A deterministic Python Calculation Engine.
- The existing CSV/Markdown Engineering Knowledge Base.
- SQLite project and calculation storage.
- Google Drive synchronization.
- PDF, XLSX, and CSV export.
- Unit, benchmark, regression, and end-to-end testing.

The key architectural distinction is:

**Knowledge Base = Engineering Reference**

**Calculation Engine = Engineering Mathematics**

**Application Services = Workflow Coordination**

**GUI = User Interaction**

**Cloud Sync = Reference File Synchronization**

**Export Engine = Engineering Deliverables**

The V1 application will not depend on Gemini, Antigravity, AI Agents, or any LLM API to perform engineering calculations.

Gemini and Antigravity may continue to be used externally as development tools, but the finished application will run independently.

**Recommended immediate next milestone:** Complete the Day 5–10 Knowledge Base roadmap, then build one end-to-end vertical slice using a selected C&C workflow. This will validate the connection between CSV reference data, Markdown procedures, Python calculations, GUI inputs, and PDF/XLSX output before implementing the remaining modules.
