param(
  [string]$AudioPath = "episodes/1.tam-nhu-mat-ho/audio/voiceover.mp3",
  [string]$Output = "/workspace/out-whisperx.json",
  [switch]$RequireGpu
)

# Create a host cache directory for Hugging Face models (~/.cache/huggingface on Windows: %USERPROFILE%\.cache\huggingface)
$hostCacheRoot = Join-Path $env:USERPROFILE ".cache"
if (-not (Test-Path $hostCacheRoot)) {
    Write-Host "Creating host cache root at $hostCacheRoot"
    New-Item -ItemType Directory -Path $hostCacheRoot -Force | Out-Null
}

Write-Host "Using host cache root: $hostCacheRoot (will be mounted into container /root/.cache)"

$pwdPath = (Get-Location).Path

# Ensure audio path inside container; if user passed a host-relative path, prefix with /workspace/
if ($AudioPath -notmatch '^(/|[A-Za-z]:)') {
    $containerAudio = "/workspace/$AudioPath"
} else {
    # If an absolute Windows path was provided, convert it to a container path by mounting parent dir manually
    $containerAudio = $AudioPath
}

$gpuFlag = if ($RequireGpu) { '--gpus all' } else { '' }
$requireArg = if ($RequireGpu) { '--require-gpu' } else { '' }

Write-Host "Running container (mounting repo and caches: /workspace, /root/.cache/huggingface, /root/.cache/torch)"
Write-Host "Repository mount: $pwdPath -> /workspace"
Write-Host "Audio inside container: $containerAudio"

# Mount entire host cache root into /root/.cache so all caches (whisper, huggingface, torch, etc.) are reused.
$cmd = "docker run --rm $gpuFlag -v `"$pwdPath`:/workspace`" -v `"$hostCacheRoot`:/root/.cache`" -e HF_HOME=/root/.cache/huggingface -e TRANSFORMERS_CACHE=/root/.cache/huggingface -e TORCH_HOME=/root/.cache/torch cc_bcal-whisperx --audio $containerAudio --output $Output $requireArg"

Write-Host "Executing: $cmd"
Invoke-Expression $cmd
