$ErrorActionPreference = "Stop"

$RepositoryRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Command,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
  )

  & $Command @Arguments
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    exit $exitCode
  }
}

function Test-OnlyConftestBaseline {
  $conftest = Get-Item -Path "tests\conftest.py" -ErrorAction SilentlyContinue
  if ($null -eq $conftest) {
    return $false
  }

  $pythonFiles = @(Get-ChildItem -Path "tests" -File -Recurse -Filter "*.py" -ErrorAction SilentlyContinue)
  $testFiles = @(Get-ChildItem -Path "tests" -File -Recurse -Include "test_*.py", "*_test.py" -ErrorAction SilentlyContinue)

  return (
    $pythonFiles.Count -eq 1 -and
    $pythonFiles[0].FullName -eq $conftest.FullName -and
    $testFiles.Count -eq 0
  )
}

Push-Location $RepositoryRoot
try {
  Invoke-Checked python -m py_compile server.py trpg_server\users\manager.py

  if (Test-Path "package.json") {
    Invoke-Checked npm run typecheck
    Invoke-Checked npm run build:frontend
  }

  $frontendFiles = @(
    "frontend\dist\index.html",
    "js\react\main.css"
  )

  foreach ($file in $frontendFiles) {
    if (-not (Test-Path $file)) {
      Write-Error "Missing frontend build output: $file"
      exit 1
    }
  }

  $jsFiles = @(
    "data\tools\diceTool.js",
    "data\tools\toolManager.js",
    "js\config\TestRequestConfig.js",
    "js\config\ConfigManager.js",
    "js\config\AIPlatformManager.js",
    "js\api-client.js",
    "js\dom-utils.js",
    "js\models\ScenarioModel.js",
    "js\views\ScenarioView.js",
    "js\controllers\ScenarioController.js",
    "js\tabs.js",
    "js\platform-ui.js",
    "js\cookie-consent.js",
    "js\generated\templates.js",
    "js\chat.js",
    "js\auth\api.js",
    "js\auth\state.js",
    "js\auth\floating-field.js",
    "js\auth\login-view.js",
    "js\auth\register-view.js",
    "js\auth\profile-dialog.js",
    "js\auth\user-card.js",
    "js\auth\index.js",
    "js\i18n.js",
    "js\network.js",
    "js\rooms.js",
    "js\scenario.js",
    "js\character-sheet.js",
    "js\main.js",
    "js\react\main.js"
  )

  foreach ($file in $jsFiles) {
    Invoke-Checked node --check $file
  }

  python -W error::DeprecationWarning -m pytest -q
  $pytestExitCode = $LASTEXITCODE

  if ($pytestExitCode -eq 0) {
    $global:LASTEXITCODE = 0
  } elseif ($pytestExitCode -eq 5 -and (Test-OnlyConftestBaseline)) {
    $global:LASTEXITCODE = 0
  } else {
    exit $pytestExitCode
  }
} finally {
  Pop-Location
}
