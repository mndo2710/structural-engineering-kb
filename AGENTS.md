# AGENTS.md — Global Agent Rules for structural-engineering-kb

This file defines the mandatory rules, architectural contracts, and workflow conventions that ALL agents (Primary Agent and custom subagents) must follow when working in this project.

## Project Identity

- **Product:** Standalone Windows Desktop Structural Engineering Calculation Application.
- **Authoritative Architecture Baseline:** `proposed.md` (SAD v1.1) and `proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md` (`1KlEES_QYXMFnwYAKwqdathM7LalXiBq8`).
- **Progress Tracker:** `state_summary.txt` — the central project progress and Google Drive ID registry.
- **Working Rules:** `rules.md` — locked engineering and architectural conventions.

## Mandatory Pre-Work Protocol

Before starting any task or work package, every agent MUST:

1. Read `rules.md` for locked engineering conventions and working rules.
2. Read `proposed.md` (SAD v1.1) and `proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md` for the authoritative architecture, work packages (`Phase 0 / WP-0` through `Phase 10 / Day 20`), and acceptance gates.
3. Read `state_summary.txt` for current project progress and cached Google Drive File/Folder IDs.

## Global Engineering & UI Freeze Rules

### 1. Frozen PySide6 4-Panel UI (Non-Negotiable)
- **Visual Freeze:** Preserve the approved header bar (`ASD | LRFD` segmented switch), collapsible sidebar (232 px expanded with user groups and drag-to-reorder / 48 px icon rail, ~120 ms animation), 3-column `Add Calculation` dialog, and 4-panel workspace layout (`Panel 1 — INPUTS` left 280–380 px; `Panel 2 — DIAGRAM` top-right; `Panel 3 — CALCULATION SHEET` middle-right with code-basis banner, `Equation -> Substitution -> Result`, and right-aligned code references integrated inline; `Panel 4 — SUMMARY` bottom-right).
- **Prohibitions:** Never add a 5th panel, never create a separate reference panel, never alter visual styling/proportions, and never place engineering equations in GUI, diagram, or exporter code.

### 2. Language, Units & Design Methods
- **Code & Technical Deliverables:** 100% US Structural Engineering English across all `.csv`, `.md`, `.py`, `.json`, `.xlsx`, and `.pdf` files, variable names, class/function identifiers, comments, and filenames.
- **User Communication:** Vietnamese (`Tiếng Việt`).
- **Unit System:** Strictly US Customary (`in.`, `ft`, `lbs`, `kips`, `psi`, `ksi`, `psf`, `plf`, `lb-in.`, `lb-ft`, `kip-in.`, `kip-ft`).
- **ASD & LRFD Separation:** Support both **ASD** and **LRFD**. Never mix ASD load combinations with LRFD resistance factors ($\phi$) or LRFD load combinations with ASD safety factors ($\Omega$) in the same check.

### 3. Input Policy, Zero Sample Defaults & Item Lifecycle
- **Blank Start:** Required engineering inputs on a newly created blank calculation item must start blank, yielding status `INCOMPLETE` and an empty Calculation Sheet. Never display mockup sample numbers or hardcoded fallbacks (`c_delta = 0.69`) as live calculation outputs.
- **Run vs. Save Revision:** `Run Calculation` computes an in-memory result and updates `last_dcr` without creating a revision. `Save Revision` explicitly creates an immutable SQLite revision storing inputs, result, trace, code edition, software version, and reference SHA-256 snapshot.
- **Stale Flag:** Keep the 5 locked calculation statuses (`PASS`, `FAIL`, `REQUIRES REVIEW`, `INCOMPLETE`, `INVALID INPUT`). Represent edited/outdated state via a separate `is_stale` flag (`last_input_hash != current_hash`).

### 4. Clean Architecture Dependency Direction
- `gui/` imports **only** application-facing modules (`app/controllers/`, `app/services/`, `app/models/`, `app/rendering/`). `gui/` must **never** import `core/`, `storage/`, `cloud/`, or `exporters/`.
- `core/` contains pure deterministic engineering calculations and depends **only** on `core/common/` and `core/ports/` (`ReferenceDataPort`). `core/` must **never** import `PySide6`, `gui/`, or concrete `app/services/` implementations.
- `app/registry/` (`ModuleRegistry`, `ModuleSpec`, `FieldSpec`) is the single source of truth for module catalog, input schemas, dispatch, maturity gating (`verified`, `preview`, `coming_soon`, `unavailable`), and diagram builders.
- `CalculationResult.trace` (`CalcStep`, `Quantity`, `RefSpec`) is the single structured calculation trace shared by Panel 3 (offline vendored KaTeX + rich-text fallback), PDF (`ReportLab`), and XLSX (`openpyxl`), following the **Rule 5 4-Stage Load-Path Order** (`Stage 1: Geometry/Limits -> Stage 2: Primary Force Transfer -> Stage 3: Connecting Element/Base Metal -> Stage 4: Supporting Member/Global Interaction`).

### 5. Deterministic V1 Runtime
- The V1 application is **100% deterministic and offline-capable** — zero AI APIs, zero Gemini/LLM runtime calls, and zero external CDN requests (all KaTeX and SVG assets vendored locally in `gui/assets/`).

## Knowledge Base & Governance File Protection

- The verified Knowledge Base (**66 CSV tables** in `database/` and **26 Markdown procedures** in `procedures/` audited via `config/reference_manifest.json`) is **locked and protected**. Never modify, delete, or reorganize existing verified CSV or Markdown files without explicit user approval and the 5-step verification protocol.
- The following governance files are **read-only** for all subagents:
  - `rules.md` — Only the Primary Agent may update upon explicit user instruction.
  - `proposed.md` and `proposal/Structural_Calculation_App_Consolidated_Architecture_Proposal.md` — Locked architectural specifications; only Section 2.1 of `proposed.md` may be updated by the Primary Agent in sync with `state_summary.txt`.
  - `state_summary.txt` — Owned and updated by the Primary Agent (Tech Lead / Project Coordinator).

## Collaboration & Work-Package Protocol

- **Stay in your lane:** Each agent works strictly within its assigned directory and work-package scope (`Phase 0 / WP-0` through `Phase 10 / Day 20`).
- **No simultaneous edits:** Agents must not edit the same files concurrently.
- **Mandatory Work-Package Reporting:** At the end of every work package, report exact files added/modified, owner, test commands and results, benchmark comparisons, UI screenshot-regression outcome, migration evidence, and any deviations.
- **Escalate, don't guess:** Stop and escalate to the Primary Agent whenever an engineering assumption, code reference, protected KB file, or locked governance file requires clarification or approval.

## Agent Team Structure

| Agent | Role | Owned Scope & Work Packages |
|---|---|---|
| **Primary Agent** | Tech Lead / Project Coordinator | Overall orchestration, `WP-0` baseline audit, `state_summary.txt` & `proposed.md` Sec. 2.1 updates, Day 20 UAT & V1.0 release sign-off |
| `kb-curator` | Knowledge Base Curator | `database/`, `procedures/`, `config/reference_manifest.json`, L2 reference integrity & HUS210-2 source verification |
| `calculation-engine` | Calculation Engine Developer | `core/` (`common/`, `ports/`, `asce7/`, `nds/`, `aisc360/`, `aci318/`, `tms402/`), `WP-2` (`CalcStep` + math parser), `WP-9` (C&C/Wood trace backfill), `WP-11` (Day 15 Steel & Day 16 Concrete/CMU engines), engine benchmark/regression tests |
| `desktop-app` | Desktop App Developer | `gui/`, `app/` (`models/`, `registry/`, `controllers/`, `services/`, `rendering/`), `exporters/`, `WP-0b`, `WP-1b`, `WP-3`..`WP-8`, `WP-10` (Day 18 multi-item PDF/XLSX reports), PyInstaller packaging |
| `cloud-data` | Cloud & Data Engineer | `storage/` (`repositories/`, `migrations/`, `backups/`), `cloud/`, `config/`, `WP-1a` (SQLite Schema v2 migration), `WP-1b` storage support, `Day 17` Google Drive raw KB sync & offline cache |
| `qa-verifier` | QA & Engineering Verifier | Read-only audit (`WP-0`), continuous WP verification (`WP-12`), L1–L5 + GUI screenshot + Offline + Clean-Machine Packaging verification (`Day 19`), V1.0 release gate checklist |
