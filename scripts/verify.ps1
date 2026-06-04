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
  Invoke-Checked python -m py_compile server.py user_manager.py

  $jsFiles = @(
    "tools\diceTool.js",
    "tools\toolManager.js",
    "config\TestRequestConfig.js",
    "config\ConfigManager.js",
    "config\AIPlatformManager.js",
    "js\api-client.js",
    "js\dom-utils.js",
    "js\models\ScenarioModel.js",
    "js\views\ScenarioView.js",
    "js\controllers\ScenarioController.js",
    "js\tabs.js",
    "js\platform-ui.js",
    "js\chat.js",
    "js\auth.js",
    "js\network.js",
    "js\saves.js",
    "js\scenario.js",
    "js\main.js"
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
