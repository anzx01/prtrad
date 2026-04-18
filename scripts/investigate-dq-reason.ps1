param(
    [string]$ApiBaseUrl = "http://localhost:8000",
    [string]$ReasonCode = "REJ_DATA_LEAK_RISK",
    [int]$Limit = 10
)

$ErrorActionPreference = "Stop"

function Format-OptionalValue {
    param(
        [object]$Value
    )

    if ($null -eq $Value -or $Value -eq "") {
        return "-"
    }

    return [string]$Value
}

$escapedReasonCode = [System.Uri]::EscapeDataString($ReasonCode)
$response = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/dq/reasons/$escapedReasonCode?limit=$Limit"

Write-Host "DQ reason focus" -ForegroundColor Cyan
Write-Host ("  reason_code: {0}" -f $response.reason_code)
Write-Host ("  latest_checked_at: {0}" -f (Format-OptionalValue $response.latest_checked_at))
Write-Host ("  total_matches: {0}" -f $response.total_matches)

if ($null -eq $response.samples -or $response.samples.Count -eq 0) {
    Write-Host "No matching samples found." -ForegroundColor Green
    return
}

$index = 1
foreach ($sample in $response.samples) {
    $blockingCodes = if ($sample.blocking_reason_codes) { $sample.blocking_reason_codes -join "," } else { "-" }
    $warningCodes = if ($sample.warning_reason_codes) { $sample.warning_reason_codes -join "," } else { "-" }

    Write-Host ("[{0}] market_id={1} status={2} failure_count={3} score={4}" -f `
        $index, `
        (Format-OptionalValue $sample.market_id), `
        (Format-OptionalValue $sample.status), `
        (Format-OptionalValue $sample.failure_count), `
        (Format-OptionalValue $sample.score))
    Write-Host ("  blocking_reason_codes: {0}" -f $blockingCodes)
    Write-Host ("  warning_reason_codes: {0}" -f $warningCodes)
    Write-Host ("  creation/open/close/resolution: {0} | {1} | {2} | {3}" -f `
        (Format-OptionalValue $sample.timestamps.creation_time), `
        (Format-OptionalValue $sample.timestamps.open_time), `
        (Format-OptionalValue $sample.timestamps.close_time), `
        (Format-OptionalValue $sample.timestamps.resolution_time))
    Write-Host ("  source_updated_at: {0}" -f (Format-OptionalValue $sample.timestamps.source_updated_at))
    Write-Host ("  latest_snapshot_time: {0}" -f (Format-OptionalValue $sample.timestamps.latest_snapshot_time))
    Write-Host ("  previous_snapshot_time: {0}" -f (Format-OptionalValue $sample.timestamps.previous_snapshot_time))

    if ($sample.matching_checks) {
        foreach ($check in $sample.matching_checks) {
            Write-Host ("  check: {0} | {1}" -f (Format-OptionalValue $check.code), (Format-OptionalValue $check.message))
            if ($null -ne $check.details) {
                $detailsJson = $check.details | ConvertTo-Json -Compress -Depth 5
                Write-Host ("    details: {0}" -f $detailsJson)
            }
        }
    }

    $index += 1
}
