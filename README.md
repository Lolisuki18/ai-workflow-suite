# ai-workflow-suite

The glue for four Agent Skills repos: one orchestrator (`delivery-lifecycle`) that carries a piece of work from idea to release, the rules all repos share (`CONVENTIONS.md`) and a single installer.

| Repo | Covers | Orchestrator |
|---|---|---|
| [`dev-workflow-skills`](https://github.com/Lolisuki18/dev-workflow-skills) | plan, code, tests, audit, bug, refactor, security, migration, explain, CI/CD | `dev-lifecycle` |
| [`pull-request-skills`](https://github.com/Lolisuki18/pull-request-skills) | commit, PR text, self-review, review, replies, CI triage, conflicts, PR splitting | - |
| [`qa-workflow-skills`](https://github.com/Lolisuki18/qa-workflow-skills) | test plan, matrix, E2E, API, non-functional, regression, defects, report | `qa-lifecycle` |
| [`docs-workflow-skills`](https://github.com/Lolisuki18/docs-workflow-skills) | README, diagrams, API docs, ADR, changelog, runbook, SDLC reports | `docs-lifecycle` |

## Skill index

<!-- skills:start -->
**1 skills.** This index is generated from each `SKILL.md`; run `python scripts/readme-index.py` to refresh it.

| Skill | What it does |
|---|---|
| [`delivery-lifecycle`](delivery-lifecycle/SKILL.md) | Orchestrates a whole delivery across the four skill sets in 5 stages — Build (dev-lifecycle), Pull Request (pre-pr-self-review, commit and PR text), QA (qa-lifecycle)... |
<!-- skills:end -->

## The flow

```text
Stage 1 Build        dev-lifecycle           -> plan/ + code + tests
Stage 2 Pull Request pre-pr-self-review, commit-message-writer, pr-description-writer (pr-splitter if large)
Stage 3 QA           qa-lifecycle            -> qa-artifacts/01..05, Go / Conditional Go / No-Go
Stage 4 Docs         docs-lifecycle          -> README, diagrams, API docs, ADRs
Stage 5 Release      changelog-release-notes-writer, runbook-writer, ci-cd-setup
```

`delivery-lifecycle` labels each reply `[Delivery Stage X/5: ...]`, stops for approval between stages and passes requirement IDs (`R1..Rn`) and real results forward in a `delivery-notes.md`. It does not repeat the work of the sub-skills; it only sequences them. Start at any stage when the earlier ones are not needed. What each stage hands to the next is in [`delivery-lifecycle/references/handoff-map.md`](delivery-lifecycle/references/handoff-map.md).

## Install as Claude Code plugins

Each repo has a `.claude-plugin/plugin.json` and this repo has a `.claude-plugin/marketplace.json` listing all five. After the repos are pushed:

```powershell
claude plugin marketplace add Lolisuki18/ai-workflow-suite
claude plugin install dev-workflow-skills@lolisuki18-skills
claude plugin install qa-workflow-skills@lolisuki18-skills
```

Plugin skills are namespaced by the plugin name (for example `/dev-workflow-skills:dev-lifecycle`). The manifests follow the current plugin documentation but have **not** been checked with `claude plugin validate` yet; run it on each repo before publishing. The plugin points `skills` at the repo root, and the docs do not say whether the other root folders (`scripts/`, `docs/`, `evals/`) are ignored by that scan: check this with the validator.

## Install with scripts

Clone the four repos and this one next to each other, then:

```powershell
python scripts/install-all.py                      # every repo found next to this one, into ~/.claude/skills
python scripts/install-all.py --agent gemini       # same options as each repo's scripts/install.py
python scripts/install-all.py --dry-run            # preview
python scripts/install-all.py --list               # which repos were found
python scripts/install-all.py --repos dev,pr         # only some repos: dev, pr, qa, docs, suite
python scripts/install-all.py --profile minimal      # a small starter set (also: dev, qa, full)
python scripts/install-all.py --only qa-lifecycle,bug-investigator
```

Links (junctions on Windows, symlinks elsewhere); existing skills are never overwritten. Use `--repos-dir <path>` when the repos live elsewhere. Each repo also has its own `scripts/install.py`.

## Rules shared by all repos

See [`CONVENTIONS.md`](CONVENTIONS.md): progress labels, hard stops, gap placeholders (`[Needs input]` / `[Cần bổ sung]`), evidence format, artifact folders, requirement IDs, language, skill file rules and safety defaults.

## Keeping the repos in step

| Script | What it does |
|---|---|
| `scripts/sync-tools.py` | Checks (or with `--apply` fixes) that `install.py`, `readme-index.py` and `validate.py` in every repo equal the canonical copies here. Each repo's CI also diffs them against this repo on GitHub. |
| `scripts/readme-index.py` | Regenerates the skill index of a repo's README from the `SKILL.md` frontmatter; `--check` fails when it is out of date. |
| `scripts/check-links.py` | Finds `use <skill>` references to skills that do not exist, broken relative links and wrong repository URLs across the five repos (runs in this repo's CI by checking all five out). |

Edit the shared scripts here only, then run `python scripts/sync-tools.py --apply`.

## Validate

```bash
python scripts/validate.py
```

Runs on this repo's skills only. The other repos have their own validators (`validate.py` or `validate-skills.py`).

## Status

- `delivery-lifecycle`: one eval case in `delivery-lifecycle/evals/`, run once on 2026-11-23 by a Claude subagent that was given only the SKILL.md. It passed all 7 graders (stage anchor, asked which skill sets are installed, carried R1..R3, stopped for approval, facts-only handoff note). The first run exposed an inconsistent fixture (a stub marked Done), which was fixed and re-run. It was not chosen by an agent from its description, so triggering is untested.
- The four repos' own eval status is in each repo's `evals/README.md`.
- MIT licensed (see `LICENSE`).
