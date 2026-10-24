$ErrorActionPreference = 'Stop'
$a4ProjectRoot = $PSScriptRoot
$a4DocumentRoot = Join-Path $a4ProjectRoot 'document'
$a4BuildRoot = Join-Path $a4DocumentRoot 'build'
$a4PdfRoot = Join-Path $a4ProjectRoot 'output\pdf'
New-Item -ItemType Directory -Force -Path $a4BuildRoot, $a4PdfRoot | Out-Null
Push-Location -LiteralPath $a4DocumentRoot
try {
    for ($a4Pass = 1; $a4Pass -le 3; $a4Pass++) {
        & xelatex -disable-installer -interaction=nonstopmode -halt-on-error -jobname=A4_Phenikaa_report -output-directory=build main.tex
        if ($LASTEXITCODE -ne 0) {
            throw 'XeLaTeX failed. Read document/build/A4_Phenikaa_report.log.'
        }
    }
    Copy-Item -LiteralPath (Join-Path $a4BuildRoot 'A4_Phenikaa_report.pdf') -Destination (Join-Path $a4PdfRoot 'A4_Phenikaa_report.pdf') -Force
} finally {
    Pop-Location
}
Write-Output (Join-Path $a4PdfRoot 'A4_Phenikaa_report.pdf')
