param()

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$ROOT = (Get-Location).Path
$PY = if ($env:PY) { $env:PY } else { 'python' }
$LIBS = if ($env:LIBS) { $env:LIBS } else { 'simplug diot simpleconf bidict glom' }
$MODELS = if ($env:MODELS) { $env:MODELS } else { 'qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b' }
$METHODS = if ($env:METHODS) { $env:METHODS } else { 'B0_direct,B1_api_list,B2_raw_api_docs,B3_oracle_api_sequence,B4_gold_pair_rule' }
$RUNS = if ($env:RUNS) { [int]$env:RUNS } else { 3 }
$TEMPERATURE = if ($env:TEMPERATURE) { $env:TEMPERATURE } else { '0.2' }
$TASKS = if ($env:TASKS) { $env:TASKS } else { '' }
$RESULT_ROOT = if ($env:RESULT_ROOT) { $env:RESULT_ROOT } else { Join-Path $ROOT 'result' }
$CLEAN = if ($env:CLEAN) { $env:CLEAN } else { '0' }
$GEN_JOBS = if ($env:GEN_JOBS) { [int]$env:GEN_JOBS } else { 4 }
$EVAL_JOBS = if ($env:EVAL_JOBS) { [int]$env:EVAL_JOBS } else { 8 }
$KEEP_ALIVE = if ($env:KEEP_ALIVE) { $env:KEEP_ALIVE } else { '1h' }
$NUM_PREDICT = if ($env:NUM_PREDICT) { $env:NUM_PREDICT } else { '500' }
$TOP_P = if ($env:TOP_P) { $env:TOP_P } else { '0.9' }
$NUM_GPU = if ($env:NUM_GPU) { $env:NUM_GPU } else { '' }

Write-Host '=================================================='
Write-Host ' PairCoder unified benchmark (4 libs x 5 models)'
Write-Host '=================================================='
Write-Host " libs       : $LIBS"
Write-Host " models     : $MODELS"
Write-Host " methods    : $METHODS"
Write-Host " runs       : $RUNS    temperature: $TEMPERATURE"
Write-Host " gen jobs   : $GEN_JOBS    eval jobs: $EVAL_JOBS"
Write-Host " keep-alive : $KEEP_ALIVE  num_predict: $NUM_PREDICT  top_p: $TOP_P"
if ($NUM_GPU) { Write-Host " num_gpu    : $NUM_GPU" }
Write-Host " python     : $PY"
Write-Host " results    : $RESULT_ROOT/<lib>_5model"
if ($TASKS) { Write-Host " tasks      : $TASKS (subset)" }
Write-Host '--------------------------------------------------'

try {
  & $PY --version | Out-Null
} catch {
  throw "PY='$PY' not found on PATH."
}

try {
  Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -TimeoutSec 5 | Out-Null
} catch {
  throw "cannot reach Ollama at http://localhost:11434 (start it with: ollama serve)"
}

$taskArg = @()
if ($TASKS) { $taskArg = @('--tasks', $TASKS) }

$numGpuArg = @()
if ($NUM_GPU) { $numGpuArg = @('--num-gpu', $NUM_GPU) }

function Assert-InWorkspace([string]$PathToCheck) {
  $full = [System.IO.Path]::GetFullPath($PathToCheck)
  $rootFull = [System.IO.Path]::GetFullPath($ROOT)
  if (-not $full.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to touch path outside workspace: $full"
  }
  return $full
}

function Run-Simplug([string]$ResultDir) {
  Write-Host '--- [1/2] generate only (paircoder_step0_simplug_pilot.py) ---'
  & $PY .\paircoder_step0_simplug_pilot.py `
    --models $MODELS --methods $METHODS --temperature $TEMPERATURE `
    --runs $RUNS --jobs $GEN_JOBS --keep-alive $KEEP_ALIVE --num-predict $NUM_PREDICT --top-p $TOP_P `
    @numGpuArg --result-dir $ResultDir @taskArg
  Write-Host '--- [2/2] anchor suite + hidden-test eval (run_exec_eval.py) ---'
  Push-Location .\exec_oracle
  try {
    & $PY .\run_exec_eval.py --result-dir $ResultDir --jobs $EVAL_JOBS
  } finally {
    Pop-Location
  }
}

function Run-Generic([string]$Lib, [string]$ResultDir) {
  Push-Location .\exec_oracle
  try {
    Write-Host '--- [1/3] anchor suite (oracle trustworthiness gate) ---'
    & $PY .\benchlib.py $Lib
    Write-Host '--- [2/3] generate (Ollama, B0-B4) ---'
    & $PY .\benchlib_generate.py --lib $Lib --models $MODELS --methods $METHODS `
      --temperature $TEMPERATURE --runs $RUNS --jobs $GEN_JOBS --keep-alive $KEEP_ALIVE `
      --num-predict $NUM_PREDICT --top-p $TOP_P @numGpuArg --result-dir $ResultDir @taskArg
    Write-Host '--- [3/3] execution-oracle eval ---'
    & $PY .\benchlib_eval.py --result-dir $ResultDir --jobs $EVAL_JOBS
  } finally {
    Pop-Location
  }
}

foreach ($lib in ($LIBS -split '\s+')) {
  if (-not $lib) { continue }
  $rdir = Join-Path $RESULT_ROOT ("{0}_5model" -f $lib)
  $rdir = Assert-InWorkspace $rdir
  Write-Host ""
  Write-Host ("########## {0}  ->  {1} ##########" -f $lib, $rdir)
  if ($CLEAN -eq '1' -and (Test-Path $rdir)) {
    Write-Host "--- CLEAN=1: wiping $rdir ---"
    Remove-Item -LiteralPath $rdir -Recurse -Force
  }
  if ($lib -eq 'simplug') {
    Run-Simplug $rdir
  } else {
    Run-Generic $lib $rdir
  }
}

Write-Host ""
Write-Host '=================================================='
Write-Host ' Done. Per-lib summaries: <result>/exec_eval/exec_summary.md'
Write-Host ' Visualize all libs with:  python visualize_exec.py'
Write-Host '=================================================='
