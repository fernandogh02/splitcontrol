$ErrorActionPreference = "Stop"

$BackendPath = $PSScriptRoot
$LogDirectory = Join-Path $BackendPath "logs"
$LogFile = Join-Path $LogDirectory "cierre_automatico.log"

$PythonCandidates = @(
    (Join-Path $BackendPath "venv\Scripts\python.exe"),
    (Join-Path $BackendPath ".venv\Scripts\python.exe"),
    (Join-Path $BackendPath "env\Scripts\python.exe")
)

$PythonPath = $PythonCandidates |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $PythonPath) {
    throw "No se encontro el entorno virtual en venv, .venv o env."
}

if (-not (Test-Path $LogDirectory)) {
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
}

Set-Location $BackendPath

$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

try {
    $Output = & $PythonPath "manage.py" "cerrar_actividades" 2>&1

    "[$Timestamp] EJECUCION CORRECTA" |
        Out-File -FilePath $LogFile -Append -Encoding utf8

    $Output |
        Out-File -FilePath $LogFile -Append -Encoding utf8

    exit 0
}
catch {
    "[$Timestamp] ERROR: $($_.Exception.Message)" |
        Out-File -FilePath $LogFile -Append -Encoding utf8

    exit 1
}