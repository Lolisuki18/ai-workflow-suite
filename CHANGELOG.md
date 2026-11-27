# Changelog

Format: newest first. Skills are prompts, so "breaking" means a change in behavior an agent will notice (labels, hard stops, script flags).

## Unreleased (0.2.0)

### Added
- `delivery-lifecycle/evals/trigger-prompts.md` with positive and negative trigger prompts, including the full idea-to-ship request.
- `delivery-lifecycle` orchestrator (build, pull request, QA, docs, release) with a hand-off map and one eval case.
- `CONVENTIONS.md` shared by the four skill repos.
- `scripts/install-all.py` (`--repos`, `--profile`, `--only`) and `scripts/sync-tools.py` that keeps `install.py`, `readme-index.py` and `validate.py` identical in every repo.
- `.claude-plugin/marketplace.json` listing the five plugins (not yet checked with `claude plugin validate`).
- `scripts/readme-index.py`, `scripts/validate.py`, `scripts/install.py`, MIT `LICENSE`, CI workflow.
- `scripts/check-links.py` (cross-repo skill names, relative links, repository URLs) and a CI job that checks the five repos out side by side.
- `install-all.py --repos`, `--profile` (`minimal`, `dev`, `qa`, `full`) and `--only`; `install.py --only` / `--exclude`.
- Shared `readme-index.py` generates the skill index in every README.

### Changed
- `delivery-lifecycle` description covers idea-to-shipped requests (build, tests, docs, release) and excludes single phases; gate 3 → 4 refers to the small-N rule of `qa-summary-reporter`.
- `CONVENTIONS.md` section 4: re-run before claiming, record baseline failures, keep line endings.
- `delivery-lifecycle`: module-form artifact paths, `02b`/`03c` in QA round list, stage-end merged approvals, two meanings of "provisional", fix rounds sized by diff, commit and browser-regression-test ownership; `CONVENTIONS.md` section 10 fix-round sizing.
- `CONVENTIONS.md`: one module-namespacing form (section 5), one small-scope size rule (section 10), new section 11 "Sub-skills inside a lifecycle", placeholder translation, rule that skills do not cite `CONVENTIONS.md` as shipped. `delivery-lifecycle` uses the same module form, accepts a provisional Conditional Go for Not Run cases that need a person or device, and defers path-only hard stops to the approved file list.
- `delivery-lifecycle`: bug-fix loop, commit ownership, base branch and build under test as required hand-off fields, QA round rule, defect closing by the user, merged kickoff answers and approvals, Stage 4 route mapping; the `delivery-notes.md` template gains build, base branch, verdict and gate source, accepted risks, PR text, not-run list, QA round and version fields, a `Done with conditions` status and a last Decisions block.
- `CONVENTIONS.md`: evidence rules for `file:line` and placeholders vs real results; new section 10 "Small scope".
- All skill descriptions are English only and about 35% shorter (one sentence of purpose, 4 trigger phrases, `Do NOT use for ...`); about 8,500 to 5,400 tokens for 44 skills. The shared validator now requires English and at most 650 characters.
- `install-all.py` installs the `minimal` profile by default; use `--profile full` for everything.
