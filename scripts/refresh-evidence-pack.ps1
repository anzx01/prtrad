param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$ActorId = "console_autopilot",
  [string]$StrategyVersion = "baseline-v1",
  [int]$WindowDays = 30,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$logsDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) {
  New-Item -ItemType Directory -Path $logsDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$logFile = Join-Path $logsDir "refresh-evidence-pack-$stamp.log"

function Write-StepLog {
  param(
    [string]$Level,
    [string]$Message
  )

  $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level.ToUpperInvariant(), $Message
  $color = switch ($Level.ToLowerInvariant()) {
    "good" { "Green" }
    "warn" { "Yellow" }
    "bad" { "Red" }
    default { "Cyan" }
  }

  Write-Host $line -ForegroundColor $color
  Add-Content -Path $logFile -Value $line -Encoding UTF8
}

function Get-ErrorMessage {
  param(
    [Parameter(ValueFromPipeline = $true)]
    $ErrorRecord
  )

  if ($null -eq $ErrorRecord) {
    return "Unknown error"
  }

  if ($ErrorRecord.ErrorDetails -and $ErrorRecord.ErrorDetails.Message) {
    return [string]$ErrorRecord.ErrorDetails.Message
  }

  if ($ErrorRecord.Exception -and $ErrorRecord.Exception.Message) {
    return [string]$ErrorRecord.Exception.Message
  }

  return [string]$ErrorRecord
}

function Invoke-ApiPost {
  param(
    [string]$Path,
    $Body
  )

  $uri = "{0}{1}" -f $BaseUrl.TrimEnd('/'), $Path
  $json = if ($null -ne $Body) { $Body | ConvertTo-Json -Depth 8 -Compress } else { $null }

  if ($DryRun) {
    Write-StepLog "info" ("DRY RUN POST {0}{1}" -f $uri, $(if ($json) { " body=$json" } else { "" }))
    return $null
  }

  if ($null -eq $Body) {
    return Invoke-RestMethod -Method Post -Uri $uri
  }

  return Invoke-RestMethod -Method Post -Uri $uri -ContentType "application/json" -Body $json
}

function Invoke-Step {
  param(
    [string]$Label,
    [string]$Path,
    $Body,
    [int]$Attempt = 1
  )

  Write-StepLog "info" "Running: $Label"

  try {
    Invoke-ApiPost -Path $Path -Body $Body | Out-Null
    Write-StepLog "good" "Completed: $Label"
  }
  catch {
    $message = Get-ErrorMessage $_
    if ($Attempt -lt 2 -and $message.ToLowerInvariant().Contains("database is locked")) {
      Write-StepLog "warn" "$Label hit database lock, retrying in 0.8s"
      Start-Sleep -Milliseconds 800
      Invoke-Step -Label $Label -Path $Path -Body $Body -Attempt ($Attempt + 1)
      return
    }

    Write-StepLog "bad" "$Label failed: $message"
    throw
  }
}

$steps = @(
  @{ Label = "Recompute risk exposures"; Path = "/risk/exposures/compute"; Body = $null },
  @{ Label = "Recompute long-window calibration"; Path = "/calibration/recompute-all?window_type=long"; Body = $null },
  @{
    Label = "Run backtest"
    Path  = "/backtests/run"
    Body  = @{
      run_name         = "autopilot-backtest-$stamp"
      window_days      = $WindowDays
      executed_by      = $ActorId
      strategy_version = $StrategyVersion
    }
  },
  @{
    Label = "Run shadow check"
    Path  = "/shadow/execute"
    Body  = @{
      run_name    = "autopilot-shadow-$stamp"
      executed_by = $ActorId
    }
  },
  @{
    Label = "Generate daily report"
    Path  = "/reports/generate"
    Body  = @{
      report_type  = "daily_summary"
      generated_by = $ActorId
    }
  },
  @{
    Label = "Generate weekly report"
    Path  = "/reports/generate"
    Body  = @{
      report_type  = "weekly_summary"
      generated_by = $ActorId
    }
  }
)

foreach ($stage in @("M4", "M5", "M6")) {
  $steps += @{
    Label = "Generate $stage stage review"
    Path  = "/reports/generate"
    Body  = @{
      report_type  = "stage_review"
      generated_by = $ActorId
      stage_name   = $stage
    }
  }
}

Write-StepLog "info" "Starting full evidence refresh. Log file: $logFile"

if (-not $DryRun) {
  try {
    $healthUri = "{0}/health" -f $BaseUrl.TrimEnd('/')
    Invoke-RestMethod -Method Get -Uri $healthUri | Out-Null
    Write-StepLog "good" "API health check passed: $healthUri"
  }
  catch {
    $message = Get-ErrorMessage $_
    Write-StepLog "bad" "API health check failed: $message"
    throw
  }
}

foreach ($step in $steps) {
  Invoke-Step -Label $step.Label -Path $step.Path -Body $step.Body
  if (-not $DryRun) {
    Start-Sleep -Milliseconds 160
  }
}

Write-StepLog "good" $(if ($DryRun) { "DRY RUN completed. No API calls were sent." } else { "Full evidence refresh completed." })
