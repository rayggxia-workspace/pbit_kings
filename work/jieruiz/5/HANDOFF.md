# PLL Mode Validation Handoff

## Latest: v3 Switch-Only Continuation, 2026-10-21

Validated source0bccec8fe54c0b9a97d12f4f9c05fcbf9574ba50. Final ZIP
backend_pll_modes_20261021_v3_scripts.zip:83,682 bytes,36 files, SHA256
747eaebc6a763b42ba006a0234f362dadf2ac722c07027088d99845f629b03df.
All36 package bytes match Git source blobs; syntax/schema checks PASS.

Reviewed actual v2 job38230453, archive SHA256
a04394f619986ccb1a79a3097a7d53eec5aa9520e4fe6d2f17ff1299ae30bb9c.
All33 v2 source identities matched. Cold25 bypass completed pin UART/compute/
full3200-bit snapshot; complete40ns period,20.20/19.80ns pulses,reference lag
0.18..0.19ns. Safe and no-injection controls raw timing0, legacy reproduces the
same30ps hold within60ps of handoff. A VCS packed-string padding bug made the
v2 probe audit incorrectly fail scope; raw trace supports injection causality.
Standalone original1ps and matched10ps vendor models both reproduce6 inf warnings
and6 runt pulses (1ps vs10ps), independently of the chip/SDF.

Switch stopped before its third APPLY: target mhz changed25 while active clock
was still150. The new reference checker was incorrectly enabled by target mode.
v3 separates confirmed active_mhz, adds tested reference-guard unit and explicit
string labels. No DUT/SDF/vendor behavior changes and no new timing waiver.
errors18 checks still pass, full snapshot200 words known;4540 distinct MAC E
setuphold events occur1603265.86..1603266.24ns after reset assertion1603263.27,
well before PLL EN-off1603421.82. No extra active-window event, but this is not
proof all affected internal registers refill or STA is clean. Backend review stays.

26 local tests PASS49.86s, including actual frozen v2 archive re-audit without EDA
and an orchestration fixture checking only one build/switch with no model rerun.
Frozen57-input index prevents reuse of modified/wrong evidence. Historical
padding normalization is documented and leaves all raw bytes unchanged; raw
negative-control failure remains explicit. Small local re-audit output:
result_pipeline/PLL_38230453_REAUDIT_v3 (outside this checkout), no large extract.

Next user run: upload backend_pll_modes_20261021_v3_scripts.zip, verify
VERSION20261021_pll_modes_v3 and manifest, then
PREVIOUS_RESULT=/public3/home/t6s011227/pbit_chimera_pipeline_20260920/backend_pll_modes_20261020/results/38230453 BUILD_JOB= bash submit.sh switch
Only switch is simulated; previous five cases/model probes are hash-checked and
re-audited. New source means a new chip executable must compile; do not reuse v2
build. Combined summary explicitly distinguishes historical vs new simulation.
Use the original tar.gz as PREVIOUS_RESULT if the result directory is archived.
Historical re-audit checks recorded coverage provenance, not current binaries or
fresh coverage; licensing inputs and raw archives remain outside Git.
Publication/ZIP identity is recorded in DELIVERY.json. Below is preserved history.

## Latest: v2 Suspect Diagnostics, 2026-10-20

Validated v2 source commit7cd8c8b6b4309012cb285c6d8f42c5e61b3c97db;
package72799 bytes/33 files, SHA256
452e28be5de87cdcc926967ea5ffec1de66f448a9eaeee3868a6e5877251df15.
All33 ZIP source bytes match Git blobs. Bash syntax/schema checks PASS.
Ordinary Git push failed again with connection reset. Remote draft PR6 still
has a875049 until connectivity returns; do not claim v2 source is remotely pushed.
Local ZIP is authoritative and can be uploaded to HPC independently. Issue/PR
receipts are synchronized via API without substituting another member's identity.

v1 job38227554 downloaded and independently reviewed; exact final v1 source
manifest matched. See sim/backend_pll_modes_20261020/REVIEW_38227554_ZH.txt.
Bypass failure was an overly strict project-written guard; period40ns remained
correct while pulses20.20/19.80ns were rejected. One extra30ps req_addr[3] hold
is a Q-feedback/injection suspect, not a proven silicon failure or an allowed
waiver. Original netlist CK evidence: address3=CTS_8; write-launch=CTS_5.
82 MAC/RNG reset-window events and vendor inf/runt behavior remain explicit.

User requested diagnostic scripts for all suspects. v2 in the SAME package
directory/branch adds full-period/duty/reference checks, three bus controls,
isolated original-vendor1ps/matched10ps stop probes and full snapshot X checks.
No DUT/SDF/vendor-function patch, no global/narrow new waiver, no PT rerun.
21 local unittest checks PASS (39.19s). Full-top elaboration uses declaration-only
DUT, actual UART hosts execute with synthetic peers; actual licensed PLL ports
elaborated only. Remote v2 VCS is NOT yet run. Version20261020_pll_modes_v2.

Next: upload backend_pll_modes_20261020_v2_scripts.zip to existing server root,
unzip -o, verify VERSION/manifest and bash submit.sh all. quick selects only
three bus controls plus model probes. Do not reuse38227554/v1 build. Download
backend_pll_modes_JOBID.tar.gz; first inspect suspect_diagnosis.json, then each
raw case audit/clock_metrics/mode_trace and model_probe summaries. Legacy control
may intentionally reproduce the original hold; raw failure remains recorded.
Only clean safe/no-injection controls plus correlated legacy reproduction support
an injection-artifact diagnosis. No causality conclusion before these runs.
Full output X checks do not prove all internal unreset pipeline flops are known.

Current local delivery and publication facts are in DELIVERY.json; below is
preserved v1 handoff history, not the current server-run status.

Date: 2026-10-20 Asia/Shanghai. Owner: jieruiz.
Repository: rayggxia-workspace/pbit_kings. Issue #5.
Branch: task/5-pll-mode-validation. Base: 05571587a8895d644f73c767bda02fa146ecedca,
dependent recovery PR #4 (not merged).
Draft PR #6: https://github.com/rayggxia-workspace/pbit_kings/pull/6, not merged.
Issue status in_review; server mode evidence pending, do not close task.
Sparse worktree: tmp/pbit-pll-issue5-20261020. Reuse it; no full clone needed.
Validated script commit: be9e1088e28e811a0f11f6d4d85556949a73b2cd.
Final ZIP index/SHA-256 and local checks: DELIVERY.json (61,141 bytes, 29 files).
Final GitHub sync pending: initial implementation a875049 is already pushed in
draft PR #6, but final metadata/test/provenance commits be9e108 and326c2b2 failed
to push twice (connection reset, then github.com:443 unreachable). Local final
ZIP c806992829014dc9819998de53c895d2a480bcee053bdf55a599b135ead10625
is the delivery authority for server upload. Do not claim draft PR has the final
package metadata yet. Next publication action is ordinary push of this existing
branch when connectivity returns, then update PR/Issue receipt to the final ZIP.

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
