param(
    [string]$ApiBaseUrl = "http://localhost:8000",
    [int]$Limit = 5
)

$ErrorActionPreference = "Stop"

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

$response = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/dq/summary?limit=$Limit"
$summary = $response.summary

if ($null -eq $summary) {
    throw "DQ summary payload missing"
}

$statusDistribution = $summary.status_distribution
$passCount = Get-OptionalCount -Object $statusDistribution -Name "pass"
$warnCount = Get-OptionalCount -Object $statusDistribution -Name "warn"
$failCount = Get-OptionalCount -Object $statusDistribution -Name "fail"

Write-Host "DQ health summary" -ForegroundColor Cyan
Write-Host ("  freshness_status: {0}" -f $summary.freshness_status)
Write-Host ("  snapshot_age_seconds: {0}" -f $summary.snapshot_age_seconds)
Write-Host ("  status_distribution: pass={0}, warn={1}, fail={2}" -f $passCount, $warnCount, $failCount)

$capture = $summary.latest_snapshot_capture
if ($null -ne $capture) {
    Write-Host "Latest snapshot capture diagnostics" -ForegroundColor Cyan
    Write-Host ("  triggered_at: {0}" -f $capture.triggered_at)
    Write-Host ("  created: {0}" -f $capture.created)
    Write-Host ("  book_fetch_failed_tokens: {0}" -f (Get-OptionalCount -Object $capture -Name "book_fetch_failed_tokens"))
    Write-Host ("  created_from_source_payload: {0}" -f (Get-OptionalCount -Object $capture -Name "created_from_source_payload"))
    Write-Host ("  skipped_missing_order_books: {0}" -f (Get-OptionalCount -Object $capture -Name "skipped_missing_order_books"))
}

if ($summary.freshness_status -ne "fresh") {
    throw ("DQ freshness check failed: expected fresh, got {0}" -f $summary.freshness_status)
}

Write-Host "DQ health check passed." -ForegroundColor Green
