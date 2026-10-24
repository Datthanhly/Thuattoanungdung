"""Restore the archived measured datasets, without overwriting different files."""
from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'data/benchmarks/a4_open_ground.zip'
DESTINATION = ROOT/'outputs/a4_open_ground'


def main():
    destination = DESTINATION.resolve()
    with ZipFile(ARCHIVE) as archive:
        manifest = json.loads(archive.read('manifest_sha256.json'))
        entries = [i for i in archive.infolist() if not i.is_dir() and i.filename != 'manifest_sha256.json']
        assert set(manifest) == {i.filename for i in entries}
        planned = []
        # Check every destination and digest before writing anything.
        for entry in entries:
            parts = PurePosixPath(entry.filename)
            if parts.is_absolute() or '..' in parts.parts or '\\' in entry.filename:
                raise ValueError(f'Unsafe archive member: {entry.filename}')
            target = (destination/entry.filename).resolve()
            if not target.is_relative_to(destination):
                raise ValueError(f'Archive member outside results directory: {entry.filename}')
            expected = manifest[entry.filename]
            with archive.open(entry) as source:
                if hashlib.file_digest(source, 'sha256').hexdigest() != expected:
                    raise ValueError(f'Archive checksum mismatch: {entry.filename}')
            if target.exists():
                with target.open('rb') as source:
                    if hashlib.file_digest(source, 'sha256').hexdigest() != expected:
                        raise ValueError(f'Existing file differs, kept unchanged: {target}')
            else:
                planned.append((entry, target))
        for entry, target in planned:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
    print(f'Verified {len(entries)} files; restored {len(planned)} files to {destination}')


if __name__ == '__main__':
    main()
