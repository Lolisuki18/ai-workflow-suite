# Releasing 1.0.0

Proposed version for all five repos: `1.0.0` (change it in every `.claude-plugin/plugin.json`, in `.claude-plugin/marketplace.json` and in each `CHANGELOG.md` if you pick another). Do the steps in order; nothing here is run for you.

## 1. Checks (all must pass)

Run from `ai-workflow-suite`, with the four other repos checked out next to it:

```bash
python scripts/validate.py
python scripts/readme-index.py --check
python -m unittest discover -s tests
python scripts/sync-tools.py
python scripts/check-links.py
```

In each other repo: `python scripts/validate.py` (dev: `python scripts/validate-skills.py`), `python scripts/readme-index.py --check`, and the unit tests where `tests/` exists (`qa-workflow-skills`, `dev-workflow-skills`). Also run `python -m json.tool .claude-plugin/plugin.json`. Check that `git status` is clean and each `CHANGELOG.md` has a `## [1.0.0]` section.

## 2. Order of pushing

The suite goes first: its `marketplace.json` and its CI check the other repos by GitHub name. Then the four skill repos.

```bash
cd ai-workflow-suite && git push origin main
cd ../dev-workflow-skills && git push origin main
cd ../pull-request-skills && git push origin main
cd ../qa-workflow-skills && git push origin main
cd ../docs-workflow-skills && git push origin main
```

Wait for CI to go green in every repo before tagging.

## 3. Tag each repo

```bash
git tag -a v1.0.0 -m "1.0.0"
git push origin v1.0.0
```

## 4. GitHub releases

Use the `## [1.0.0]` section of that repo's `CHANGELOG.md` as the notes (copy it to a file first):

```bash
gh release create v1.0.0 --title "1.0.0" --notes-file release-notes.md
```

## 5. Smoke test after release

```bash
claude plugin validate .
python scripts/install-all.py --profile minimal --dry-run
python scripts/install-all.py --profile minimal
claude plugin marketplace add Lolisuki18/ai-workflow-suite
claude plugin install qa-workflow-skills@lolisuki18-skills
```

`claude plugin validate .` runs once per repo root (the manifests were never validated before this step) and also in the suite for `marketplace.json`. Fix any warning before announcing. Then, in a fresh session of a scratch project, try five prompts:

1. "Build me a small CLI that tracks tasks" (`dev-lifecycle` should start Phase 1 and stop for approval).
2. "Write my PR description" (`pr-description-writer`).
3. "Review this diff" with a small diff (`pr-review-writer`).
4. "Write a test plan for this app" (`qa-lifecycle` or `qa-test-plan-writer`).
5. "Write an ADR for the storage choice" (`adr-writer`, if the docs repo is installed).

Each reply should carry the skill's step label and stop where the skill says it does. If a prompt does not trigger the skill, open an issue before the next release.
