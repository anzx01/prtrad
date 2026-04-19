param(
    [string]$PythonExecutable = ".\.venv\Scripts\python.exe",
    [int]$MarketLimit = 0,
    [string]$ReasonCode = "REJ_DATA_INCOMPLETE",
    [int]$ReasonLimit = 10
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$logsDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$logFile = Join-Path $logsDir "dq-baseline-$stamp.log"
$pythonPath = if ([System.IO.Path]::IsPathRooted($PythonExecutable)) {
    $PythonExecutable
} else {
    Join-Path $repoRoot $PythonExecutable
}
$scriptPath = Join-Path $repoRoot "scripts\run_dq_baseline.py"

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

function Get-OptionalCount {
    param(
        [object]$Object,
        [string]$Name
    )

    if ($null -eq $Object) {
        return 0
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property -or $null -eq $property.Value) {
        return 0
    }

    return [int]$property.Value
}

if (-not (Test-Path $pythonPath)) {
    throw "Python executable not found: $pythonPath"
}

$pythonArgs = @($scriptPath, "--reason-code", $ReasonCode, "--reason-limit", "$ReasonLimit")
if ($MarketLimit -gt 0) {
    $pythonArgs += @("--market-limit", "$MarketLimit")
}

$stderrFile = [System.IO.Path]::GetTempFileName()
try {
    Write-StepLog "info" "Running synchronous DQ baseline. Log file: $logFile"
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $jsonOutput = & $pythonPath @pythonArgs 2> $stderrFile
    $ErrorActionPreference = $previousErrorActionPreference
    $exitCode = $LASTEXITCODE
    $stderrText = if (Test-Path $stderrFile) { Get-Content $stderrFile -Raw -ErrorAction SilentlyContinue } else { "" }

    if ($exitCode -ne 0) {
        if ($stderrText) {
            Add-Content -Path $logFile -Value $stderrText -Encoding UTF8
        }
        throw ("DQ baseline helper failed with exit code {0}. {1}" -f $exitCode, $stderrText.Trim())
    }

    $jsonText = ($jsonOutput | Out-String).Trim()
    if (-not $jsonText) {
        throw "DQ baseline helper returned empty output."
    }

    Add-Content -Path $logFile -Value $jsonText -Encoding UTF8
    $result = $jsonText | ConvertFrom-Json

    Write-StepLog "good" ("Snapshot capture completed: selected={0}, created={1}, source_payload_fallback={2}" -f `
        (Get-OptionalCount -Object $result.capture -Name "selected_markets"), `
        (Get-OptionalCount -Object $result.capture -Name "created"), `
        (Get-OptionalCount -Object $result.capture -Name "created_from_source_payload"))
    Write-StepLog "good" ("DQ run completed: selected={0}, created={1}, pass={2}, warn={3}, fail={4}" -f `
        (Get-OptionalCount -Object $result.dq -Name "selected_markets"), `
        (Get-OptionalCount -Object $result.dq -Name "created"), `
        (Get-OptionalCount -Object $result.dq -Name "pass"), `
        (Get-OptionalCount -Object $result.dq -Name "warn"), `
        (Get-OptionalCount -Object $result.dq -Name "fail"))
    Write-StepLog "info" ("Batch summary: checked_at={0}, latest_snapshot_time={1}, freshness={2}, snapshot_age_seconds={3}" -f `
        $result.summary.checked_at, `
        $result.summary.latest_snapshot_time, `
        $result.summary.freshness_status, `
        $result.summary.snapshot_age_seconds)

    if ($result.summary.top_blocking_reasons) {
        Write-StepLog "info" "Top blocking reasons"
        foreach ($reason in $result.summary.top_blocking_reasons) {
            Write-StepLog "info" ("  {0} = {1}" -f $reason.reason_code, $reason.count)
        }
    }

    if ($result.reason_focus) {
        Write-StepLog "info" ("Reason focus: {0}, matches={1}" -f $result.reason_focus.reason_code, $result.reason_focus.total_matches)
        if ($result.reason_focus.check_counts) {
            Write-StepLog "info" "Matching check counts"
            foreach ($item in $result.reason_focus.check_counts) {
                Write-StepLog "info" ("  {0} = {1}" -f $item.code, $item.count)
            }
        }

        if ($result.reason_focus.missing_field_counts) {
            Write-StepLog "info" "Missing field counts"
            foreach ($item in $result.reason_focus.missing_field_counts) {
                $checkCodes = if ($item.check_codes) { $item.check_codes -join "," } else { "-" }
                Write-StepLog "info" ("  {0} = {1} (checks={2})" -f $item.field_name, $item.count, $checkCodes)
            }
        }
    }

    if ($result.summary.freshness_status -ne "fresh") {
        throw ("DQ baseline freshness check failed: expected fresh, got {0}" -f $result.summary.freshness_status)
    }

    Write-StepLog "good" "DQ baseline completed."
}
finally {
    $ErrorActionPreference = "Stop"
    if (Test-Path $stderrFile) {
        Remove-Item -LiteralPath $stderrFile -Force
    }
}
