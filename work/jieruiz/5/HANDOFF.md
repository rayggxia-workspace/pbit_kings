# PLL Mode Validation Handoff

Date: 2026-10-20 Asia/Shanghai. Owner: jieruiz.
Repository: rayggxia-workspace/pbit_kings. Issue #5.
Branch: task/5-pll-mode-validation. Base: 05571587a8895d644f73c767bda02fa146ecedca,
dependent recovery PR #4 (not merged).
Draft PR #6: https://github.com/rayggxia-workspace/pbit_kings/pull/6, not merged.
Issue status in_review; server mode evidence pending, do not close task.
Sparse worktree: tmp/pbit-pll-issue5-20261020. Reuse it; no full clone needed.
Validated script commit: be9e1088e28e811a0f11f6d4d85556949a73b2cd.
Final ZIP index/SHA-256 and local checks: DELIVERY.json (61,141 bytes, 29 files).

## Goal and Scope

Standalone backend_pll_modes_20261020 suite for latest backend_261014 netlist,
vendor PLL_20260916, default WC maximum SDF / optional separate BC minimum SDF,
10 ps. No DUT changes, no vendor functional patch, no global timing-check disable,
no FGP, no VCD or power rerun. Existing two-first-stage narrow profile retained.

Cases: cold25 bypass; 300/150/25/300/same300 APPLY; invalid commands/configs,
BUSY rejections/clear and APPLY during active compute followed by recovery at150.
Each epoch has actual PLL UART (except precisely targeted short-BUSY injection),
two actual core UART probes and tiny two-node MaxCut/run/snapshot. Current core
divider500 means600/300/50 kbaud; configUART stays1M. Mixed transport is logged,
not misrepresented as all-pin full-array configuration. Core resets on APPLY.

## Known Prior Evidence

Recovery archive backend_recovery_diag_38219776.tar.gz SHA256:
e60016fa0c04697a58c48dbf4405338afa8ad68aaf8e77d1ce5b3b6e2c9019c8.
Three phases targeted functionality pass, timing events1586/9/0 all in reset,
1575 observed flops refreshed, complete3200-bit snapshot and selected RNG match.
PLL inf/stop pulses remain. This is not the new mode-suite result or timing signoff.
Existing real-UART38168732 and crossbank/boundaries38215256 should not be rerun
just to prove the new scripts exist. Historical ideal-PLL mode tests do not prove
the current vendor model/SDF paths.

## Actual Local Verification

15 unittest methods PASS; 2 Bash syntax checks PASS. XSim2018.3 elaborates actual
new host/TB with declaration-only DUT and executes actual core/PLL host codecs
against synthetic serial peers, including back-to-back bytes and three bauds.
Icarus executes clock-guard valid/short/stop/reset tests. Audit negative fixtures
and Python3.6 grammar PASS. Explicit WC/BC literal MTM selection unit-tested.
The old Icarus cannot elaborate the host concurrency; it was not used to claim
that check. No full-netlist VCS or analog/STA/power test has run locally.

Host changes are testbench only: dynamic bit period; serialized transaction
storage/guard; stop-bit center return to re-arm before a back-to-back byte.
Keep watchdog/start/stop/frame checks intact. Actual netlist acceptance is pending.

## Next Actions

Upload the scripts ZIP from the local a_P_BIT root to the existing server project
root. Unzip -o, cd backend_pll_modes_20261020, python3 run.py verify ., then
bash submit.sh all. Optional CORNER=BC bash submit.sh all is separate build/job.
Exact paths/checkpoint/build-reuse commands are in README_ZH.txt.
Default4CPU/8G, serialVCS. No self-imposed wall cap, subject to scheduler policy.

Download backend_pll_modes_<JOBID>.tar.gz. Review diagnostic_summary.json and
case audit.json, epochs.jsonl, transactions.jsonl, checks.jsonl, mode_trace.csv
and raw simulation.log. Validate source manifest/coverage-binding hashes.
If only a case needs rerun, BUILD_JOB may reuse the SAME release/corner/input
build; source/corner changes must reject stale binary. Do not delete link targets.

Review-required reset/model warnings are retained, not silently waived. Any
outside-reset event/pulse, bad UART result, wrong mode/clock, missing check or
bad snapshot fails. If compile fails, raw compile.log remains on the server and
must be tailed separately (excluded from small result archive).

Confirm with vendor actual stop/start/BP/EN rules and startup wait; no LOCK is
measured here. No claim of clock-loss/analog fault recovery. Backend must still
check local reset tree, recovery/removal, pulse widths and real working STA.

## Collaboration

No raw netlist/model/PDK/result archive uploaded publicly. Only scripts and small
provenance. Preserve existing registered/pending import records. Projects target
board is not configured; query/sync still needs explicit target and permissions,
do not invent board IDs or create a workaround board. Reviewer to be designated.
Read current Issue/PR and this handoff on resume, not stale older STATUS alone.
Fresh 2026-10-20 GraphQL readback: Issue #5 has 0 visible projectItems; target
board remains unspecified, so this is not evidence of synchronized board state.
