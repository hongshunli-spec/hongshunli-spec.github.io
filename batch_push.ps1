# Batch push gh-pages: split 103 family photo albums into 8 batches, commit+push each
Set-Location D:\myblog\public
$ErrorActionPreference = "Continue"

$dirs = @(Get-ChildItem "album\family_photos_tmp" -Directory -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name | Sort-Object)
if ($dirs.Count -eq 0) {
  $dirs = @(Get-ChildItem "album\家庭照片" -Directory | Select-Object -ExpandProperty Name | Sort-Object)
}
$total = $dirs.Count
$batches = 8
$batchSize = [math]::Ceiling($total / $batches)
Write-Output "Total folders: $total, batch size ~$batchSize, batches: $batches"
$batchNum = 0
$start = 0
$fail = $false

while ($start -lt $total) {
  $batchNum++
  $end = [math]::Min($start + $batchSize - 1, $total - 1)
  $slice = $dirs[$start..$end]
  Write-Output ""
  Write-Output "===== Batch $batchNum/$batches (folders $($start+1)-$($end+1), $($slice.Count) items) ====="
  
  $paths = $slice | ForEach-Object { "album/家庭照片/$_" }
  git add -- @paths 2>&1 | Out-Null
  if ($LASTEXITCODE -ne 0) { Write-Output "[FAIL] add failed batch $batchNum"; $fail = $true; break }
  
  if ($end -eq ($total - 1)) {
    git add -- "albums/index.html" 2>&1 | Out-Null
    Write-Output "(includes albums index.html)"
  }
  
  $stagedCount = (git diff --cached --name-only 2>&1 | Measure-Object).Count
  Write-Output "Staged files this batch: $stagedCount"
  if ($stagedCount -eq 0) { Write-Output "[SKIP] no change"; $start = $end + 1; continue }
  
  git commit -m "family photos album batch $batchNum/$batches" 2>&1 | Select-Object -Last 2
  if ($LASTEXITCODE -ne 0) { Write-Output "[FAIL] commit failed batch $batchNum"; $fail = $true; break }
  
  Write-Output "Pushing batch $batchNum..."
  git push origin gh-pages 2>&1 | Select-Object -Last 3
  $pushCode = $LASTEXITCODE
  if ($pushCode -ne 0) {
    Write-Output "[FAIL] push failed batch $batchNum (code $pushCode)"
    $fail = $true
    break
  }
  Write-Output "Batch $batchNum done OK"
  $start = $end + 1
}

if ($fail) {
  Write-Output "===== FAILED, stopped at batch $batchNum ====="
} else {
  Write-Output "===== ALL $batchNum batches pushed ====="
}
Write-Output "Final HEAD: $(git log --oneline -1 2>&1)"
