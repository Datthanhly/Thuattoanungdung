"""Package editable report sources, figures and measured data for Overleaf."""

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    root = Path(__file__).resolve().parents[1] / "document"
    files = [root / name for name in ("main.tex", "README.md", "measured_results.json")]
    for folder in ("chapters", "tables", "figures"):
        files.extend(p for p in (root / folder).rglob("*") if p.is_file())
    if any(not p.is_file() for p in files):
        raise SystemExit("Generate the report before packaging it.")
    output = root / "A4_Phenikaa_Overleaf.zip"
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for p in sorted(files):
            archive.write(p, p.relative_to(root).as_posix())
    print(output)


if __name__ == "__main__":
    main()
