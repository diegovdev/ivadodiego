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

## Spec Workflow — per feature

1. `/ck:spec` + use spec-writer → writes SPEC.md, outputs approval prompt
2. Review SPEC.md — if approved: paste approval prompt → spec-writer creates GitHub issue + outputs build prompt
3. Create GitButler stacked branch, paste build prompt
4. Open PR with `Closes #<issue-number>`

## decisions.md

Read before acting. Add an entry after every decision — what, why, rejected alternatives. Never re-decide what's already recorded.
