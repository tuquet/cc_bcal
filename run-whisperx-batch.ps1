param(
  [string]$AudioFolder = "episodes/1.tam-nhu-mat-ho/audio",
  [string]$Pattern = "*.mp3",
  [switch]$RequireGpu,
  [switch]$Force
)

function Write-Log($s){ Write-Host "[run-whisperx-batch] $s" }

$repoRoot = (Get-Location).Path
$hostCacheRoot = Join-Path $env:USERPROFILE ".cache"

if (-not (Test-Path $hostCacheRoot)) {
  Write-Log "Creating host cache root at $hostCacheRoot"
  New-Item -ItemType Directory -Path $hostCacheRoot -Force | Out-Null
}

$absAudioFolder = Join-Path $repoRoot $AudioFolder
if (-not (Test-Path $absAudioFolder)) { Write-Error "Audio folder not found: $absAudioFolder"; exit 2 }

$files = Get-ChildItem -Path $absAudioFolder -Filter $Pattern | Sort-Object Name
if ($files.Count -eq 0) { Write-Log "No files matching $Pattern in $absAudioFolder"; exit 0 }

$gpuFlag = if ($RequireGpu) { '--gpus all' } else { '' }
$requireArg = if ($RequireGpu) { '--require-gpu' } else { '' }

foreach ($f in $files) {
  $mp3Path = $f.FullName
  $base = [System.IO.Path]::GetFileNameWithoutExtension($f.Name)
  $srtPath = Join-Path $f.DirectoryName ($base + '.srt')
  if ((Test-Path $srtPath) -and (-not $Force)) {
    Write-Log "Skipping existing SRT: $srtPath (use -Force to overwrite)"
    continue
  }

  Write-Log "Processing: $mp3Path -> $srtPath"

  # container paths
  $containerAudio = "/workspace/" + (Resolve-Path $mp3Path).Path.Substring($repoRoot.Length+1).Replace('\','/')
  $tmpJson = "/workspace/.out-whisperx-$base.json"

  $cmd = "docker run --rm $gpuFlag -v `"$repoRoot`:/workspace`" -v `"$hostCacheRoot`:/root/.cache`" -e HF_HOME=/root/.cache/huggingface -e TRANSFORMERS_CACHE=/root/.cache/huggingface -e TORCH_HOME=/root/.cache/torch cc_bcal-whisperx --audio $containerAudio --output $tmpJson $requireArg"
  Write-Log "Running container..."
  Write-Log $cmd
  $rv = Invoke-Expression $cmd
  if ($LASTEXITCODE -ne 0) { Write-Error "Container failed for $mp3Path (exit $LASTEXITCODE)"; continue }

  # Convert JSON -> SRT using Node helper
  $hostTmpJson = Join-Path $repoRoot ('.out-whisperx-' + $base + '.json')
  if (-not (Test-Path $hostTmpJson)) { Write-Error "Expected JSON not found: $hostTmpJson"; continue }

  Write-Log "Converting JSON to SRT..."
  & node scripts/write-srt-from-outjson.mjs $hostTmpJson $f.DirectoryName $base
  if ($LASTEXITCODE -ne 0) { Write-Error "Failed to write SRT for $mp3Path"; continue }

  # cleanup tmp json
  Remove-Item -Force $hostTmpJson -ErrorAction SilentlyContinue
  Write-Log "Finished: $srtPath"
}

Write-Log "Batch finished."
