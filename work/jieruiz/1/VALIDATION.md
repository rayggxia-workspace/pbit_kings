# Validation record

Date: 2026-10-17 Asia/Shanghai. Source commit: b2c0e774f03b5a7ec205f269e2170344df2139bd.

- `python scripts/check_project.py`: PASS, management schema 1.
- `python work/jieruiz/1/verify_import.py --record`: PASS, 182 source files checked, SHA-256 manifest generated, Python syntax parsed.
- `bash -n` on the 16 tracked shell scripts: PASS; scripts not executed.
- `git diff --cached --check source/pbit_chimera`: PASS for migration additions. The full import diff against template main reports existing source whitespace/CRLF warnings; historical source was deliberately not reformatted.
- Source-history blob size audit: largest 1,504,001 bytes, generated test fixture.
- Basic private-key/token/vendor-confidential pattern scan on source head: no matches. This is a bounded check, not a formal security audit.
- No new VCS/DC/PT/Innovus or FPGA testing. Historical reports are not presented as current passes.

Only source README gets a workspace entry and source .gitignore gets safety patterns;
all other imported source files must retain their original Git blobs. No local
untracked EDA directories were staged. Full source history is preserved as a merge parent.

Integration limits: management registry currently enforces private-only projects;
this public project's registration requires maintainer handling (management Issue #3).
GitHub GraphQL returned INSUFFICIENT_SCOPES for Projects; current credential lacks
read:project. Board state is unverified and synchronization pending. No scopes,
collaborators, repository protections or organization policies were changed.
