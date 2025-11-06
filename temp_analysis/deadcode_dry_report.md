## Dead-code & DRY Analysis Report

Target: repository root (skip `.venv`), analyze only `src/`.

Generated: 2025-11-06

Purpose: provide an actionable, phase-split plan and findings so another AI agent can continue automated remediation, triage, or create CI checks.

---

## Quick summary

- Tools executed (commands shown in PowerShell form):
  - ruff: `ruff check src --exclude ".venv"`
  - vulture: `vulture src --min-confidence 70 --exclude ".venv"`
  - jscpd: `jscpd src --reporters console --threshold 5 --ignore ".venv/**"`

- High level results:
  - ruff: 109 issues found in `src/` (25 auto-fixable with `--fix`). Categories: extraneous f-strings (F541), unused imports/variables (F401/F841), star-import issues (F403/F405), bare except (E722), other style errors. Run `ruff check src --fix --exclude ".venv"` to apply safe fixes.
  - vulture: 2 high-confidence unused items reported (unused imports with ~90% confidence). Vulture is conservative; false positives expected with dynamic usage.
  - jscpd: 9 clone groups (0.41% duplicated lines). Notable clones are cross-file and within-file duplicates in indicator code and AI provider request/response handling.

---

## How this file is structured

- Phase 0: Inputs & constraints for the AI
- Phase 1: Quick auto-fix and re-evaluation (low-risk)
- Phase 2: Dead-code triage (vulture + annotations)
- Phase 3: DRY/duplication refactor plan (jscpd results)
- Phase 4: CI automation and gating
- Phase 5: Verification, tests, and follow-ups

Each phase includes: intent, exact commands (PowerShell), acceptance criteria, and safe-scope actions for an automated agent.

---

## Phase 0 — inputs & constraints (must obey)

- Working directory: repository root `d:\qrak\PythonScripts\DiscordCryptoAnalyzer`
- Analyze only `src/`. Exclude `.venv` and other virtualenvs, build artifacts, and `cache/` if desired.
- Python environment: assume project uses Python 3.11+ and a `.venv` exists. Do NOT modify `.venv` contents.
- Safety: do not apply destructive refactors across many files without test coverage. Prefer single-file automated fixes (lint autofixes) then re-run checks.
- Reporting: write intermediate outputs to `temp_analysis/` for human review.

Notes for the AI agent: when you see star imports (e.g., `from src.indicators.indicators.momentum import *`) prefer replacing with explicit imports or maintain an `__all__` in the imported module to satisfy static analysis.

---

## Phase 1 — Quick auto-fix and re-evaluation (low-risk)

Goal: Apply safe, automated lint fixes and reduce noise before deeper triage.

Commands (PowerShell):

```powershell
Set-Location -LiteralPath "d:\qrak\PythonScripts\DiscordCryptoAnalyzer"
python -m pip install --upgrade pip
pip install ruff
# Run safe fixes (will modify source files; single commit recommended)
ruff check src --fix --exclude ".venv"
# Re-run to confirm remaining issues
ruff check src --exclude ".venv"
```

Acceptance criteria:
- `ruff check src` output shows <= 10 remaining issues or only issues requiring human judgment (e.g., API constants, dynamic imports).
- Create a short report `temp_analysis/ruff_after_fix.txt` with the final `ruff` output.

Actions for an automated agent:
- Run the commands above.
- Save `ruff` before/after outputs to `temp_analysis/ruff_before.txt` and `temp_analysis/ruff_after.txt`.
- Commit the changes as a single branch/commmit (if allowed) with message: `chore: apply ruff --fix automated lint fixes`.

Notes:
- Ruff may fix extraneous `f` prefixes, remove unused imports flagged by pyflakes rules, and format trivial issues. Do not enable `--unsafe-fixes` without human review.

---

## Phase 2 — Dead-code triage (vulture)

Goal: Identify likely-unused functions/classes/variables and produce a triage list with owners and recommended actions.

Commands:

```powershell
Set-Location -LiteralPath "d:\qrak\PythonScripts\DiscordCryptoAnalyzer"
pip install vulture
vulture src --min-confidence 70 --exclude ".venv" > temp_analysis/vulture_report_raw.txt
```

Acceptance criteria:
- A triage file `temp_analysis/vulture_triage.md` that lists each vulture finding with:
  - file path
  - line snippet (3 lines around finding)
  - confidence score (from vulture output)
  - recommended action (delete/whitelist/extract/confirm)

Triage rules for the AI agent:
- If an item is an import used only by string-based reflection, plugin registration, or in __all__ exports, mark it as `whitelist` (do not delete).
- If an item is an obvious test-only helper or orphaned internal function with no references, mark `delete candidate`.
- If uncertain, mark `needs human review` and include context (nearby functions/classes and any related TODO comments).

Suggested vulture whitelist approach (file):
- Create `tools/vulture_whitelist.py` or `temp_analysis/vulture_whitelist.txt` listing names to ignore; vulture supports `--exclude` for files but not direct name whitelisting — create a small script to filter results.

Automation pattern for an AI:
- Parse `temp_analysis/vulture_report_raw.txt`.
- For each finding with confidence >= 80% and clearly unused, create a small patch (separate branch) that removes the unused import/function with a short test-run (if tests exist).

Warnings:
- Vulture can false-positive when code uses `getattr`, `eval`, string-based imports, or frameworks that dynamically load modules. Always prefer whitelisting over blind deletion.

---

## Phase 3 — DRY / duplication refactor plan (jscpd)

Goal: Turn jscpd clone groups into shared helpers or small utility functions to reduce duplicated code.

Key jscpd findings (top groups):
- `src/indicators/indicators/support_resistance/support_resistance_indicators.py`: repeated blocks within same file — extract helper
- `src/platforms/utils/cryptocompare_categories_api.py` <-> `src/rag/management/category_processor.py`: duplicated block (20 lines) — extract to `src/platforms/utils/_category_utils.py` or `src/utils/category_utils.py` and import from both places
- AI provider request/response handling duplicates across `src/platforms/ai_providers/openrouter.py` and `src/platforms/ai_providers/google.py` — centralize common request/formatting logic in a small base helper `src/platforms/ai_providers/_helpers.py`
- Indicator base vs technical indicators duplication — consider small refactor to share core loop or helper functions.

Commands to reproduce jscpd run (PowerShell):

```powershell
Set-Location -LiteralPath "d:\qrak\PythonScripts\DiscordCryptoAnalyzer"
# jscpd installed globally via npm
jscpd src --reporters console --threshold 5 --ignore ".venv/**" > temp_analysis/jscpd_report.txt
```

Refactor pattern for each clone group (automated steps):
1. Create a new helper module path suggested above and implement the extracted function(s) using the narrowest API possible.
2. Replace duplicated blocks in source files with a small call to the helper (one-line change if possible).
3. Run tests or a quick smoke run (if no tests, run a minimal import check: `python -c "import importlib; importlib.import_module('src.module.path')"` for changed modules) to ensure no import-time errors.
4. Commit as a focused change per clone group with message: `refactor: extract <x> helper to remove duplicate code`.

Acceptance criteria:
- Each clone group results in <=1 new helper module and <=3 files changed.
- Duplicated lines removed and jscpd re-run shows those clones eliminated or reduced below threshold.

---

## Phase 4 — CI automation & gating

Goal: Add a GitHub Action to run `ruff`, `vulture` (report-only), and `jscpd` on PRs, blocking changes that introduce new critical issues.

Minimal workflow outline (for `.github/workflows/static_analysis.yml`):

- Jobs:
  - lint: run `ruff check src --exclude .venv` and fail on non-zero exit
  - duplicates: run `jscpd` and fail if duplicates exceed configured threshold (or mark as warning)
  - dead-code-report: run `vulture` and attach `vulture_report_raw.txt` as an artifact (do not fail automatically — false positives require human judgement)

CI steps (PowerShell preserved for local-run parity but Actions will use ubuntu-latest):

```powershell
Set-Location -LiteralPath "d:\qrak\PythonScripts\DiscordCryptoAnalyzer"
ruff check src --exclude ".venv"
jscpd src --reporters console --threshold 5 --ignore ".venv/**"
vulture src --min-confidence 70 --exclude ".venv" > vulture_report_raw.txt
```

Notes:
- Prefer `ruff` as the blocking linter (fast). Keep `vulture` as report-only until whitelist curated.
- Optionally gate `jscpd` as a quality check (fail only when duplicated lines exceed X%).

---

## Phase 5 — Verification, tests, and follow-ups

Goal: Validate changes and detect regressions.

Actions for the AI agent:
- Run `python -m pip install -r requirements.txt` (or use existing venv) and then run any test suite (if present). If no tests, run an import-scan for changed modules:

```powershell
python -c "import pkgutil, importlib, sys; [importlib.import_module(mod.name) for mod in pkgutil.walk_packages(['src'])]"
```

- Generate a follow-up report `temp_analysis/followup_checks.md` listing changed files, lingering issues, and suggested human-review items.

---

## Example remediation plan for a single clone group (doable automatically)

1. Identify the clone files and exact code region (from `temp_analysis/jscpd_report.txt` produced earlier).
2. Create `src/utils/<helper>.py` with a single well-named function containing the cloned logic.
3. Replace duplicate blocks in source files with a small import and call.
4. Run `ruff check src --fix --exclude ".venv"` and then the smoke-import script.
5. Commit as `refactor: extract <helper> to eliminate duplication (jscpd)`.

---

## Raw tool summary (numbers)

- ruff (initial): 109 issues found; 25 auto-fixable.
- vulture: 2 high-confidence unused imports reported.
- jscpd: 9 clones found; 121 duplicated lines (0.41% of repo lines).

---

## Attachments & outputs to produce (place under `temp_analysis/`)

- `ruff_before.txt` — raw ruff output before fixes
- `ruff_after.txt` — raw ruff output after `--fix`
- `vulture_report_raw.txt` — vulture output
- `vulture_triage.md` — a structured triage list (AI should create)
- `jscpd_report.txt` — jscpd output
- `refactor_plan.md` — for each clone group record proposed helper path and changed files

---

## Final notes & guidance for a follow-on AI

- Start with Phase 1: it's low-risk and reduces noise. Save artifacts.
- Use Phase 2 triage to build a safe whitelist for vulture to prevent accidental deletion.
- Refactor duplication in small, atomic commits (one clone group per commit).
- After each automated change, run import-smoke and lints; if tests exist, run them.
- Create CI workflow that fails on `ruff` but uploads vulture reports until whitelist is mature.


---

End of report.
