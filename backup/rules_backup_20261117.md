# MASTER WORKING RULES & ENGINEERING CONVENTIONS (`rules.md`)
**Project:** `structural-engineering-kb` (Standalone US Structural Engineering Calculation Application)  
**Last Updated:** November 14, 2026  
**Status:** Locked & Active (Auto-updated upon explicit user instruction)

---

## RULE 1: AUTHORITATIVE PROJECT DIRECTION & CHANGE CONTROL
- **Primary Architecture Baseline:** `proposed.md` (*Software Architecture Document — SAD v1.0*) is the single authoritative design and roadmap specification for the project.
- **Strict Change Control:**
  - Only **Section `2.1 Existing Project Status`** in `proposed.md` may be updated automatically in parallel with `state_summary.txt` to reflect completed work packages and repository inventory.
  - **No other section of `proposed.md`, nor any existing locked file or architectural decision, may be modified, overwritten, or deleted without explicit permission from the user.**
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
  - Before replacing any active file on Google Drive (`state_summary.txt`, `proposed.md`, `README.md`, `app_settings.json`, etc.), rename the superseded version with a `_backup` suffix and move it into the `backup/` folder (`168YNvao8onqXfHC-cjcSCWZz0sPnHz7h`).
  - Move all obsolete drafts, duplicate files, or converted GDocs/GSheets into `backup/` so active project folders remain 100% clean.
- **Rolling State Summary & Token Optimization (`state_summary.txt`):**
  - Update `/structural-engineering-kb/state_summary.txt` (and Section `2.1` of `proposed.md`) every 3 turns or upon milestone completion.
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

---

## RULE 6: EXCEL WORKBOOK & EXPORT STANDARDS (`@structural-excel`)
- **Format Preference:** Always deliver `.xlsx` workbooks (`openpyxl` / `XlsxWriter`), never Google Sheets, to preserve exact mathematical subscript/superscript formatting.
- **Standardized 17-Column Layout (`A` to `Q`):**
  - Font: **Arial, 10pt**, row height `18.0 pt`, explicit `vertAlign="baseline"` on all normal text/symbol runs so sub/superscripts do not shift baseline alignment.
  - Zero borders in calculation body; blue font for user inputs; dropdown validation linked to the `Database` tab via `VLOOKUP`/`INDEX-MATCH`.
  - Root expressions formatted as power superscripts `(a)^(1/2)`; multiplication formatted with `.`.
  - **3-Tab Workbook Architecture:** `Calc_Sheet` (displaying `Equation -> Substitution -> Result -> Limit -> DCR`), `Database`, and automated `Source_Audit`.
- **Two-Stage Delivery Workflow (when generating custom calculation sheets in chat):** Stage 1 presents a Markdown preview of the calculation flow for user confirmation; Stage 2 delivers the verified `.xlsx` file.

---

## RULE 7: BUILDING DEPARTMENT PLAN CHECK RESPONSE STANDARDS (`@structural-plan-check`)
- **Tone & Format:** Concise, objective US structural engineering English (`response ngắn gọn`).
- **Strict No-Numbering Rule:** Never use numbered lists (`1, 2, 3...`) inside plan check response blocks. Use concise prose paragraphs or hyphenated bullets (`-`) with line breaks.
- **Direct Resolution Structure:** Begin every response with `Addressed.` or `Acknowledged and coordinated.`, explicitly state the revised drawing sheet (`Sheet S0.01`, `Detail 4/S5.01`), calculation section, governing code section, and exact engineering resolution.

---

## RULE 8: STANDALONE DESKTOP APP IMPLEMENTATION RULES (`proposed.md` V1)
- **Deterministic Calculation First:** Python functions in `core/` perform all engineering calculations; Markdown files in `procedures/` are reference documentation only and are never executed as code.
- **No AI in V1 Runtime:** V1 desktop application runs 100% independently offline/cloud-connected without any Gemini or LLM API dependency.
- **Strict Layer Separation:** `gui/` (`PySide6`) communicates only with `app/services/` (`ProjectService`, `CalculationService`, `KnowledgeBaseService`, `ValidationService`, `ReportService`, `CloudSyncService`, `SettingsService`, `HistoryService`), never directly with `core/` equations or Google Drive APIs.
- **Explicit Statuses & Traceability:** Every calculation returns a standardized `CalculationResult` object (`PASS`, `FAIL`, `REQUIRES REVIEW`, `INCOMPLETE`, `INVALID INPUT`) stored with full revision history in SQLite (`storage/projects/structural_app.sqlite3`).
