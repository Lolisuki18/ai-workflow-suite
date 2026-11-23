#!/usr/bin/env python3
"""Install the skills of every skill repo found next to this one with a single command.

Usage:
  python scripts/install-all.py [install.py options]          # e.g. --agent gemini --scope project --copy
  python scripts/install-all.py --repos-dir ~/skills --dry-run
  python scripts/install-all.py --list                         # show the repos that would be used

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
    args, forward = ap.parse_known_args()

    repos = find_repos(Path(args.repos_dir).expanduser().resolve())
    if not repos:
        print(f"error: no skill repos found under {args.repos_dir}", file=sys.stderr)
        return 1
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
