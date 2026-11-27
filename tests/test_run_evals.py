"""Tests for scripts/run-evals.py (stdlib unittest, mock backend, temp dirs; no model is called).

Run from the repo root:  python -m unittest discover -s tests
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run-evals.py"
spec = importlib.util.spec_from_file_location("run_evals", str(SCRIPT))
RE = importlib.util.module_from_spec(spec)
sys.modules["run_evals"] = RE
spec.loader.exec_module(RE)


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_skill(repo, name):
    write(Path(repo) / name / "SKILL.md", "---\nname: %s\ndescription: Does things. Do NOT use for x.\n---\nbody\n" % name)


def make_case_dir(repo, skill, name, prompt_md, graders, scaffold=None, files=None):
    d = Path(repo) / skill / "evals" / name
    write(d / "case.yaml", 'schema_version: "1.1"\nname: %s\nexpected_outcome: |\n  something\n%s' % (
        name, "context:\n  scaffold_script: place-files.sh\n" if scaffold else ""))
    write(d / "prompt.md", prompt_md)
    for i, g in enumerate(graders, 1):
        write(d / "graders" / ("%02d-g.md" % i), g)
    if scaffold:
        write(d / "place-files.sh", scaffold)
    for rel, c in (files or {}).items():
        write(d / "files" / rel, c)
    return d


LLM = "---\ntype: llm\nfocus: trace\nweight: 1\n---\n\n%s\n"


class YamlTests(unittest.TestCase):
    def test_subset(self):
        y = RE.parse_yaml('a: 1\nb: "x y"\nc: [p, "q r"]\nd: |\n  l1\n  l2\ne:\n  - one\n  - two\nf:\n  g: h\n')
        self.assertEqual(y["a"], 1)
        self.assertEqual(y["b"], "x y")
        self.assertEqual(y["c"], ["p", "q r"])
        self.assertEqual(y["d"], "l1\nl2")
        self.assertEqual(y["e"], ["one", "two"])
        self.assertEqual(y["f"], {"g": "h"})

    def test_frontmatter_turns_block_list(self):
        meta, body = RE.split_frontmatter("---\ntags: [a]\nturns:\n  - first msg\n  - \"ok, go\"\n---\nbody\n")
        self.assertEqual(meta["turns"], ["first msg", "ok, go"])
        self.assertEqual(body.strip(), "body")


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.repo = Path(self._td.name) / "repo"
        self.repo.mkdir()

    def tearDown(self):
        self._td.cleanup()

    def test_case_dir_with_legacy_labelled_turn(self):
        make_skill(self.repo, "s1")
        make_case_dir(self.repo, "s1", "c1",
                      "---\ntags: [x]\nmax_turns: 5\nallowed_tools: [Read]\n---\n\nPlease split.\n\n"
                      "Turn 2 (sent after the reply): approved, go.\n", [LLM % "It proposes."])
        cases = RE.discover(self.repo)
        self.assertEqual(len(cases), 1)
        c = cases[0]
        self.assertEqual((c.id, c.format, c.legacy), ("s1/c1", "case-dir", "labelled-turn"))
        self.assertEqual(c.turns, ["Please split.", "approved, go."])
        self.assertEqual(c.assertions[0]["type"], "llm")
        self.assertIn("x", c.tags)
        self.assertEqual(c.problems, [])

    def test_case_dir_turns_convention_and_grader_types(self):
        make_skill(self.repo, "s1")
        make_case_dir(self.repo, "s1", "c2", "---\nturns:\n  - one\n  - two\n---\nignored body\n",
                      ["---\ntype: contains\ntext: hello\n---\n", "---\ntype: llm\nweight: 0\n---\nsoft\n"])
        c = RE.discover(self.repo)[0]
        self.assertEqual(c.turns, ["one", "two"])
        self.assertIsNone(c.legacy)
        self.assertEqual(c.assertions[0]["type"], "contains")
        self.assertFalse(c.assertions[1]["required"])

    def test_evals_json_followup_and_turns(self):
        make_skill(self.repo, "w")
        write(self.repo / "evals" / "evals.json", json.dumps({"cases": [
            {"id": "a-01", "skill": "w", "setup": "Any repo.", "prompt": "p1", "followup": "approved",
             "expect": ["x"], "must_not": ["y"]},
            {"id": "a-02", "skill": "none", "setup": "Any repo.", "turns": ["t1", "t2", "t3"], "expect": ["z"],
             "must_not": []}]}))
        cs = {c.id: c for c in RE.discover(self.repo)}
        self.assertEqual(cs["w/a-01"].turns, ["p1", "approved"])
        self.assertEqual(cs["w/a-01"].legacy, "followup")
        self.assertEqual([a.get("negate") for a in cs["w/a-01"].assertions], [None, True])
        self.assertEqual(len(cs["none/a-02"].turns), 3)
        self.assertIn("negative", cs["none/a-02"].tags)

    def test_trigger_md_variants(self):
        for s in ("qa-a", "qa-b"):
            make_skill(self.repo, s)
        write(self.repo / "evals" / "trigger-prompts.md",
              "# T\n\n## qa-a\n| | Prompt |\n|---|---|\n| ✅ | do a thing |\n| ❌ | other thing → `qa-b` |\n"
              "| ❌ | plain (note) |\n\n## Ambiguous prompts\n| | Prompt |\n|---|---|\n| ✅ | skip me |\n")
        write(self.repo / "evals" / "trigger-tests.md",
              "| # | Prompt | Context | Expected |\n|---|---|---|---|\n"
              "| 1 | build app | empty | qa-a |\n| 2 | fix typo | any | none (trivial) |\n"
              "| 3 | fix dup | repo | qa-b (NOT qa-a) |\n")
        cs = {c.id: c for c in RE.discover(self.repo)}
        self.assertEqual(len([c for c in cs.values() if c.format == "trigger-md"]), 6)
        pos = cs["qa-a/trigger-01"]
        self.assertEqual(pos.assertions[0]["type"], "skill_fired")
        neg = cs["qa-a/trigger-02"]
        self.assertEqual([a["type"] for a in neg.assertions], ["skill_not_fired", "skill_fired"])
        self.assertEqual(cs["qa-a/trigger-03"].turns, ["plain"])
        self.assertEqual(cs["qa-a/trigger-1"].assertions[0].get("exclusive"), True)
        self.assertEqual(cs["none/trigger-2"].assertions[0]["skill"], "*")
        self.assertEqual([a["type"] for a in cs["qa-b/trigger-3"].assertions], ["skill_fired", "skill_not_fired"])

    def test_scenario_md(self):
        make_skill(self.repo, "dev-x")
        write(self.repo / "evals" / "scenarios" / "01-demo.md",
              "# Scenario 01 - Demo (dev-x)\n\n**Setup:** empty folder.\n\n"
              "**Turn 1 (user):** `hello there`\n\nChecklist turn 1\n- MUST: label shown\n- SHOULD: short\n\n"
              "**Turn 2 (user):** `ok go`\n\nChecklist turn 2\n- MUST: writes plan\n- FAIL: writes code\n\n"
              "**Fail signs:** invented libs.\n")
        write(self.repo / "evals" / "scenarios" / "03-sub.md",
              "# Scenario 03 - Sub\n\n**Setup:** any repo.\n\n## 3a - A\n**User:** `typo`\n- MUST: edits\n\n"
              "## 3b - B\n**User (after 3a):** `more`\n- MUST: x\n")
        cs = {c.id: c for c in RE.discover(self.repo)}
        c = cs["dev-x/scenario-01-demo"]
        self.assertEqual(c.turns, ["hello there", "ok go"])
        self.assertEqual([(a.get("turn"), a.get("required"), a.get("negate")) for a in c.assertions],
                         [(1, None, None), (1, False, None), (2, None, None), (2, None, True), (None, None, True)])
        self.assertIsNone(c.manual)
        self.assertEqual(cs["scenario/scenario-03-sub-3a"].turns, ["typo"])
        self.assertIn("continues", cs["scenario/scenario-03-sub-3b"].manual)

    def test_behavior_md(self):
        write(self.repo / "evals" / "behavior-checks.md",
              '# B\n\n## B1 - Label (qa-a)\n**Prompt:** "Do a thing" (remark)\n- [ ] first\n- [ ] second\n\n'
              '## B2 - Vague\n**Prompt:** Provide four requirements\n- [ ] x\n')
        cs = {c.id: c for c in RE.discover(self.repo)}
        self.assertEqual(cs["none/b1"].turns, ["Do a thing"])
        self.assertEqual(len(cs["none/b1"].assertions), 2)
        self.assertTrue(cs["none/b2"].manual)

    def test_filters(self):
        make_skill(self.repo, "s1")
        make_skill(self.repo, "s2")
        make_case_dir(self.repo, "s1", "a", "---\ntags: [t1]\n---\np\n", [LLM % "g"])
        make_case_dir(self.repo, "s2", "b", "---\ntags: [t2]\n---\np\n", [LLM % "g"])
        cases = RE.discover(self.repo)
        self.assertEqual([c.id for c in RE.select(cases, skill=["s2"])], ["s2/b"])
        self.assertEqual([c.id for c in RE.select(cases, case=["s1/a"])], ["s1/a"])
        self.assertEqual([c.id for c in RE.select(cases, tag=["t1"])], ["s1/a"])
        self.assertEqual(len(RE.select(cases)), 2)


class DryRunTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.repo = Path(self._td.name) / "repo"
        self.repo.mkdir()
        make_skill(self.repo, "s1")

    def tearDown(self):
        self._td.cleanup()

    def test_valid_case_has_no_problems(self):
        make_case_dir(self.repo, "s1", "ok", "Input files: a.txt\n\nhi\n", [LLM % "g"],
                      scaffold='#!/usr/bin/env bash\nset -eu\ncp -R "$(dirname "$0")/files/." .\n',
                      files={"a.txt": "data"})
        cases = RE.discover(self.repo)
        out = []
        self.assertEqual(RE.dry_run(cases, [self.repo], log=out.append), 0)
        self.assertIn("cases found: 1", out[-1])

    def test_missing_input_file_and_bad_grader_reported(self):
        make_case_dir(self.repo, "s1", "bad", "Input files: missing.txt\n\nhi\n",
                      ["---\ntype: regex\n---\n", "---\ntype: nonsense\n---\n"],
                      scaffold="#!/usr/bin/env bash\nset -eu\nmkdir -p x\n")
        cases = RE.discover(self.repo)
        out = []
        n = RE.dry_run(cases, [self.repo], log=out.append)
        self.assertGreaterEqual(n, 3)
        text = "\n".join(out)
        self.assertIn("missing.txt", text)
        self.assertIn("unknown assertion type", text)

    def test_python_fallback_scaffold(self):
        d = make_case_dir(self.repo, "s1", "py", "hi\n", [LLM % "g"],
                          scaffold="#!/usr/bin/env bash\nset -eu\nmkdir -p src\ncat > src/a.txt <<'EOF'\nline1\nEOF\n"
                                   'cp -R "$(dirname "$0")/files/." .\n', files={"b.txt": "B"})
        dest = Path(tempfile.mkdtemp())
        try:
            self.assertIsNone(RE.run_scaffold(d / "place-files.sh", dest, force_python=True))
            self.assertEqual((dest / "src" / "a.txt").read_text(encoding="utf-8").strip(), "line1")
            self.assertEqual((dest / "b.txt").read_text(encoding="utf-8"), "B")
        finally:
            RE.rmtree(dest)


def tr_with(project, replies, skills=None, installed=()):
    tr = RE.Transcript(project, installed)
    for i, r in enumerate(replies):
        tr.turns.append({"prompt": "p%d" % i, "reply": r, "skills": (skills or [[]] * len(replies))[i], "tools": []})
    return tr


class AssertionTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.p = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def g(self, a, tr):
        return RE.grade_deterministic(a, tr)[0]

    def test_contains_regex(self):
        tr = tr_with(self.p, ["[Phase 1/5] Hello World", "second reply"])
        self.assertTrue(self.g({"type": "contains", "text": "Hello"}, tr))
        self.assertTrue(self.g({"type": "contains", "text": "hello", "case_insensitive": True}, tr))
        self.assertFalse(self.g({"type": "contains", "text": "second", "in": "first"}, tr))
        self.assertTrue(self.g({"type": "contains", "text": "second", "in": "last"}, tr))
        self.assertTrue(self.g({"type": "contains", "text": "second", "in": 2}, tr))
        self.assertTrue(self.g({"type": "not_contains", "text": "nope"}, tr))
        self.assertFalse(self.g({"type": "not_contains", "text": "Hello"}, tr))
        self.assertTrue(self.g({"type": "regex", "pattern": r"Phase \d/5"}, tr))
        self.assertTrue(self.g({"type": "not_regex", "pattern": r"Phase 9"}, tr))
        self.assertFalse(self.g({"type": "not_regex", "pattern": r"Phase \d"}, tr))

    def test_label_first_line_and_max_lines(self):
        tr = tr_with(self.p, ["\n[Phase 1/5: X]\nbody", "[Phase 2/5: Y]\nmore"])
        self.assertTrue(self.g({"type": "label_first_line", "pattern": r"^\[Phase \d/5"}, tr))
        tr2 = tr_with(self.p, ["[Phase 1/5]", "no label here"])
        self.assertFalse(self.g({"type": "label_first_line", "pattern": r"^\[Phase"}, tr2))
        self.assertTrue(self.g({"type": "label_first_line", "pattern": r"^\[Phase", "in": "first"}, tr2))
        self.assertTrue(self.g({"type": "max_lines", "max": 2}, tr))
        self.assertFalse(self.g({"type": "max_lines", "max": 1}, tr))

    def test_files_and_command(self):
        write(self.p / "docs" / "adr" / "003-x.md", "# ADR\nDecision: pg")
        tr = tr_with(self.p, ["x"])
        self.assertTrue(self.g({"type": "file_exists", "path": "docs/adr/003-*.md"}, tr))
        self.assertFalse(self.g({"type": "file_exists", "path": "docs/adr/004-*.md"}, tr))
        self.assertTrue(self.g({"type": "file_contains", "path": "docs/adr/*.md", "text": "Decision"}, tr))
        self.assertTrue(self.g({"type": "file_contains", "path": "docs/adr/003-x.md", "pattern": r"pg$"}, tr))
        self.assertFalse(self.g({"type": "file_contains", "path": "docs/adr/003-x.md", "text": "mongo"}, tr))
        self.assertTrue(self.g({"type": "command_exit_code", "command": "exit 0"}, tr))
        self.assertTrue(self.g({"type": "command_exit_code", "command": "exit 3", "expect": 3}, tr))
        self.assertFalse(self.g({"type": "command_exit_code", "command": "exit 3"}, tr))

    def test_skill_assertions(self):
        tr = tr_with(self.p, ["x"], skills=[["a"]], installed={"a", "b"})
        self.assertTrue(self.g({"type": "skill_fired", "skill": "a"}, tr))
        self.assertFalse(self.g({"type": "skill_fired", "skill": "b"}, tr))
        self.assertTrue(self.g({"type": "skill_not_fired", "skill": "b"}, tr))
        self.assertFalse(self.g({"type": "skill_not_fired", "skill": "*"}, tr))
        tr2 = tr_with(self.p, ["x"], skills=[["a", "b"]], installed={"a", "b"})
        self.assertFalse(self.g({"type": "skill_fired", "skill": "a", "exclusive": True}, tr2))

    def test_extract_skill_names(self):
        self.assertEqual(RE.extract_skill_names([{"name": "Skill", "input": {"skill": "pkg:qa-x"}},
                                                 {"name": "Read", "input": {}}]), ["qa-x"])


def make_runner_repo(root):
    repo = Path(root) / "repo"
    make_skill(repo, "s1")
    make_case_dir(repo, "s1", "pass-case", "Q1\n\nTurn 2 (after): approved\n",
                  [LLM % "It proposes first.", "---\ntype: contains\ntext: DONE\nin: last\n---\n"])
    make_case_dir(repo, "s1", "fail-case", "Q\n", ["---\ntype: contains\ntext: MAGIC\n---\n"])
    make_case_dir(repo, "s1", "err-case", "Q\n", [LLM % "g"])
    make_case_dir(repo, "s1", "file-case", "Q\n", ["---\ntype: file_exists\npath: out/result.md\n---\n"])
    return repo


MOCK = {
    "default": {"reply": ""},
    "cases": {
        "s1/pass-case": {"turns": [{"reply": "[Phase 1] proposal"}, {"reply": "DONE"}]},
        "s1/fail-case": {"turns": [{"reply": "nothing"}]},
        "s1/err-case": {"turns": [{"error": "timeout after 5s"}]},
        "s1/file-case": {"turns": [{"reply": "wrote", "files": {"out/result.md": "x"}}]},
    },
    "graders": {"default": {"pass": True, "evidence": "mock ok"}},
}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.repo = make_runner_repo(self._td.name)
        self.opts = RE.Opts()

    def tearDown(self):
        self._td.cleanup()

    def run_cases(self, mock, case_filter=None, runs=1):
        cases = RE.select(RE.discover(self.repo), case=case_filter)
        backend = RE.MockBackend(self.opts, mock)
        return RE.run_all(cases, backend, self.opts, [self.repo], runs, {"s1"}, log=lambda *_: None)

    def test_multi_turn_and_statuses(self):
        entries = {e["id"]: e for e in self.run_cases(MOCK)}
        self.assertEqual(entries["s1/pass-case"]["status"], "pass")
        self.assertEqual(len(entries["s1/pass-case"]["runs"][0]["turns"]), 2)
        self.assertEqual(entries["s1/fail-case"]["status"], "fail")
        self.assertEqual(entries["s1/err-case"]["status"], "error")
        self.assertIn("timeout", entries["s1/err-case"]["reason"])
        self.assertEqual(entries["s1/file-case"]["status"], "pass")
        s = RE.summarize(list(entries.values()))
        self.assertEqual((s["pass"], s["fail"], s["error"], s["skipped"]), (2, 1, 1, 0))
        self.assertEqual(RE.exit_code(s), 1)

    def test_exit_codes(self):
        self.assertEqual(RE.exit_code({"fail": 0, "error": 0}), 0)
        self.assertEqual(RE.exit_code({"fail": 0, "error": 2}), 2)
        self.assertEqual(RE.exit_code({"fail": 1, "error": 2}), 1)

    def test_llm_fail_records_evidence_and_no_llm_skips(self):
        mock = json.loads(json.dumps(MOCK))
        mock["graders"] = {"default": {"pass": False, "evidence": "no proposal seen"}}
        e = {x["id"]: x for x in self.run_cases(mock, ["s1/pass-case"])}["s1/pass-case"]
        self.assertEqual(e["status"], "fail")
        self.assertEqual(e["runs"][0]["assertions"][0]["evidence"], "no proposal seen")
        self.opts.no_llm = True
        e = self.run_cases(MOCK, ["s1/pass-case"])[0]
        self.assertEqual(e["runs"][0]["assertions"][0]["status"], "skipped")
        self.assertEqual(e["status"], "pass")

    def test_grader_error_is_runner_error_not_fail(self):
        mock = json.loads(json.dumps(MOCK))
        mock["graders"] = {"default": {"pass": True, "error": "x"}, "by_text": {"proposes": {"pass": False, "error": "grader down"}}}
        e = self.run_cases(mock, ["s1/pass-case"])[0]
        self.assertEqual(e["status"], "error")

    def test_runs_majority(self):
        mock = json.loads(json.dumps(MOCK))
        mock["cases"]["s1/fail-case"] = {"runs": [[{"reply": "MAGIC"}], [{"reply": "MAGIC"}], [{"reply": "no"}]]}
        e = self.run_cases(mock, ["s1/fail-case"], runs=3)[0]
        self.assertEqual([r["status"] for r in e["runs"]], ["pass", "pass", "fail"])
        self.assertEqual(e["status"], "pass")
        self.assertEqual(RE.majority(["pass", "fail"]), "fail")
        self.assertEqual(RE.majority(["error", "error"]), "error")
        self.assertEqual(RE.majority(["error", "pass", "fail", "fail"]), "fail")

    def test_prose_fixture_is_skipped_by_default(self):
        write(self.repo / "evals" / "evals.json", json.dumps({"cases": [
            {"id": "p-01", "skill": "s1", "setup": "Node 20 project with package.json.", "prompt": "hi",
             "expect": ["x"], "must_not": []}]}))
        entries = {e["id"]: e for e in self.run_cases(MOCK, ["s1/p-01"])}
        self.assertEqual(entries["s1/p-01"]["status"], "skipped")
        self.assertIn("prose", entries["s1/p-01"]["reason"])

    def test_main_end_to_end_reports_and_exit_code(self):
        mock = Path(self._td.name) / "mock.json"
        mock.write_text(json.dumps(MOCK), encoding="utf-8")
        rj, rm = Path(self._td.name) / "o" / "r.json", Path(self._td.name) / "o" / "r.md"
        code = RE.main(["--repo", str(self.repo), "--backend", "mock", "--mock-file", str(mock),
                        "--report", str(rj), "--report", str(rm)])
        self.assertEqual(code, 1)
        data = json.loads(rj.read_text(encoding="utf-8"))
        self.assertEqual(data["summary"], {"total": 4, "pass": 2, "fail": 1, "error": 1, "skipped": 0})
        md = rm.read_text(encoding="utf-8")
        self.assertIn("| s1/fail-case | case-dir | FAIL", md)
        self.assertIn("runner error", md)
        code_ok = RE.main(["--repo", str(self.repo), "--backend", "mock", "--mock-file", str(mock),
                           "--case", "s1/pass-case"])
        self.assertEqual(code_ok, 0)

    def test_list_and_dry_run_exit_codes(self):
        self.assertEqual(RE.main(["--repo", str(self.repo), "--list"]), 0)
        self.assertEqual(RE.main(["--repo", str(self.repo), "--dry-run"]), 0)
        make_case_dir(self.repo, "s1", "broken", "x\n", ["---\ntype: regex\n---\n"])
        self.assertEqual(RE.main(["--repo", str(self.repo), "--dry-run"]), 1)


class ClaudeBackendTests(unittest.TestCase):
    STREAM = "\n".join([
        json.dumps({"type": "system", "subtype": "init", "session_id": "sid-1"}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "qa-x"}},
            {"type": "text", "text": "partial"}]}}),
        json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "final answer",
                    "session_id": "sid-1", "total_cost_usd": 0.01}),
    ])

    def test_parse_stream_json(self):
        r = RE.parse_stream_json(self.STREAM)
        self.assertEqual((r["text"], r["session_id"], r["error"]), ("final answer", "sid-1", None))
        self.assertEqual(RE.extract_skill_names(r["tool_uses"]), ["qa-x"])
        self.assertIsNotNone(RE.parse_stream_json("garbage")["error"])

    def test_turn_args_and_resume(self):
        calls = []
        orig = RE.run_claude_cli
        RE.run_claude_cli = lambda args, stdin, cwd, timeout, claude_bin="claude": (
            calls.append((list(args), stdin)) or (0, self.STREAM, ""))
        try:
            o = RE.Opts(model="sonnet", max_turns=7)
            b = RE.ClaudeBackend(o)
            case = RE.Case(id="s/c", format="case-dir", turns=["a", "b"], allowed_tools=["Read", "Bash"])
            st = b.start(case, 0)
            r1 = b.turn(st, case, 0, "first", ".")
            b.turn(st, case, 1, "second", ".")
        finally:
            RE.run_claude_cli = orig
        a1, a2 = calls[0][0], calls[1][0]
        self.assertNotIn("--resume", a1)
        self.assertEqual(a2[a2.index("--resume") + 1], "sid-1")
        self.assertEqual(a1[a1.index("--allowedTools") + 1], "Read,Bash")
        self.assertEqual(a1[a1.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(a1[a1.index("--model") + 1], "sonnet")
        self.assertEqual(calls[1][1], "second")  # prompt goes on stdin
        self.assertEqual(r1["skills"], ["qa-x"])
        known = {"-p", "--output-format", "stream-json", "--verbose", "--permission-mode", "--allowedTools",
                 "--model", "--max-turns", "--resume"}
        self.assertTrue(all(x in known or not x.startswith("-") for x in a2), a2)

    def test_grader_parses_structured_output(self):
        orig = RE.run_claude_cli
        RE.run_claude_cli = lambda *a, **k: (0, json.dumps({"structured_output": {"pass": True, "evidence": "q"}}), "")
        try:
            v, err = RE.ClaudeBackend(RE.Opts()).grade("x")
        finally:
            RE.run_claude_cli = orig
        self.assertEqual((v, err), ({"pass": True, "evidence": "q"}, None))
        RE.run_claude_cli = lambda *a, **k: (0, json.dumps({"result": "no verdict"}), "")
        try:
            v, err = RE.ClaudeBackend(RE.Opts()).grade("x")
        finally:
            RE.run_claude_cli = orig
        self.assertIsNone(v)
        self.assertTrue(err)


if __name__ == "__main__":
    unittest.main()
