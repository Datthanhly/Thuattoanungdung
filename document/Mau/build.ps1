$ErrorActionPreference = 'Stop'
$mauRoot = $PSScriptRoot
$mauBuild = Join-Path $mauRoot 'build'
$mauPdf = Join-Path $mauRoot '..\..\output\pdf'
New-Item -ItemType Directory -Force -Path $mauBuild, $mauPdf | Out-Null
Push-Location -LiteralPath $mauRoot
try {
    for ($mauPass = 1; $mauPass -le 3; $mauPass++) {
        & xelatex -disable-installer -no-shell-escape -interaction=nonstopmode -halt-on-error -jobname=Bao_cao_N01 -output-directory=build main.tex
        if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX failed: read build/Bao_cao_N01.log' }
    }
    Copy-Item -LiteralPath (Join-Path $mauBuild 'Bao_cao_N01.pdf') -Destination (Join-Path $mauPdf 'Bao_cao_Thuat_toan_ung_dung_N01.pdf') -Force
} finally { Pop-Location }
