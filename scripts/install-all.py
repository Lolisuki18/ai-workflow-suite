#!/usr/bin/env python3
"""Install the skills of every skill repo found next to this one with a single command.

Usage:
  python scripts/install-all.py [install.py options]          # installs the `minimal` profile; e.g. --agent gemini --scope project --copy
  python scripts/install-all.py --profile full                 # every skill (about 5,000 tokens of descriptions in each conversation)
  python scripts/install-all.py --repos-dir ~/skills --dry-run
  python scripts/install-all.py --list                         # show the repos that would be used
  python scripts/install-all.py --repos dev,pr                 # only these repos: dev, pr, qa, docs, suite
  python scripts/install-all.py --profile minimal              # a small starter set instead of everything
  python scripts/install-all.py --only qa-lifecycle,bug-investigator

A skill repo is any folder under --repos-dir (default: the parent of this repo), up to two levels
deep, that contains scripts/install.py. Every option except --repos-dir and --list is forwarded to
each repo's own install.py (see `python scripts/install.py --help`), so presets, --dry-run, --copy,
--uninstall and --force behave the same everywhere. Stdlib only.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# short key -> text that must appear in the repo folder name
REPO_KEYS = {"dev": "dev-workflow", "pr": "pull-request", "qa": "qa-workflow", "docs": "docs-workflow", "suite": "ai-workflow-suite"}
OLD_PR_NAME = "skill-code-review"  # the pull-request repo may still be cloned under its old name

# starter profiles: skill names; `full` = everything
PROFILES = {
    "minimal": ["dev-lifecycle", "feature-plan-writer", "test-case-writer", "bug-investigator",
                "pre-pr-self-review", "pr-description-writer", "pr-review-writer", "commit-message-writer"],
    "dev": ["dev-lifecycle", "feature-plan-writer", "test-case-writer", "codebase-auditor", "bug-investigator",
            "refactor-planner", "security-reviewer", "migration-writer", "code-explainer", "ci-cd-setup",
            "performance-profiler"],
    "qa": ["qa-lifecycle", "qa-test-plan-writer", "qa-test-matrix-writer", "qa-e2e-writer", "qa-defect-writer",
           "qa-summary-reporter", "qa-api-tester", "qa-nonfunctional-writer", "qa-regression-planner",
           "qa-accessibility-auditor"],
    "full": None,
}


def find_repos(root: Path):
    found = set()
    for pattern in ("*/scripts/install.py", "*/*/scripts/install.py"):
        for p in root.glob(pattern):
            repo = p.parent.parent
            if any(part.startswith(".") for part in repo.relative_to(root).parts):
                continue
            if any((repo / d / "SKILL.md").exists() for d in (x.name for x in repo.iterdir() if x.is_dir())):
                found.add(repo.resolve())
    return sorted(found)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                 allow_abbrev=False)
    ap.add_argument("--repos-dir", default=str(HERE.parent), help="folder holding the skill repos")
    ap.add_argument("--list", action="store_true", help="list the repos found and exit")
    ap.add_argument("--repos", help="comma-separated repo keys to use: dev, pr, qa, docs, suite")
    ap.add_argument("--profile", choices=sorted(PROFILES), help="install a predefined set of skills")
    args, forward = ap.parse_known_args()

    repos = find_repos(Path(args.repos_dir).expanduser().resolve())
    if args.repos:
        keys = [k.strip() for k in args.repos.split(",") if k.strip()]
        bad = [k for k in keys if k not in REPO_KEYS]
        if bad:
            print(f"error: unknown repo key(s) {bad}; use {sorted(REPO_KEYS)}", file=sys.stderr)
            return 1
        def match(repo):
            n = repo.name
            return any(REPO_KEYS[k] in n or (k == "pr" and OLD_PR_NAME in n) for k in keys)
        repos = [r for r in repos if match(r)]
    if not repos:
        print(f"error: no skill repos found under {args.repos_dir}", file=sys.stderr)
        return 1
    has_selection = "--only" in forward or any(a.startswith("--only=") for a in forward)
    profile = args.profile
    if not profile and not has_selection and not args.list:
        profile = "minimal"
        print("No --profile or --only given: installing the `minimal` profile. "
              "Every installed skill adds its description to each conversation; use --profile dev|qa|full for more.")
    if profile and PROFILES[profile] is not None and not has_selection:
        forward += ["--only", ",".join(PROFILES[profile])]
    if args.list:
        for r in repos:
            print(r)
        return 0

    rc = 0
    for repo in repos:
        print(f"\n== {repo.name}")
        r = subprocess.run([sys.executable, str(repo / "scripts" / "install.py"), *forward])
        rc = rc or r.returncode
    return rc


if __name__ == "__main__":
    sys.exit(main())
