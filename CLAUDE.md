## Agents

| Agent | When to use |
|-------|-------------|
| `spec-writer` | Translate requirements into SPEC.md before any implementation |
| `code-writer` | Implement features, modules, pipelines, Docker configs, notebooks |
| `test-writer` | Write or fix tests for any module |
| `code-reviewer` | Review Python code quality before committing |
| `cloud-reviewer` | Review Dockerfiles, Docker Compose, CI/CD |

## Conventions

- Main package: `src/museums/`
- Tests: `tests/`
- No `print()` in library code — use logging
- Type hints required everywhere

## Spec Workflow — per task

1. `/ck:spec` + use spec-writer → writes SPEC.md, outputs build prompt
2. Review SPEC.md — if approved, paste build prompt
3. code-writer reads §T row → creates GitHub issue + GitButler branch if `issue`/`branch` cells = `-` → implements → updates §T issue/branch cells
4. test-writer → code-reviewer → `gh pr create --body "Closes #<issue>"` (PR is feature/stack-level, not tracked in §T)

Any agent answers "what's next?" with the right next-step prompt (work done) or outstanding-items list (work not done).

## decisions.md

Read before acting. Add an entry after every decision — what, why, rejected alternatives. Never re-decide what's already recorded.
