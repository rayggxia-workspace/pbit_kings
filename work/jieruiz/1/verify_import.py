"""Verify imported source bytes and reproducible SHA-256 evidence."""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = "b2c0e774f03b5a7ec205f269e2170344df2139bd"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=str(ROOT))


def main():
    names = git("ls-tree", "-r", "--name-only", "-z", SOURCE).decode().split("\0")
    records = []
    for name in filter(None, names):
        source = git("show", SOURCE + ":" + name)
        actual = (ROOT / name).read_bytes()
        normalize = lambda b: b.replace(b"\r\n", b"\n")
        if name == "README.md":
            body = normalize(source).decode("utf-8").splitlines()
            target = normalize(actual).decode("utf-8")
            assert all(line in target for line in body), name
        elif name == ".gitignore":
            assert normalize(source).strip() in normalize(actual), name
        else:
            assert normalize(source) == normalize(actual), name
        records.append({"path": name, "bytes": len(source),
                        "sha256": hashlib.sha256(source).hexdigest()})
    for path in ROOT.rglob("*.py"):
        if ".git" not in path.parts:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    manifest = {"source_repository": "jieruiz/pbit_kings", "source_branch": "pbit_chimera",
                "source_commit": SOURCE, "files": records,
                "hash_basis": "original Git blob bytes; working-tree CRLF may differ"}
    output = Path(__file__).with_name("source_manifest.json")
    if "--record" in sys.argv:
        output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    else:
        assert json.loads(output.read_text(encoding="utf-8")) == manifest
    print("PASS: {} source files verified; all Python files parse; SHA-256 manifest verified.".format(len(records)))
    print("NOT RUN: RTL, VCS, DC, PT, Innovus; migration-only validation.")


if __name__ == "__main__":
    main()
