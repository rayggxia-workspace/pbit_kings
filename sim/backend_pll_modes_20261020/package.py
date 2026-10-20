"""Hash and snapshot scripts only, without PDK or simulation artifacts."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files(root):
    allowed={'.py','.sv','.svh','.tcl','.sh','.txt','.json','.sdf'}
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix not in allowed:
            continue
        rel=p.relative_to(root)
        if any(s in rel.parts for s in ('__pycache__','snapshots','results','logs')):
            continue
        if str(rel).replace('\\','/')=='manifest.json':
            continue
        yield p


def manifest(root):
    return {p.relative_to(root).as_posix():digest(p) for p in files(root)}


def main():
    root=Path(sys.argv[2]).resolve()
    data=manifest(root)
    if sys.argv[1]=='snapshot':
        base=root/'snapshots'
        base.mkdir(exist_ok=True)
        target=Path(tempfile.mkdtemp(prefix='submission.',dir=str(base)))
        for name in data:
            dst=target/name
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(str(root/name),str(dst))
        (target/'manifest.json').write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
        print(target)
    elif sys.argv[1]=='zip':
        target=Path(sys.argv[3])
        with zipfile.ZipFile(str(target),'w',zipfile.ZIP_DEFLATED) as z:
            for name in data:
                z.write(str(root/name),root.name+'/'+name)
            z.writestr(root.name+'/manifest.json',json.dumps(data,indent=2,sort_keys=True)+'\n')
        print('ZIP={} files={} SHA256={}'.format(target,len(data),digest(target)))
    else:
        raise ValueError('snapshot|zip')


if __name__=='__main__':
    main()
