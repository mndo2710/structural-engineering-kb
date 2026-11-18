# AGENTS.md — Global Agent Rules for structural-engineering-kb

This file defines the mandatory rules and conventions that ALL agents (primary and custom subagents) must follow when working in this project.

## Project Identity

- **Product:** Standalone Windows Desktop Structural Engineering Calculation Application.
- **Architecture Baseline:** `proposed.md` (SAD v1.0) — the single authoritative design specification.
- **Progress Tracker:** `state_summary.txt` — the central project progress record.
- **Working Rules:** `rules.md` — locked engineering conventions.

## Mandatory Pre-Work Protocol

Before starting any task, every agent MUST:

1. Read `rules.md` for locked engineering conventions and working rules.
2. Read `proposed.md` (SAD v1.0) for the authoritative architecture specification.
3. Read `state_summary.txt` for current project progress and cached Google Drive IDs.

## Global Engineering Rules

### Language & Units
- **Code & Technical Deliverables:** 100% US Structural Engineering English (all `.csv`, `.md`, `.py`, `.json`, `.xlsx`, `.pdf` files, variable names, class/function identifiers, comments, filenames).
- **User Communication:** Vietnamese (`Tiếng Việt`).
- **Unit System:** Strictly US Customary (`in.`, `ft`, `lbs`, `kips`, `psi`, `ksi`, `psf`, `plf`, `lb-in.`, `lb-ft`, `kip-in.`, `kip-ft`).

### Design Methods
- Support both **ASD** (Allowable Stress Design) and **LRFD** (Load and Resistance Factor Design / Strength Design).
- **NEVER mix** ASD load combinations with LRFD resistance factors (φ) or LRFD load combinations with ASD safety factors (Ω) in the same check.

### Deterministic V1 Runtime
- The V1 application must be **100% deterministic** — no AI APIs, no Gemini integration, no LLM dependencies at runtime.
- Gemini and Antigravity are used exclusively as **development tools**, not as runtime components.

## Knowledge Base Protection

- The existing verified Knowledge Base (**66 CSV tables** in `database/` and **26 Markdown procedures** in `procedures/`) is **locked and protected**.
- **NEVER modify, delete, or reorganize** existing verified CSV or Markdown files without explicit user approval.
- **NEVER invent** engineering data, code provisions, or design assumptions.

## File Protection

The following files are **read-only** for all subagents:
- `rules.md` — Only the primary agent may update upon explicit user instruction.
- `proposed.md` — Only Section 2.1 may be updated by the primary agent in sync with `state_summary.txt`.
- `state_summary.txt` — Only the primary agent (Tech Lead / Project Coordinator) may update.

## Architectural Discipline

- Follow the layered architecture defined in SAD v1.0 Section 3.
- `gui/` communicates only with `app/services/`, never directly with `core/` or `cloud/`.
- `core/` contains all engineering calculations — no equations in GUI code.
- `app/services/` coordinates workflows between layers.
- Knowledge Base (`database/`, `procedures/`) and Project Data (`storage/`) remain separate.

## Collaboration Protocol

- **Stay in your lane:** Each agent works only within its assigned responsibilities.
- **No simultaneous edits:** Agents must not edit the same files concurrently.
- **Report deliverables:** Every agent must report all created and modified files at the end of each task.
- **Test evidence required:** All code changes must include or reference corresponding test evidence.
- **Engineering traceability:** Every calculation must trace to a specific code section and reference file.
- **Escalate, don't guess:** If information is missing or ambiguous, escalate to the Tech Lead (primary agent) instead of making assumptions.

## Agent Team Structure

| Agent | Role | Scope |
|---|---|---|
| **Primary Agent** | Tech Lead / Project Coordinator | Overall orchestration, `state_summary.txt` updates, architecture decisions |
| `kb-curator` | Knowledge Base Curator | `database/`, `procedures/`, `config/reference_manifest.json` |
| `calculation-engine` | Calculation Engine Developer | `core/`, `tests/` (calculation tests) |
| `desktop-app` | Desktop App Developer | `gui/`, `app/`, `exporters/` |
| `cloud-data` | Cloud & Data Engineer | `storage/`, `cloud/`, `config/` |
| `qa-verifier` | QA & Engineering Verifier | Read-only review and testing across all directories |
