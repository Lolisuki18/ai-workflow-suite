#!/usr/bin/env python3
"""Keep the shared helper scripts identical in every skill repo.

The canonical copies live in this repo's scripts/ folder. Other repos hold copies so that each one
works on its own after a plain clone.

Usage:
  python scripts/sync-tools.py            # check: list repos whose copies differ (exit 1 if any)
  python scripts/sync-tools.py --apply    # overwrite the differing copies with the canonical ones
  python scripts/sync-tools.py --repos-dir ~/skills

Shared files:
  install.py     every repo
  readme-index.py every repo
  validate.py    every repo that has its own copy (the dev repo uses its own validate-skills.py)
  run-evals.py   every repo except those in KEEP_LOCAL (qa-workflow-skills keeps its own trigger-prompt runner,
                 whose flags --cmd/--detect-regex/--only/--out are documented in that repo; run the shared tool
                 on it with `python scripts/run-evals.py --repo ../qa-workflow-skills`)

Repos are the folders under --repos-dir (default: the parent of this repo), up to two levels deep,
that contain scripts/install.py. Stdlib only.
"""
import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARED = ["install.py", "readme-index.py", "validate.py", "run-evals.py"]
OPTIONAL = {"validate.py"}  # copied only where the repo already has one
KEEP_LOCAL = {"run-evals.py": {"qa-workflow-skills"}}  # repos that keep their own, different file


def find_repos(root: Path):
    found = set()
    for pattern in ("*/scripts/install.py", "*/*/scripts/install.py"):
        for p in root.glob(pattern):
            repo = p.parent.parent.resolve()
            if repo != HERE.parent.resolve():
                found.add(repo)
    return sorted(found)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repos-dir", default=str(HERE.parent.parent))
    ap.add_argument("--apply", action="store_true", help="overwrite differing copies")
    args = ap.parse_args()

    repos = find_repos(Path(args.repos_dir).expanduser().resolve())
    if not repos:
        print("error: no other skill repos found", file=sys.stderr)
        return 1
    differ = 0
    for repo in repos:
        for name in SHARED:
            if repo.name in KEEP_LOCAL.get(name, ()):
                continue
            canon = HERE / name
            copy = repo / "scripts" / name
            if not canon.exists():
                print(f"error: canonical {name} missing", file=sys.stderr)
                return 1
            if not copy.exists():
                if name in OPTIONAL:
                    continue
                state = "missing"
            elif copy.read_bytes() == canon.read_bytes():
                continue
            else:
                state = "differs"
            differ += 1
            if args.apply:
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(canon, copy)
                print(f"updated  {repo.name}/scripts/{name} ({state})")
            else:
                print(f"{state:8} {repo.name}/scripts/{name}")
    if not differ:
        print("all shared scripts match the canonical copies")
        return 0
    return 0 if args.apply else 1


if __name__ == "__main__":
    sys.exit(main())
