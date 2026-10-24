"""Bundle only the template report's sources and referenced assets for Overleaf."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import shutil
import json


def main():
    root=Path(__file__).resolve().parents[1]/'document/Mau'
    project=root.parents[1]
    source_files=[]
    for folder in ['a4_evac','tests','scripts','data/a4']:
        source_files.extend(p for p in (project/folder).rglob('*') if p.is_file()
                            and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.zip'})
    source_files.extend(project/name for name in ['README.md','requirements.txt'])
    benchmark_archive=project/'data/benchmarks/a4_open_ground.zip'
    if benchmark_archive.is_file():
        source_files.append(benchmark_archive)
    for folder in ['outputs/a4_open_ground/benchmark','outputs/a4_open_ground/review_20261024']:
        source_files.extend(p for p in (project/folder).rglob('*.json')
                            if p.name in {'comparison.json','metrics.json','parameters.json','environment.json','complete.json','validation.json','occupancy.json'})
    manifest={p.relative_to(project).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    source_zip=root/'A4_Evac_Source.zip'
    with ZipFile(source_zip,'w',ZIP_DEFLATED) as archive:
        for p in sorted(source_files):archive.write(p,p.relative_to(project).as_posix())
        archive.writestr('source_sha256.json',json.dumps(manifest,indent=2))
    shutil.copy2(source_zip,project/'output/pdf/A4_Evac_Source.zip')
    files=[root/'main.tex',root/'README.md',root/'build.ps1',root/'image/Logo.png']
    files.append(source_zip)
    for folder in ('section','figures','tables','data'):
        files.extend(p for p in (root/folder).rglob('*') if p.is_file())
    if not all(p.is_file() for p in files):
        raise SystemExit('Report inputs missing')
    destination=root/'Bao_cao_N01_Overleaf.zip'
    with ZipFile(destination,'w',ZIP_DEFLATED) as archive:
        for p in sorted(files):
            archive.write(p,p.relative_to(root).as_posix())
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert archive.read('main.tex')==(root/'main.tex').read_bytes()
    print(destination)


if __name__=='__main__':
    main()
