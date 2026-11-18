# MASTER WORKING RULES & ENGINEERING CONVENTIONS (`rules.md`)
**Project:** `structural-engineering-kb` (Standalone US Structural Engineering Calculation Application)  
**Last Updated:** November 17, 2026 (Synchronized with Consolidated Architecture Proposal `1KlEES_QYXMFnwYAKwqdathM7LalXiBq8`)  
**Status:** Locked & Active (Auto-updated upon explicit user instruction)

---

## RULE 1: AUTHORITATIVE PROJECT DIRECTION & CHANGE CONTROL
- **Primary Architecture & Roadmap Baseline:**
  - `proposed.md` (*Software Architecture Document — SAD v1.1*) and `proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md` (`1KlEES_QYXMFnwYAKwqdathM7LalXiBq8`) together form the single authoritative design, refactoring, and V1.0 completion specification for the project.
- **Strict Change Control:**
  - Only **Section `2.1 Existing Project Status`** in `proposed.md` may be updated automatically in parallel with `state_summary.txt` to reflect completed work packages and repository inventory.
  - **No other section of `proposed.md`, `proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md`, nor any existing locked file or architectural decision, may be modified, overwritten, or deleted without explicit permission from the user.**
- **Living Rules Update Policy:** Whenever the user establishes a new working rule or modifies an existing rule in chat, `rules.md`, `state_summary.txt`, and persistent agent memory must be updated immediately.

---

## RULE 2: LANGUAGE, UNITS & DESIGN PHILOSOPHY
- **User-Facing Communication (Chat):** 100% Vietnamese (`Tiếng Việt`), concise, direct, peer-to-peer engineering style without conversational filler.
- **Technical Deliverables & Codebase:** 100% US Structural Engineering English across all `.csv`, `.md`, `.py`, `.json`, `.xlsx`, and `.pdf` files, including all variable names, class/function identifiers, comments, drawing notes, and filenames. Never mix Vietnamese text into technical deliverables.
- **Unit System:** Strictly **US Customary Units** (`in.`, `ft`, `lbs`, `kips`, `psi`, `ksi`, `psf`, `plf`, `lb-in.`, `lb-ft`, `kip-in.`, `kip-ft`). Validate units at input and maintain full numerical precision during intermediate calculations.
- **Design Methods (ASD & LRFD):**
  - Support both **Allowable Stress Design (ASD)** and **Load and Resistance Factor Design (LRFD / Strength Design)**.
  - Never mix ASD load combinations with LRFD resistance factors ($\phi$) or LRFD load combinations with ASD safety factors ($\Omega$) in the same check.

---

## RULE 3: GOOGLE DRIVE RAW FILE SYNC, BACKUP & TOKEN OPTIMIZATION
- **Raw File Upload Standard:** Always upload `.csv`, `.md`, `.py`, `.json`, and `.txt` files to Google Drive using `drive:create_file` with:
  - `base64_content="file:///..."`
  - `mime_type="application/octet-stream"`
  - Files must remain raw binary/text files for direct desktop synchronization and must **never** be auto-converted into Google Docs or Google Sheets.
- **Backup & Clean Workspace Discipline (`backup/`):**
  - Before replacing any active file on Google Drive (`state_summary.txt`, `proposed.md`, `rules.md`, `AGENTS.md`, `README.md`, `app_settings.json`, etc.), rename the superseded version with a `_backup` suffix and move it into the `backup/` folder (`168YNvao8onqXfHC-cjcSCWZz0sPnHz7h`).
  - Move all obsolete drafts, duplicate files, or converted GDocs/GSheets into `backup/` so active project folders remain 100% clean.
- **Rolling State Summary & Token Optimization (`state_summary.txt`):**
  - Update `/structural-engineering-kb/state_summary.txt` (and Section `2.1` of `proposed.md`) every 3 turns or upon milestone/work-package completion.
  - Cache all verified Google Drive Folder IDs and File IDs inside `state_summary.txt` and `config/reference_manifest.json` for zero-search lookup, avoiding redundant directory scans.

---

## RULE 4: CSV DATABASE STANDARDS (`@structural-database-csv`)
- **Filename Convention:** `[Code]_[TableNumber].csv` (e.g., `ASCE7-22_Table_12.2-1.csv`, `NDS-2024_Table_12K.csv`, `AISC360-22_Table_J2.5_Welded_Joints.csv`).
- **Encoding:** Strictly `utf-8-sig` (UTF-8 with BOM) so Microsoft Excel renders Greek characters, mathematical symbols, and superscripts/subscripts without corruption.
- **Data Fidelity:**
  - Preserve exact row and column ordering from the source standard.
  - Retain all mathematical symbols, variable notations, and footnote markers (`[a]`, `[1]`, `*`).
  - Include complete verbatim footnotes and design notes at the bottom of the CSV.
- **Authorized Reference Sources:**
  1. User's Google Drive Reference Library `TCUS` (`1WTG1-B0xZ0GozvfigreJvtLxJI6HnIwQ`).
  2. Official **Simpson Strong-Tie** catalogs and product pages (`https://www.strongtie.com/`).
  3. **SkyCiv Software Documentation** (`https://skyciv.com/docs/`).
- **Mandatory 5-Step Verification & Manifest Registration:** Verify (1) Filename, (2) Dimensions/Order, (3) Symbols/Headers, (4) Numerical/OCR Accuracy, and (5) Footnote Completeness before registering the table in `config/reference_manifest.json`.

---

## RULE 5: CALCULATION PROCEDURE STANDARDS (`@structural-procedures`)
- **Mandatory 7-Section Plan Check Structure:** Every calculation procedure (`.md` in `procedures/` and exported `.pdf` reports) must follow this exact 7-section layout:
  1. **Section 1: Design Assumptions, Load Path & Governing Codes** (Complete load path trace for $P, V, M$, in-plane vs. out-of-plane effects).
  2. **Section 2: Load Combinations & Internal Forces at the Critical Section** (ASCE 7 Sec. 2.3 LRFD & Sec. 2.4 ASD, including $0.6D + 0.6W$ and $0.6D + 0.7E$ uplift/overturning).
  3. **Section 3: Primary Member Verification** (Compactness, stability factors $C_L, C_P$, $t_{\text{des}} = 0.93 t_{\text{nom}}$ for HSS, combined interaction).
  4. **Section 4: Sequential Connection / Limit State Checks Along the Load Path** (Must include brittle and local failure modes: NDS App. E group tear-out, prohibition of cross-grain tension in wood ledgers, AISC Ch. K HSS wall plastification/crippling, ACI 318 Ch. 17 & TMS 402 out-of-plane breakout, one-way bond beam shear, and confining `#4` U-bar hairpins per ACI 318 Sec. 17.5.2.1).
  5. **Section 5: Supporting Member / Global Substrate Verification** (Supporting wall, slab edge, rafter back-span, or footing/pier checks).
  6. **Section 6: Mandatory Detailing & Construction Notes** (Material grades, weldability ASTM A706 / AWS D1.4, fastener rules, minimum edge distances).
  7. **Section 7: Summary Calculation & Detailing Checklist Table** (4 columns: `Step`, `Design Verification Item`, `Governing Code Reference`, `Limit State / Acceptance Equation`).
- **Standardized Load-Path Verification Sequence (Mandatory Consistency Across Procedures & `CalcStep` Traces):** Within Section 4 (and across Sections 3–5 and `CalcStep.stage`), every procedure and calculation trace must follow this 4-stage load-path order:
  1. *Stage 1 — Geometry, Detailing & Applicability Limits:* Verify section compactness/slenderness, $t_{des}$, Chapter K limits, hole spacing/edge distances, or weld size limits ($w_{min}, w_{max}$).
  2. *Stage 2 — Primary Force-Transfer Mechanism:* Check the primary load-transferring element (bolt shear/tension/eccentricity, weld throat capacity, HSS face plastification/punching/sidewall checks, or concrete bearing).
  3. *Stage 3 — Connecting Element & Base Metal Limit States:* Check affected plate/angle/base-metal yielding, net rupture, block shear, shear-flexure interaction, or prying action.
  4. *Stage 4 — Supporting Member / Global Substrate & Combined Interaction:* Check supporting member web/HSS wall punching shear, panel zone shear, torsion interaction (Eq. H3-6), or concrete/masonry breakout.
- **Dual LRFD & ASD Parity:** Every `.md` procedure in `procedures/` and every `core/` engine module must support parallel LRFD ($\phi R_n$) and ASD ($R_n / \Omega$) evaluations without mixing load or resistance factors.

---

## RULE 6: EXCEL WORKBOOK & EXPORT STANDARDS (`@structural-excel`)
- **Format Preference:** Always deliver `.xlsx` workbooks (`openpyxl` / `XlsxWriter`), never Google Sheets, to preserve exact mathematical subscript/superscript formatting.
- **Standardized 17-Column Layout (`A` to `Q`):**
  - Font: **Arial, 10pt**, row height `18.0 pt`, explicit `vertAlign="baseline"` on all normal text/symbol runs so sub/superscripts do not shift baseline alignment.
  - Zero borders in calculation body; blue font for user inputs; dropdown validation linked to the `Database` tab via `VLOOKUP`/`INDEX-MATCH`.
  - Root expressions formatted as power superscripts `(a)^(1/2)`; multiplication formatted with `.`.
  - **3-Tab Workbook Architecture:** `Calc_Sheet` (displaying `Equation -> Substitution -> Result -> Limit -> DCR`), `Database` (with resilient multi-header CSV parsing so zero referenced tables are skipped), and automated `Source_Audit`.
- **Two-Stage Delivery Workflow (when generating custom calculation sheets in chat):** Stage 1 presents a Markdown preview of the calculation flow for user confirmation; Stage 2 delivers the verified `.xlsx` file.

---

## RULE 7: BUILDING DEPARTMENT PLAN CHECK RESPONSE STANDARDS (`@structural-plan-check`)
- **Tone & Format:** Concise, objective US structural engineering English (`response ngắn gọn`).
- **Strict No-Numbering Rule:** Never use numbered lists (`1, 2, 3...`) inside plan check response blocks. Use concise prose paragraphs or hyphenated bullets (`-`) with line breaks.
- **Direct Resolution Structure:** Begin every response with `Addressed.` or `Acknowledged and coordinated.`, explicitly state the revised drawing sheet (`Sheet S0.01`, `Detail 4/S5.01`), calculation section, governing code section, and exact engineering resolution.

---

## RULE 8: STANDALONE DESKTOP APP & CONSOLIDATED ARCHITECTURE RULES (`proposed.md` v1.1 & `Consolidated Proposal`)
- **UI Freeze (Non-Negotiable):** The approved PySide6 4-panel workspace (`Panel 1 — INPUTS` left 280–380 px; `Panel 2 — DIAGRAM` top-right; `Panel 3 — CALCULATION SHEET` middle-right with equations and code references integrated inline; `Panel 4 — SUMMARY` bottom-right), header bar (`ASD | LRFD` segmented toggle), collapsible sidebar (232 px expanded / 48 px rail, ~120 ms animation), and 3-column `Add Calculation` dialog are visually frozen. Never add a 5th panel or alter visual layout/styling.
- **Clean Architecture & Dependency Direction:**
  - `gui/` imports only `app/` (`app/controllers/`, `app/services/`, `app/models/`, `app/rendering/`), never `core/`, `storage/`, `cloud/`, or `exporters/`.
  - `core/` contains pure deterministic engineering calculations and depends only on `core/common/` and `core/ports/` (`ReferenceDataPort`); `core/` must never import `gui/` or concrete `app/services/` implementations.
- **Single ModuleRegistry, Structured `CalcStep` Trace & Typed `DiagramSpec`:**
  - `app/registry/` (`ModuleRegistry`, `ModuleSpec`, `FieldSpec`) is the single source of truth for dialog templates, input forms, engine dispatch, maturity gating (`verified`, `preview`, `coming_soon`, `unavailable`), and diagram builders.
  - Calculation engines emit structured `CalculationResult.trace` (`CalcStep`, `Quantity`, `RefSpec`) consumed identically by Panel 3 (offline vendored KaTeX with rich-text fallback), PDF (`ReportLab`), and XLSX (`openpyxl`).
  - Panel 2 draws from a Qt-independent `DiagramSpec`; geometry redraws immediately on input edits while derived forces come strictly from the deterministic engine.
- **Project-Scoped Item Lifecycle, Zero Sample Defaults & Stale Flag:**
  - Required engineering inputs start blank on a new item (`INCOMPLETE` status, empty Calculation Sheet). Never display sample/mockup numbers or hardcoded fallbacks (`c_delta = 0.69`) as live user calculation outputs.
  - `Run Calculation` computes an in-memory result without creating a revision; `Save Revision` writes an immutable SQLite revision with reference SHA-256 hash and code-edition snapshots.
  - Keep the 5 locked statuses (`PASS`, `FAIL`, `REQUIRES REVIEW`, `INCOMPLETE`, `INVALID INPUT`) and track outdated results via a separate `is_stale` flag in SQLite Schema v2 (`PRAGMA user_version = 2`).
