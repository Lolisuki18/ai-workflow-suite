#!/usr/bin/env python3
"""Check references that cross skill repos: skill names, relative links and repository URLs.

Usage:
  python scripts/check-links.py                       # repos found next to this one
  python scripts/check-links.py --dirs a b c          # explicit repo folders (CI checks them out side by side)

Checks (code fences and evals/ folders are ignored):
  0. No trigger phrase (a quoted phrase before "Do NOT use" in a description) is claimed by two different
     skills, in any repo, so the agent never has to guess between them.
  1. "use <skill>" references in skill descriptions and "(use a or b)" lists name a skill that exists
     in at least one of the repos.
  2. Relative Markdown links [text](path) point to a file or folder that exists.
  3. https://github.com/Lolisuki18/<repo> URLs name one of the five known repos; the old name
     `skill-code-review` is reported as an error.
Exit code 1 when any check fails. Stdlib only.
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
KNOWN_REPOS = {"dev-workflow-skills", "pull-request-skills", "qa-workflow-skills", "docs-workflow-skills",
               "ai-workflow-suite"}
OLD_NAMES = {"skill-code-review"}
SKILL_REF = re.compile(r"\buse ([a-z][a-z0-9]*(?:-[a-z0-9]+)+)")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
GH = re.compile(r"github\.com/Lolisuki18/([A-Za-z0-9_.-]+)")
FENCE = re.compile(r"```.*?```", re.S)
TRIGGER = re.compile(r"""['"]([^'"]{6,70})['"]""")


def discover(root: Path):
    found = set()
    for pattern in ("*/scripts/install.py", "*/*/scripts/install.py"):
        for p in root.glob(pattern):
            found.add(p.parent.parent.resolve())
    return sorted(found)


def md_files(repo: Path):
    for p in repo.rglob("*.md"):
        rel = p.relative_to(repo).parts
        if any(part in ("evals", "node_modules", ".git") for part in rel):
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dirs", nargs="*", help="repo folders to check (default: repos next to this one)")
    args = ap.parse_args()

    repos = [Path(d).resolve() for d in args.dirs] if args.dirs else discover(HERE.parent)
    if not repos:
        print("error: no repos found", file=sys.stderr)
        return 1
    skills = {d.name for r in repos for d in r.iterdir() if d.is_dir() and (d / "SKILL.md").exists()}
    errors = []
    triggers = {}
    for repo in repos:
        for d in sorted(p for p in repo.iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
            text = (d / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"^description:\s*(.+)$", text, re.M)
            if not m:
                continue
            desc = m.group(1).strip()
            if len(desc) > 1 and desc[0] == desc[-1] and desc[0] in "\"'":
                desc = desc[1:-1]
            for phrase in set(TRIGGER.findall(desc.split("Do NOT use")[0])):
                triggers.setdefault(phrase.lower().strip(), set()).add(d.name)
    for phrase, owners in sorted(triggers.items()):
        if len(owners) > 1:
            errors.append(f"trigger phrase {phrase!r} is claimed by {sorted(owners)}")
    for repo in repos:
        for f in md_files(repo):
            rel = f.relative_to(repo).as_posix()
            text = FENCE.sub("", f.read_text(encoding="utf-8", errors="ignore"))
            if f.name == "SKILL.md" and f.parent.parent == repo:
                head = text.split("\n---", 1)[0]
                for name in SKILL_REF.findall(head):
                    if name not in skills:
                        errors.append(f"{repo.name}/{rel}: description says 'use {name}' but no such skill exists")
            for target in LINK.findall(text):
                if re.match(r"^(https?:|mailto:|#)", target):
                    continue
                path = target.split("#", 1)[0]
                if not path or "<" in path or "*" in path:
                    continue
                if not (f.parent / path).exists():
                    errors.append(f"{repo.name}/{rel}: broken link ({target})")
            for repo_name in GH.findall(text):
                repo_name = repo_name.removesuffix(".git").rstrip(".")
                if repo_name in OLD_NAMES:
                    errors.append(f"{repo.name}/{rel}: old repository name '{repo_name}'")
                elif repo_name not in KNOWN_REPOS:
                    errors.append(f"{repo.name}/{rel}: unknown repository '{repo_name}'")
    for e in errors:
        print("FAIL", e)
    print(f"{len(repos)} repos, {len(skills)} skills checked, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
