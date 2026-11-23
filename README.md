# ai-workflow-suite

The glue for four Agent Skills repos: one orchestrator (`delivery-lifecycle`) that carries a piece of work from idea to release, the rules all repos share (`CONVENTIONS.md`) and a single installer.

| Repo | Covers | Orchestrator |
|---|---|---|
| [`dev-workflow-skills`](https://github.com/Lolisuki18/dev-workflow-skills) | plan, code, tests, audit, bug, refactor, security, migration, explain, CI/CD | `dev-lifecycle` |
| [`pull-request-skills`](https://github.com/Lolisuki18/pull-request-skills) | commit, PR text, self-review, review, replies, CI triage, conflicts, PR splitting | - |
| [`qa-workflow-skills`](https://github.com/Lolisuki18/qa-workflow-skills) | test plan, matrix, E2E, API, non-functional, regression, defects, report | `qa-lifecycle` |
| [`docs-workflow-skills`](https://github.com/Lolisuki18/docs-workflow-skills) | README, diagrams, API docs, ADR, changelog, runbook, SDLC reports | `docs-lifecycle` |

## The flow

```text
Stage 1 Build        dev-lifecycle           -> plan/ + code + tests
Stage 2 Pull Request pre-pr-self-review, commit-message-writer, pr-description-writer (pr-splitter if large)
Stage 3 QA           qa-lifecycle            -> qa-artifacts/01..05, Go / Conditional Go / No-Go
Stage 4 Docs         docs-lifecycle          -> README, diagrams, API docs, ADRs
Stage 5 Release      changelog-release-notes-writer, runbook-writer, ci-cd-setup
```

`delivery-lifecycle` labels each reply `[Delivery Stage X/5: ...]`, stops for approval between stages and passes requirement IDs (`R1..Rn`) and real results forward in a `delivery-notes.md`. It does not repeat the work of the sub-skills; it only sequences them. Start at any stage when the earlier ones are not needed. What each stage hands to the next is in [`delivery-lifecycle/references/handoff-map.md`](delivery-lifecycle/references/handoff-map.md).

## Install

Clone the four repos and this one next to each other, then:

```powershell
python scripts/install-all.py                      # every repo found next to this one, into ~/.claude/skills
python scripts/install-all.py --agent gemini       # same options as each repo's scripts/install.py
python scripts/install-all.py --dry-run            # preview
python scripts/install-all.py --list               # which repos were found
```

Links (junctions on Windows, symlinks elsewhere); existing skills are never overwritten. Use `--repos-dir <path>` when the repos live elsewhere. Each repo also has its own `scripts/install.py`.

## Rules shared by all repos

See [`CONVENTIONS.md`](CONVENTIONS.md): progress labels, hard stops, gap placeholders (`[Needs input]` / `[Cần bổ sung]`), evidence format, artifact folders, requirement IDs, language, skill file rules and safety defaults.

## Validate

```bash
python scripts/validate.py
```

Runs on this repo's skills only. The other repos have their own validators (`validate.py` or `validate-skills.py`).

## Status

- `delivery-lifecycle` is new and has not been run on a real agent. One eval case exists in `delivery-lifecycle/evals/` (not yet run).
- The four repos' own eval status is in each repo's `evals/README.md`.
- MIT licensed (see `LICENSE`).
