---
name: pr-desc
description: Generate a comprehensive PR description from the current branch — includes context, a summary of changes, and testing notes. Prints to stdout for the user to copy or pipe to `gh pr create`.
user-invocable: true
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff*)
  - Bash(git log*)
  - Bash(git rev-parse*)
  - Bash(git status*)
---

# /pr-desc — Generate PR Description

Generate a ready-to-use PR description from the current branch.

## Process

1. Get the commit log and full diff vs main:
   ```
   git log main...HEAD --oneline
   git diff main...HEAD
   ```

2. Read `CLAUDE.md` for project context (command behaviours, architecture constraints).

3. Draft the description (see format below).

## Output format

Print the description to stdout so the user can review and copy it, or pipe directly:
```
zeke pr-desc | gh pr create --title "..." --body-file -
```

---

## Summary

<!-- 2-4 bullet points: what changed and why -->

## Changes

<!-- Group by module. For each changed file, one line on what it does now differently. Skip files with only trivial/formatting changes. -->

## Behaviour notes

<!-- Any non-obvious edge cases, error paths, or design decisions implemented in this PR that a reviewer should know. Cross-reference CLAUDE.md behavioural rules where relevant. -->

## Testing

<!-- What was tested and how. List test files added/modified. Note any manual verification steps performed. -->

---

Keep the description factual and grounded in the diff. Do not speculate about future work or list things that did not change.
