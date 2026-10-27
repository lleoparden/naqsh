# Phase and slice workflow

One epic issue per phase, created up front. One sub-issue per approved slice,
created when the phase starts — never speculatively.

## 1. Epic issue (one per phase, up front)

An epic is self-contained and records:

- the phase goal and why it exists in the program;
- what it depends on, and what depends on it;
- deliverables, taken from `docs/plan.md`;
- go/no-go gates and the evidence each gate needs;
- exit criteria;
- explicit non-goals, so scope cannot drift;
- risks, fallbacks, and open decisions;
- the pull-request strategy for the phase;
- a task list linking each sub-issue.

## 2. Sub-issue (when the phase starts)

Written before any code. Each carries the full slice plan:

- the problem and the intended user-visible outcome;
- the approved slice reference in `docs/plan.md`;
- every file, module, type, endpoint, or asset it creates or changes;
- the boundaries it touches (frontend/backend, model calls, cost, export format);
- acceptance criteria and the exact checks or evidence to run;
- risks, failure cases, and rollback;
- the `docs/api-findings.md`, `docs/submission-notes.md`, and `docs/DECISIONS.md`
  updates it must carry.

## 3. Pull requests

- One branch serves one work item, named `type/slug`.
- Every commit and PR references its issue; PRs use the template in `.github/`.
- A PR is not ready until its scope is complete, its docs updates are included, and
  the checks below were run on the branch head.
- **Self-review before merge.** Re-read the full diff as a reviewer and post what
  it actually changes, the counter-argument or risk found, what was verified, and
  any residual doubt. An unresolved doubt blocks the merge.
- The agent may merge a small, self-contained PR with a merge commit when checks
  pass and self-review is clean. Big or important PRs (pipeline contract, cost
  model, security, public interfaces, more than a few hundred non-test lines) need
  the owner's review and merge decision.
- Never squash, rebase, force-push, delete a branch, or push directly to `main`.

## 4. Agent-ready issues

An issue may be labeled `agent-ready` only when it has: the user problem and
expected outcome, clear scope boundaries, testable acceptance criteria, relevant
risks and dependencies, an approved plan reference, and no unresolved product or
platform decision. Remove the label as soon as any of that becomes ambiguous.
