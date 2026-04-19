param(
  [ValidateSet("state", "start-paper", "start-live", "stop", "execute-next", "orders")]
  [string]$Action = "state",
  [string]$BaseUrl = "http://localhost:8000",
  [string]$ActorId = "console_autopilot",
  [string]$Reason = "控制台手动停止"
)

$ErrorActionPreference = "Stop"

function Invoke-JsonRequest {
  param(
    [string]$Method,
    [string]$Path,
    $Body = $null
  )

  $uri = "{0}{1}" -f $BaseUrl.TrimEnd('/'), $Path
  if ($null -eq $Body) {
    return Invoke-RestMethod -Method $Method -Uri $uri -Headers @{ Accept = "application/json" }
  }

  return Invoke-RestMethod `
    -Method $Method `
    -Uri $uri `
    -Headers @{ Accept = "application/json" } `
    -ContentType "application/json" `
    -Body ($Body | ConvertTo-Json -Depth 8 -Compress)
}

switch ($Action) {
  "state" {
    $result = Invoke-JsonRequest -Method "GET" -Path "/trading/state"
  }
  "start-paper" {
    $result = Invoke-JsonRequest -Method "POST" -Path "/trading/start" -Body @{
      mode     = "paper"
      actor_id = $ActorId
    }
  }
  "start-live" {
    $result = Invoke-JsonRequest -Method "POST" -Path "/trading/start" -Body @{
      mode     = "live"
      actor_id = $ActorId
    }
  }
  "stop" {
    $result = Invoke-JsonRequest -Method "POST" -Path "/trading/stop" -Body @{
      actor_id = $ActorId
      reason   = $Reason
    }
  }
  "execute-next" {
    $result = Invoke-JsonRequest -Method "POST" -Path "/trading/execute-next" -Body @{
      actor_id = $ActorId
    }
  }
  "orders" {
    $result = Invoke-JsonRequest -Method "GET" -Path "/trading/orders?limit=10"
  }
}

$result | ConvertTo-Json -Depth 8
