# Changelog

Format: newest first. Skills are prompts, so "breaking" means a change in behavior an agent will notice (labels, hard stops, script flags).

## Unreleased (0.2.0)

### Added
- `delivery-lifecycle` orchestrator (build, pull request, QA, docs, release) with a hand-off map and one eval case.
- `CONVENTIONS.md` shared by the four skill repos.
- `scripts/install-all.py` (`--repos`, `--profile`, `--only`) and `scripts/sync-tools.py` that keeps `install.py`, `readme-index.py` and `validate.py` identical in every repo.
- `.claude-plugin/marketplace.json` listing the five plugins (not yet checked with `claude plugin validate`).
- `scripts/readme-index.py`, `scripts/validate.py`, `scripts/install.py`, MIT `LICENSE`, CI workflow.
- `scripts/check-links.py` (cross-repo skill names, relative links, repository URLs) and a CI job that checks the five repos out side by side.
- `install-all.py --repos`, `--profile` (`minimal`, `dev`, `qa`, `full`) and `--only`; `install.py --only` / `--exclude`.
- Shared `readme-index.py` generates the skill index in every README.

### Changed
- All skill descriptions are English only and about 35% shorter (one sentence of purpose, 4 trigger phrases, `Do NOT use for ...`); about 8,500 to 5,400 tokens for 44 skills. The shared validator now requires English and at most 650 characters.
- `install-all.py` installs the `minimal` profile by default; use `--profile full` for everything.
