# Running the evals automatically

`scripts/run-evals.py` (Python 3.9+, standard library only) runs the eval cases of any skill repo against an
agent, multi-turn, grades them and writes a report. The canonical copy is in this repo; `sync-tools.py` copies it
into the dev, pull-request and docs repos. `qa-workflow-skills` keeps its own older script (a trigger-prompt runner
with `--cmd`, `--detect-regex`, `--only`, `--out`) because the shared tool is not a strict superset of it and that
repo's README and CHANGELOG document those flags. Run the shared tool on the QA repo with `--repo`.

## Formats it reads (unchanged, as they are)

| Format | Where | Used by |
|---|---|---|
| `case-dir` | `<skill>/evals/<case>/` with `case.yaml`, `prompt.md`, `graders/*.md`, optional `place-files.sh` + `files/` | pull-request repo, `delivery-lifecycle` |
| `evals-json` | `evals/evals.json` (`cases[]`: `id`, `skill`, `setup`, `prompt`, `expect`, `must_not`, optional `turns`/`followup`) | docs repo |
| `trigger-md` | `evals/*trigger*.md` tables: `✅/❌`, `yes/no`, or a numbered table with an `Expected` column | QA, dev, suite |
| `scenario-md` | `evals/scenarios/*.md`: `**Turn N (user):** \`text\`` plus `MUST` / `SHOULD` / `FAIL` bullets | dev repo |
| `behavior-md` | `evals/behavior-checks.md`: `## B1 ...`, `**Prompt:** "text"`, `- [ ]` checks | QA repo |

Cases that cannot be automated are listed as `manual` and reported as skipped, never as passed: scenario steps
without a literal backtick message, `behavior-md` prompts that are descriptions, sub-scenarios that continue another
one (`User (after 3b)`).

## Multi-turn convention: `turns:`

`turns` is the ordered list of user messages. Turn 2 is sent into the same session after the reply to turn 1.

```yaml
# prompt.md frontmatter (case-dir); the body is then only a human-readable note
---
tags: [skill-creator]
turns:
  - My branch is too big for one PR. Please propose how to split it.
  - approved, go ahead with the commands.
---
```

```json
{"id": "adr-01", "skill": "adr-writer", "setup": "...", "turns": ["Write an ADR ...", "approved"], "expect": ["..."]}
```

Legacy forms still work and are counted as "legacy multi-turn syntax" by `--dry-run`: a line
`Turn 2 (note): text` in the body of `prompt.md`, and `"followup": "text"` (or a list) in `evals.json`. New cases
should use `turns:`. In `scenario-md`, each `**Turn N (user):**` line is a turn already.

## Assertions

Deterministic: `contains`, `not_contains`, `regex`, `not_regex`, `file_exists`, `file_contains`, `max_lines`,
`label_first_line`, `command_exit_code`, plus `skill_fired` and `skill_not_fired` (used by trigger tables; skill
names come from `Skill` tool calls). Model graded: `llm`.

| Type | Params |
|---|---|
| `contains`, `not_contains` | `text`, optional `case_insensitive` |
| `regex`, `not_regex` | `pattern` (Python `re`, multiline) |
| `file_exists` | `path` (glob allowed, relative to the temp project) |
| `file_contains` | `path` (glob allowed) and `text` or `pattern` |
| `max_lines` | `max`: lines of the reply (each reply when `in` is `all`) |
| `label_first_line` | `pattern` matched against the first non-empty line of each selected reply |
| `command_exit_code` | `command` (run with bash when available), `expect` (default 0), `timeout` |
| `skill_fired`, `skill_not_fired` | `skill` (`*` = any installed skill), `exclusive` for `skill_fired` |
| `llm` | `text` (the rubric), optional `negate` (the thing must NOT happen), `turn` (hint) |

Common params: `in` (`all` default, `first`, `last`, or a turn number), `required: false` (advisory: reported, never
fails the case), `label`.

Where to write them:
- `case-dir`: each `graders/*.md` is one assertion. Frontmatter `type` defaults to `llm` and the body is the
  rubric; for another type put the params in the frontmatter (`type: contains`, `text: ...`, `in: last`).
  `weight: 0` makes an `llm` grader advisory. The existing graders are all `type: llm`.
- `evals-json`: `expect[]` become `llm` rubrics, `must_not[]` become negated `llm` rubrics. Add an optional
  `assertions: [{type, ...}]` list for deterministic checks, `setup_script` (path relative to `evals.json`) or
  `setup_files` (`{path: content}`) for a real fixture.
- `scenario-md`: `MUST` is a required `llm` assertion, `SHOULD` is advisory, `FAIL` and `Fail signs` are negated.
- `trigger-md`: row expectations become `skill_fired` / `skill_not_fired`.

The grader model gets the rubric and the whole transcript (user turns, replies, skills invoked, tools used, the files
left in the project) and must answer with strict JSON `{"pass": bool, "evidence": "..."}`; the evidence is stored in
the report. With `--runs N` the case verdict is the majority of the runs that completed (a tie fails).
The report separates `FAIL` (an assertion failed), `ERROR` (runner problem: CLI missing, timeout, grader gave no
verdict, fixture script failed) and `SKIPPED` (not automatable, or `--no-llm` left nothing to grade).

## How to write a case

1. Pick the skill folder, create `<skill>/evals/<short-name>/`.
2. `case.yaml`: `name`, `expected_outcome`, and `context: {scaffold_script: place-files.sh}` if you need files.
3. `prompt.md`: the user message(s) as above. Optional frontmatter: `tags`, `max_turns`, `timeout_seconds`,
   `allowed_tools`.
4. `place-files.sh` (run with the temp project as the working directory) and `files/` for fixtures; keep it
   deterministic, create git repos inside it if the skill needs one.
5. `graders/NN-name.md`: prefer deterministic assertions for anything checkable (a label on the first line, a file
   that must exist) and `llm` only for judgement.
6. `python scripts/run-evals.py --repo . --case <skill>/<short-name> --dry-run`, then run it once for real.

Fixtures that are only prose (`"setup": "Node 20 project with ..."` in `evals.json`, `**Setup:**` in scenarios) cannot
be built by a tool. Those cases are skipped unless you pass `--prose-setup inline`, which tells the model in turn 1 that
the project is described, not present (a weak test). To make them runnable add `setup_files` or a `setup_script`.

## Run locally

```powershell
# from ai-workflow-suite (or the repo's own copy of the script)
python scripts/run-evals.py --repo ../qa-workflow-skills --list
python scripts/run-evals.py --repo ../qa-workflow-skills --dry-run          # validates fixtures and graders, no model
python scripts/run-evals.py --repo ../code-review/skill-code-review --skill pr-splitter --runs 3 --report out.json --report out.md
python scripts/run-evals.py --repo ../docs-workflow-skills --tag negative --model sonnet --grader-model opus
python scripts/run-evals.py --repo ../dev-workflow-skills/dev-workflow-skills --no-llm   # trigger tables only, cheap
```

Filters: `--skill a,b`, `--case id-or-substring-or-glob`, `--tag trigger|scenario|negative|case-dir|...`.
Each run installs the repo's skills (copied, with their `evals/` folders left out so the model cannot read the
graders) into `.claude/skills` of a fresh temp project, runs the fixture script there, then sends the turns.
`--extra-skills ../other-repo` installs more skills (for example for `delivery-lifecycle`, which hands off to the
other repos). Exit code: 0 pass, 1 failures (or dry-run problems), 2 runner errors only.

Tools: default `--allowedTools Read,Glob,Grep,Skill,Write,Edit` with `--permission-mode dontAsk` (anything else is
denied). A case that declares `allowed_tools` in `prompt.md` (the existing ones include `Bash`) uses its own list;
`--allowed-tools` overrides both. Bash runs on your machine with your credentials inside a temp folder, not in a
sandbox: run unknown cases in a container or a throwaway VM.

## Run in CI

`.github/workflows/evals.yml` is manual only (`workflow_dispatch`, never on push or pull request). It needs the
repository secret `ANTHROPIC_API_KEY`, installs the CLI, runs the chosen repo (checked out next to the suite) and
uploads `out.json` / `out.md` as an artifact. Use `--runs 1` and a narrow `--skill` first.

## Cost and time

Every case is at least one CLI call per turn, plus one grader call per `llm` assertion; a case with 10 graders and
2 turns is about 12 calls and several minutes. `--runs 3` triples it. The 12 pull-request cases alone are around
100 calls per run. Use `--dry-run` and `--no-llm` first, then `--case`, then everything. `--max-budget-usd` caps one
turn, not the whole run.

## Honest limitations

- The grader is a model, often the same family as the agent under test: it shares blind spots and tends to be
  lenient with fluent answers. Treat `llm` passes as a smoke test, not a benchmark; use a different `--grader-model`
  and prefer deterministic assertions where one fits.
- Output is non-deterministic. One run (the default) says little; a flaky case needs `--runs 3` or more, and the
  majority rule hides the spread, so read the per-run table in the JSON report.
- Skills are discovered from `.claude/skills` and chosen by the agent; trigger results depend on the CLI version
  and the model. `Context` columns of trigger tables are not reproduced (the project is empty).
- Prose-only fixtures are skipped by default; `manual` cases are not covered at all.
- The CLI interface used here was written from the documentation without a local `claude` install: see the list
  below and treat the first real run as a check of the runner itself. The mock backend tests the logic, not the CLI.
- Costs shown by the CLI are estimates; the report stores the last reported cost per run when present.

## CLI flags used and their status

Documented at <https://code.claude.com/docs/en/headless> and <https://code.claude.com/docs/en/cli-reference>
(read 2026-11): `-p`, `--output-format` (`json`, `stream-json`), `--verbose`, `--resume <session id>`, `--allowedTools`,
`--permission-mode` (`dontAsk` is listed), `--model`, `--max-turns`, `--max-budget-usd`, `--json-schema` (result in
`structured_output`), `--tools ""` (disable all tools), prompt on stdin with `-p` (the `gh pr diff | claude -p` example).
`--bare` is not used: it skips skill discovery.

Not verified (all inside `run_claude_cli` / `ClaudeBackend` in `scripts/run-evals.py`, so easy to change):
- The stream-json event field names: `assistant` events with `message.content[]` blocks of type `text` / `tool_use`
  (`name`, `input`), the final `result` event fields `result`, `is_error`, `session_id`, `total_cost_usd`. The docs
  confirm `result`, `session_id`, `total_cost_usd` for `json` and that stream-json has a `result` message; the rest
  follows the Agent SDK message types and the old QA runner.
- The `Skill` tool call shape (`input.skill`) used to detect which skill fired.
- Whether `Skill` has to be in `--allowedTools` for `dontAsk`, and whether `--resume` combined with `-p` and a prompt
  on stdin continues the session in the same working directory (`--continue` is not used: the reference says it skips
  sessions created by `claude -p`).
- `--tools ""` together with `--json-schema` for the grader call, and `--permission-mode dontAsk` availability on older
  CLI versions.
- The default model when `--model` is omitted, and the cost of `--max-turns` exhaustion (the result then may have
  `is_error` set and the case is reported as a runner error).
