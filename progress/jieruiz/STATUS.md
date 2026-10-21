# jieruiz progress

## 2026-10-21 Completed v3 Switch Result 38263376

Actual WC/10ps v3 continuation completed all five epochs:300->150->25 bypass->
300->same300 APPLY. All36 frozen package identities and recorded build/SDF
provenance checked.20 functional checks,25 PLL pin UART,10 core pin UART,
5x100-word known snapshots/two-node2-sweep results PASS. Bulk array config still
uses accelerated bus; not full-UART-only or full3200-node workload/signoff.
VCS exit0; final job failure was our WIDTH scalar-limit parser. Local fix retains
all594 raw events:590 WIDTH in definite reset,3 RX setuphold+1 reset recrem in
existing exact profiles;0 additional outside-reset events. No new waiver.
BP deassertion while reference high truncated root high to620ps, local sinks
550..590ps (10..70ps short); distinct from prior inf/one-tick model stop defect.
Function recovered, but vendor safe BP-switch specification and backend WIDTH
review remain required. No new EDA, no DUT/IP edits, no rebuilt v3 ZIP. Original
archive preserved. Read-only re-audit and Chinese report in
result_pipeline/PLL_38263376_REVIEW_20261021 outside this checkout; raw files not
published. Tests/publication receipt recorded in work/jieruiz/5/HANDOFF.md.

## 2026-10-21 v2 Results and v3 Switch Continuation

Issue5 / draftPR6, same branch/checkout. Actual38230453 v2 identities all33 match;
cold25 bypass pin UART/compute/full snapshot PASS. Legacy30ps hold reproduces
beside bus acquisition, safe/no-injection0 raw timing; historical VCS string
padding caused false scope failure, now re-audited with57 exact input hashes.
Independent original1ps and matched10ps PLL models reproduce inf/runt behavior.
errors18 checks complete,4540 MAC E reset-window events retained; no extra active
events, no timing-signoff claim. switch stopped due checker using target25 before
APPLY instead of still-active150, not an observed chip BP switching failure.

Local v3 fixes active-vs-target guard and explicit string serialization, adds
immutable historical re-audit/continuation. 26 tests PASS, actual old archive
re-audit succeeds without EDA or raw-byte edits. User should submit only WC switch
with PREVIOUS_RESULT pointing at38230453; completed cases/model probes not rerun.
New VCS switch evidence pending; no DUT/SDF/vendor behavior patch, no power rerun.
Local source/package/publication states in DELIVERY.json and work/jieruiz/5/HANDOFF.md.
2026-10-21 receipt: ordinary v3 Git push failed with connection reset; local ZIP
ready. Issue/PR v3 receipts updated through API asjieruiz; remote source stilla875049,
draft/unmerged/in_review. Board target absent,0 visible items; sync pending.

## 2026-10-20 PLL v2 Suspect Diagnostics

Issue5 / draft PR6, same task branch and sparse checkout. User requested scripts
for every observed suspect. Remote v1 job38227554 reviewed: exact final29-file
source manifest, native SDF100%; 300/150 functional epochs and18 error checks
complete. Bypass abort is the project-written symmetric-half-period guard;
20.20/19.80ns still forms40ns. One extra30ps req_addr[3] hold event may be Q-feedback
disturbed by bus force; physical CK isCTS_8 vs write-launchCTS_5. Not yet waived.
82 reset-window MAC/RNG events and vendor inf/10ps CKTST pulse remain for review.

Local v2 implements period/duty/reference-edge diagnostics; legacy/safe/no-bus
controls with CK/D/Q/injection trace; native1ps and matched10ps unchanged-vendor
stop probes; full3200-bit snapshot X check after each complete mode. No DUT/SDF
patch, no new waiver, no power rerun. 21 local tests PASS including actual-host,
handoff-slot and vendor-port elaboration; no new real-netlist VCS execution.
New ZIP/provenance recorded in DELIVERY.json after final checks. Publication
state and remaining next steps are in work/jieruiz/5/HANDOFF.md. Remote v2 pending:
ordinary Git push failed with connection reset; local validated ZIP is ready.
Do not reuse v1 build; source identity intentionally changes. Existing raw result
archives kept read-only; no redundant full checkout or large extraction created.

## 2026-10-20 PLL Mode Coverage

Owner: jieruiz. Issue: https://github.com/rayggxia-workspace/pbit_kings/issues/5.
Branch: task/5-pll-mode-validation; base task/3-reset-recovery-diagnostic,
05571587a8895d644f73c767bda02fa146ecedca (PR #4 dependency, not merged).
Sparse checkout: tmp/pbit-pll-issue5-20261020; no new full clone/helper checkout.
Stage: scripts pushed for review; new real-netlist VCS mode runs pending.
Final sync caveat: PR currently has initial a875049 implementation; final local
metadata/test/provenance updates could not push after two github.com network
failures. Use the final local ZIP in DELIVERY.json; ordinary push/receipt update
is still pending and is not a blocker for uploading that ZIP to the HPC server.
PR: https://github.com/rayggxia-workspace/pbit_kings/pull/6 (draft, not merged).
Validated script commit: be9e1088e28e811a0f11f6d4d85556949a73b2cd;
final ZIP/provenance in work/jieruiz/5/DELIVERY.json.
Scope: sim/backend_pll_modes_20261020 and task docs; no DUT/PDK/vendor behavior edits.
Validation: 15 unittest PASS, including XSim actual-host three-baud/back-to-back
codec tests, full new top declaration-stub elaboration, Icarus clock guard negative
tests, Python 3.6 grammar and WC/BC setup selection. Two Bash syntax checks PASS.
No new real-netlist VCS, power, analog-lock or STA signoff result locally.
Next: user submits WC mode suite, then optional separate BC suite; inspect modes,
real versus injected transport, raw reset/active timing, UART and clock evidence.
Prior recovery job38219776 is downloaded and targeted functional recovery passed;
PLL model inf warnings/reset-only events remain review items. Do not rerun that
job or claim it is unexecuted based on the preserved older status below.
Registry/board: existing public-registration policy pending; no configured target
board; fresh Issue #5 query found 0 visible projectItems. Synchronization pending
until a real board is designated. Issue status: in_review, not done.
Handoff: work/jieruiz/5/HANDOFF.md. Reviewer pending; Issue stays open for results.

## 2026-10-20 Recovery Diagnostic

Owner: jieruiz. Repository: rayggxia-workspace/pbit_kings.
Issue: https://github.com/rayggxia-workspace/pbit_kings/issues/3
Branch: task/3-reset-recovery-diagnostic.
Base: task/1-import-chimera at 16bc36c264d5a15ecac2f3c38031b767e2231d21;
dependent PR #2 remains open, not merged.
Checkout: tmp/pbit-reset-issue3-20261020 (sparse, reused for this task only).
Stage: diagnostic scripts pushed for review; remote VCS evidence pending.
PR: https://github.com/rayggxia-workspace/pbit_kings/pull/4 (draft, not merged).
Verified script commit: b4576399b0b1d17f8fa59f521ca0b6bb90e68435.
Scope: sim/backend_recovery_diag_20261020; no RTL/netlist/vendor-model changes.
Validation: 13 local tests PASS, including original 1,589-event log parser,
monitor execution and stub-based top syntax; 2 Bash syntax checks PASS;
management schema PASS. No commercial EDA run on this machine.
Evidence: original job 38215256; raw licensed inputs/results remain in existing
authorized local/server storage. No raw simulation logs or PDK uploaded.
Next: user submits recovery-only all-phases job, downloads the small archive;
review reset-only events, refill, clock quality and complete snapshot comparison.
Board: 2026-10-20 readback found 0 visible projectItems for Issue #3;
no board.json/target board configured, so adding/synchronizing remains pending.
Registration: existing public-project registration issue remains pending.
Handoff: work/jieruiz/3/HANDOFF.md. Do not close Issue #3 before remote evidence/review.

## Import History (Preserved)

Updated: 2026-10-17 Asia/Shanghai. Owner: jieruiz.
Issue: https://github.com/rayggxia-workspace/pbit_kings/issues/1
Branch: task/1-import-chimera. Target/base: rayggxia-workspace/pbit_kings/main.
Independent checkout: pbit_kings_workspace; original mixed checkout preserved.
Source: b2c0e774f03b5a7ec205f269e2170344df2139bd.

Stage: in_review. Branch pushed; [PR #2](https://github.com/rayggxia-workspace/pbit_kings/pull/2) open, not merged.
Import merge commit: de7e6f6 (full commit and current head visible in PR).
Scope: tracked Chimera source/history and collaboration setup; no RTL changes.
Validation: management schema PASS; 182 source files and SHA-256 PASS; Python AST PASS; 16 shell syntax checks PASS; migration-only whitespace check PASS. Existing imported source has historical whitespace warnings. No EDA tests in this task.
Registration: pending, tracked by management-hub Issue #3. Registry validator only accepts private projects; user explicitly chose public. No registry change or policy bypass performed.
Board: unverified, synchronization pending; GraphQL lacks read:project scope.
Next: reviewer (to be designated) reviews PR; management maintainer confirms public registration support and authorized board synchronization. Do not close Issue #1 before acceptance.
Handoff: [work/jieruiz/1/HANDOFF.md](../../work/jieruiz/1/HANDOFF.md).
