# Migration handoff

Repository: rayggxia-workspace/pbit_kings. Owner: jieruiz. Issue: #1.
Branch: task/1-import-chimera. Source SHA: b2c0e774f03b5a7ec205f269e2170344df2139bd.
Original personal repository and mixed local working directory remain intact.
Read latest Issue, PR, AGENTS, STATUS and this handoff before resuming.

Run `python scripts/check_project.py`, `python work/jieruiz/1/verify_import.py`,
and `git diff --check`. Manifest hashes original source Git blobs, including
problem fixtures and configurations. No new EDA execution or timing closure claimed.

Delivered: [PR #2](https://github.com/rayggxia-workspace/pbit_kings/pull/2), open/not merged.
Import merge commit: de7e6f6. Latest documentation commit is the PR head.
Actual checks: management schema, 182 source-file/hash comparisons, Python AST,
16 Bash syntax checks, migration additions whitespace check all pass. Historical
source whitespace warnings remain, without reformatting.

Pending: management registration (management-hub Issue #3) and board permissions.
Registry rejects public projects; do not change visibility or weaken validator.
Maintainer must confirm a public-project registration process before a registry PR.
Projects GraphQL lacks read:project; do not borrow other accounts or silently
expand credential scope. An authorized maintainer must add/verify the Issue and
sync Project ID=pbit-kings, Status=In review, and the actual assignee.
First resume: fetch target, inspect PR #2 and Issue #1, then check management
Issue #3 for a resolved registration policy. Review before merging; no self-merge.
Review/merge requires a designated reviewer; none assigned automatically.
Do not import untracked PDK/IP/netlists/waves. Other historical branch tips remain
in the source repository. Results require an agreed authorized shared store.
