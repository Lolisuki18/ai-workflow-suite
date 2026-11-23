# Handoff map

What each stage must give the next one. If an item is missing, mark it `[Needs input]` in the handoff note rather than guessing.

## Stage 1 → 2 (Build → Pull Request)

| Item | Where it comes from |
|---|---|
| Requirements list R1..Rn with IDs | `plan/NNN-*.md` |
| Plan status `Done` and the resume point | plan header |
| Changed files and base branch | `git diff <base>...HEAD` |
| Real test and check results | `test-case-writer` report, CI or local run output |
| Known gaps and skipped checks (`skipped by user`) | plan risks section |

## Stage 2 → 3 (Pull Request → QA)

| Item | Where it comes from |
|---|---|
| Self-review verdict and any accepted risks | `pre-pr-self-review` report |
| PR link or branch / tag under test | the user |
| Requirements and acceptance criteria | plan R1..Rn, ticket |
| Test environment and data notes | plan, `.env.example`, user |

## Stage 3 → 4 (QA → Docs)

| Item | Where it comes from |
|---|---|
| Verdict (Go / Conditional Go / No-Go) and residual risks | `qa-artifacts/05-summary-report.md` |
| Real execution numbers (for Report 5 style packaging) | `qa-artifacts/03-execution-notes.md` |
| Open defects and known limitations | `qa-artifacts/04-defects.md` |
| Behaviors confirmed by tests (for user guide and API docs) | test matrix, API track notes |

## Stage 4 → 5 (Docs → Release)

| Item | Where it comes from |
|---|---|
| Docs verified against code | `docs-sync-auditor` report or Phase 4 checklist |
| Known limitations to mention in release notes | QA residual risks |
| Deploy and rollback facts | `ci-cd-setup` output, infra files |
| Version and tag range | git tags, the user |

## Handoff note template (`delivery-notes.md`)

```markdown
# Delivery notes - <project / feature>

## Stage 1 - Build - <date> - status: Done | In progress | Skipped (reason)
Artifacts: plan/001-...md, <PR branch>
Real results: <commands and outcomes>
Open items: ...

## Stage 2 - Pull Request - ...
## Stage 3 - QA - ...
## Stage 4 - Docs - ...
## Stage 5 - Release - ...

## Decisions
| Date | Decision | By |
```
