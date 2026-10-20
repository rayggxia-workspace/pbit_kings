# Recovery Diagnostic Handoff

Updated 2026-10-20 Asia/Shanghai. Owner: jieruiz.
Repository: rayggxia-workspace/pbit_kings. Issue #3.
Branch: task/3-reset-recovery-diagnostic.
Base: 16bc36c264d5a15ecac2f3c38031b767e2231d21, dependent import PR #2 open.
Current delivery commit is the commit containing this file; read `git log -1`.
Draft PR: https://github.com/rayggxia-workspace/pbit_kings/pull/4 (not merged).
Verified script commit: b4576399b0b1d17f8fa59f521ca0b6bb90e68435.
No merge/remote EDA completion is implied.

## Existing Evidence

Original archive: `backend_functional_38215256.tar.gz` in the user's APR_results.
SHA-256: c43ad39669325ad3b5ceb15756a7a94605d5b1b4583e0910fd8da28208911b7e.
The original source manifest matches the v2 scripts ZIP (33 files), SHA-256:
28e340656a72f1afa148e6a7b57181db6c62790860d59dd557fec0fd2684c603.
Crossbank/boundaries passed with zero timing events. Recovery functionality passed
but audit failed: 1,589 events, 1,575 different MAC pipeline flops, all inside
the definite core-reset-low interval. The original failure is not waived.

This is a real library check, plausibly invalid-pipeline reset activity; further
evidence is required. The unreset MAC dffe must be overwritten before meaningful
consumption. A PLL CKTST `inf` delay warning also needs review; vendor code intact.

## Delivered Scope

Standalone `sim/backend_recovery_diag_20261020` scripts. 300 MHz/WC/10 ps;
one compilation, three reset offsets; no expensive UART or power reruns, no VCD,
ordinary serial VCS without FGP license, 4 CPUs/8G requested. Existing reviewed
request-boundary adapter and two-first-stage profile retained. No new MAC waiver.

Read-only actual CK/E/D/Q monitors for 1,575 affected instances. Compare all 3,200
snapshot bits and RNG after clean/recovered two-sweep runs with actual majority=1.
Unknown enabled writes or capture mismatch conservatively fail. If warmup state
is intentionally invalid, inspect first valid consumer rather than dismissing it.
Stable clock pulse widths and all raw timing/model warnings are retained.

## Actual Validation

- `python -m unittest discover -s sim/backend_recovery_diag_20261020/tests -v`:
  13 tests PASS; original log parser, watcher negative tests, Python 3.6 grammar.
- Icarus top syntax with a stub environment PASS, NOT full-netlist simulation.
- `bash -n submit.sh` and `bash -n run_sbatch.sh` PASS.
- `python scripts/check_project.py` PASS.
- ZIP: 63,778 bytes, 30 manifested files, all SHA-256 checks PASS; shell LF PASS.
  Final ZIP SHA-256 is in DELIVERY.json (package has no vendor model/netlist).
- Commercial VCS/STA and remote runtime still NOT executed in this task.

## Next Executable Action

Upload `backend_recovery_diag_20261020_scripts.zip` to the existing server project
root, unzip with `-o`, then `cd backend_recovery_diag_20261020` and
`python3 run.py verify .`; `bash submit.sh all`. Exact paths and prerequisites are
in the package README_ZH.txt. Existing input checkpoint is job 38117744; if gone,
use CHECK_JOB=fresh to redo validation, not the already-passed functional tests.

Download `backend_recovery_diag_<JOBID>.tar.gz`. Read diagnostic_summary.json,
each diagnosis.json/reset_clock_trace.csv/simulation.log. A diagnostic-complete
marker is NOT chip timing PASS. Events outside definite reset, full snapshot/RNG
mismatch, unknown fresh writes or bad restarted clocks need concrete follow-up.
Reset-only events with passed targeted checks still require backend review of
reset release, pulse widths and valid-operation STA; finite tests are not formal
proof for every input. Keep Issue #3 open until acceptance and review.

## Collaboration / Storage

Current scripts are the only new task worktree; keep it sparse while awaiting
results, do not clone another full checkout. No raw input archive was extracted
to another full copy. Result archives and vendor files remain at authorized
local/server locations and are not public GitHub deliverables.
Public-project registry policy blocker remains in management-hub Issue #3.
No project board is configured in config/board.json; prior Projects query lacked
read:project scope. Board sync pending, responsible maintainer/reviewer to be
designated. Do not broaden credentials or invent a board/card ID.
