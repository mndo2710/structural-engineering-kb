# US Structural Engineering Knowledge Base & Standalone Desktop Application (`structural-engineering-kb`)

Deterministic Windows Desktop Structural Engineering Calculation Application (`PySide6` Frozen 4-Panel UI + Clean Architecture / Ports-and-Adapters Engine + SQLite Schema v2 Project Storage + `openpyxl` XLSX & `ReportLab` PDF Exporters + Google Drive Raw Sync) backed by 66 verified US Code Lookup Databases (`.csv`) and 26 Step-by-Step 7-Section Plan Check Calculation Procedures (`.md`) in US Customary Units (`in.`, `ft`, `lbs`, `kips`, `psi`, `ksi`, `psf`, `plf`, `lb-ft`, `kip-ft`) supporting parallel **ASD** and **LRFD** design philosophies.

---

## 1. Active Building Codes & Reference Standards
- **Building Code**: [2024 International Building Code (IBC) / 2025 California Building Code (CBC)](https://codes.iccsafe.org/content/WABellevueBC2021P1/chapter-16-structural-design)
- **Minimum Design Loads**: [ASCE/SEI 7-22 (Minimum Design Loads and Associated Criteria for Buildings and Other Structures)](https://enercalc.com/docs/sel-user-manual/calculation-modules/general/asce-seismic-wall-anchorage-2)
- **Structural Wood & Lateral Design**: AWC NDS 2024 (*National Design Specification for Wood Construction*) & AWC SDPWS 2021 (*Special Design Provisions for Wind and Seismic*)
- **Structural Steel Design**: [ANSI/AISC 360-22, AISC 341-22, AISC Steel Construction Manual (16th Ed.), & AISC Design Guide 1 / 24](https://skyciv.com/docs/)
- **Concrete & Masonry Design**: [ACI 318-19 / 318-25 (Building Code Requirements for Structural Concrete, Chapter 17 Anchorage)](https://www.steelsolver.com/p/anchor-bolt-tension-calculator.html) & [TMS 402/602-22 (Building Code Requirements for Masonry Structures)](https://www.scribd.com/document/450073931/Anchor-pdf)
- **Proprietary Connectors & Anchors**: [Simpson Strong-Tie Wood Construction Connectors (C-C-2026) & Anchoring Systems (C-A-2023)](https://www.strongtie.com/)

---

## 2. Repository Directory Structure & Architecture Overview

```text
structural-engineering-kb/
├── proposal/
│   └── Structural_Calculation_App_Consolidated_Architecture_Proposal.md  # Approved ACP & V1.0 Roadmap
├── config/
│   ├── active_code_registry.json       # Authoritative code editions (ASCE 7-22, NDS 2024, AISC 360-22, etc.)
│   ├── app_settings.json               # Application configuration & exporter settings
│   └── reference_manifest.json         # 92 SHA-256 verified reference checksums (66 CSVs + 26 MDs)
├── database/                           # 66 Protected UTF-8-SIG CSV Code & Manufacturer Lookup Tables
│   ├── asce_7/v7_22/
│   ├── ibc_cbc/v2024_ibc_v2025_cbc/
│   ├── nds_wood/v2024/ (incl. sdpws/)
│   ├── aisc_360/v16th_ed/ch_j_connections/
│   ├── aci_318_tms_402/ (aci_318_19/, tms_402_22/)
│   └── manufacturer_catalogs/simpson_strong_tie/
├── procedures/                         # 26 Protected 7-Section Plan Check Calculation Procedures (.md)
│   ├── 01_loads_and_seismic/
│   ├── 02_wood_design/
│   ├── 03_steel_design/
│   ├── 04_concrete_masonry_foundation/
│   ├── 05_plan_check_responses/
│   └── 06_components_and_cladding/
├── core/                               # Deterministic Python Calculation Engine (zero GUI/service imports)
│   ├── common/                         # units.py, load_combinations.py, calculation_result.py (CalcStep/RefSpec), math_markup.py
│   ├── ports/                          # ReferenceDataPort protocol
│   ├── asce7/                          # Wind velocity/C&C pressures, parapet, overhang, awning, trellis, guardrail, seismic
│   ├── nds/                            # Bolts (incl. App. E tear-out), nails/screws/lag/SDS, shear walls, diaphragms, Simpson hangers/ties
│   ├── aisc360/                        # Bolts, welds, shear tab (incl. HSS punching), angles, base plate, HSS-to-HSS moment/shear
│   ├── aci318/                         # Ch. 17 cast-in & post-installed concrete anchors
│   └── tms402/                         # CMU out-of-plane breakout & cantilevered embedded steel posts
├── app/                                # Application Layer & Use-Case Orchestration
│   ├── models/                         # Application DTOs, WorkspaceViewModel, DiagramSpec, SummaryViewModel
│   ├── registry/                       # ModuleRegistry, ModuleSpec, FieldSpec (19 canonical / 22 verified catalog templates)
│   ├── controllers/                    # Pure-Python WorkspaceController (load, edit, run, save_revision, stale tracking)
│   ├── services/                       # ProjectService, CalculationService, KnowledgeBaseService, ReportService, HistoryService
│   └── rendering/                      # Multi-target math renderers (KaTeX, RichText, ReportLab, openpyxl) & DiagramSpec builders
├── gui/                                # Frozen PySide6 4-Panel Desktop UI (communicates strictly with app/)
│   ├── main_window.py                  # Header bar (ASD|LRFD toggle), collapsible sidebar (232px / 48px rail), WorkspaceHost
│   ├── dialogs/                        # 3-column AddCalculationDialog (21 visible catalog cards / 19 canonical IDs)
│   ├── widgets/                        # 4-Panel Workspace (Panel 1 Inputs, Panel 2 Diagram, Panel 3 Calc Sheet, Panel 4 Summary)
│   └── assets/                         # Locally vendored offline KaTeX runtime & SVG navigation icons
├── storage/                            # Local Persistence & Backups
│   ├── repositories/                   # SQLite ProjectRepository (Schema v2: projects, groups, ordered items, drafts, revisions)
│   ├── migrations/                     # Transactional v1 -> v2 schema migrations
│   └── backups/                        # Automatic pre-migration SQLite backups
├── exporters/                          # Deterministic Engineering Deliverable Exporters
│   ├── excel_builder.py                # 17-col (A:Q) Arial 10pt openpyxl builder (Calc_Sheet, Database, Source_Audit)
│   ├── pdf_builder.py                  # 12-section ReportLab PDF builder around 7-section Plan Check layout
│   └── audit_logger.py                 # SHA-256 reference provenance & revision audit logger
├── cloud/                              # Google Drive OAuth 2.0 Raw File Synchronization & Offline Cache
├── tests/                              # 5-Level pytest verification suite (Unit, Reference, Benchmark, Regression, E2E)
├── AGENTS.md                           # Global Agent & Subagent Rules
├── rules.md                            # Master Working Rules & Engineering Conventions
├── proposed.md                         # Software Architecture Document (SAD v1.1)
├── state_summary.txt                   # Rolling Project State & Google Drive File ID Registry
├── context_guide.txt                   # Token-Optimized Context Loading Guide
├── requirements.txt                    # Pinned Python dependencies (PySide6, numpy, pandas, openpyxl, reportlab, pytest)
├── launch_app.bat                      # Windows launcher auto-detecting local venv / Python
├── structural_app.spec                 # PyInstaller Windows standalone bundle specification
└── main.py                             # Desktop application entry point
```

---

## 3. Verified Calculation Modules (19 Canonical / 22 Catalog Templates)

- **Loads (ASCE 7-22 / 2024 IBC):** `asce7_parapet_wind`, `asce7_roof_overhang`, `asce7_awning_canopy`, `asce7_trellis_loads`, `ibc_guardrail_loads`
- **Wood (NDS 2024 / SDPWS 2021):** `wood_bolt_lateral`, `wood_fastener_nds` (plus preset templates `wood_nail_lateral`, `wood_screw_withdrawal`, `wood_combined_lateral_withdrawal`), `wood_shear_wall_sdpws`, `wood_diaphragm_sdpws`, `wood_simpson_hanger_tie`
- **Steel (AISC 360-22 / Manual 16th Ed. / DG1):** `aisc_shear_tab`, `aisc_bolt_bearing`, `aisc_welded_connection`, `aisc_angle_connection`, `aisc_base_plate`, `aisc_hss_connection`
- **Concrete & Masonry (ACI 318-19 / TMS 402-22):** `aci318_anchor_tension_shear`, `tms402_cmu_anchorage`, `tms402_embedded_post`

---

## 4. Development & Verification Quickstart (Windows PowerShell)

```powershell
# 1. Install dependencies in a clean Python 3.12+ virtual environment
pip install -r requirements.txt

# 2. Run the full automated verification suite (offscreen Qt + engine benchmarks)
$env:QT_QPA_PLATFORM="offscreen"; pytest -v

# 3. Launch the PySide6 Windows Desktop Application (or double-click launch_app.bat)
python main.py

# 4. Build standalone Windows bundle via PyInstaller
pyinstaller structural_app.spec
```
