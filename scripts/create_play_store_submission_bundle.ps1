param(
    [string]$OutputDir = "play-store-package"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$bundleRoot = Join-Path $repoRoot $OutputDir
$stagingDir = Join-Path $bundleRoot "staging_$timestamp"
$zipPath = Join-Path $bundleRoot "promanage-play-store-materials-$timestamp.zip"

New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stagingDir "frontend/public") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $stagingDir "frontend/src/pages") | Out-Null

$filesToCopy = @(
    "PLAY_STORE_READINESS.md",
    "README.md",
    "frontend/package.json",
    "frontend/capacitor.config.ts",
    "frontend/index.html",
    "frontend/public/manifest.json",
    "frontend/public/icon.png",
    "frontend/play-store-assets/README.md",
    "frontend/src/pages/PrivacyPolicy.tsx",
    "frontend/src/pages/TermsOfService.tsx"
)

foreach ($relativePath in $filesToCopy) {
    $sourcePath = Join-Path $repoRoot $relativePath
    if (Test-Path $sourcePath) {
        $destinationPath = Join-Path $stagingDir $relativePath
        $destinationParent = Split-Path -Parent $destinationPath
        New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
        Copy-Item -Path $sourcePath -Destination $destinationPath -Force
    }
}

$androidProjectPath = Join-Path $repoRoot "frontend/android"
if (Test-Path $androidProjectPath) {
    Copy-Item -Path $androidProjectPath -Destination (Join-Path $stagingDir "frontend") -Recurse -Force
}

$reportPath = Join-Path $stagingDir "PLAY_STORE_BUNDLE_REPORT.txt"
@(
    "ProManage Play Store Materials Bundle",
    "Generated: $(Get-Date -Format s)",
    "",
    "Included files:",
    "- PLAY_STORE_READINESS.md",
    "- README.md",
    "- frontend/package.json",
    "- frontend/capacitor.config.ts",
    "- frontend/index.html",
    "- frontend/public/manifest.json",
    "- frontend/public/icon.png",
    "- frontend/play-store-assets/README.md",
    "- frontend/src/pages/PrivacyPolicy.tsx",
    "- frontend/src/pages/TermsOfService.tsx",
    "- frontend/android/ (included when present)",
    "",
    "Known missing items for Google Play submission:",
    "- Signed release .aab",
    "- Release keystore and signing config",
    "- Play screenshots",
    "- 1024x500 feature graphic",
    "- Confirmed production privacy policy URL",
    "- Confirmed account deletion URL/flow",
    "- Data safety form answers",
    "- Content rating answers"
) | Set-Content -Path $reportPath -Encoding UTF8

if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath -Force

Write-Host "Created Play Store materials bundle: $zipPath"