# Deja el bot listo para correr desde esta PC. Se puede ejecutar varias veces
# (solo hace lo que falta). Desde la carpeta del proyecto:
#   powershell -ExecutionPolicy Bypass -File instalar.ps1
#
#   1. Crea el entorno de Python (.venv) e instala las dependencias.
#   2. Crea .env a partir de .env.example y lo abre en el Bloc de notas para
#      pegar los secretos.
#   3. Registra la tarea «Bot noticias macro» del Programador de tareas: corre
#      bot/local.py cada hora de 7:00 a 22:00, al iniciar sesión y al
#      desbloquear la PC (local.py decide si hay algo que hacer).
#
# Para quitar la tarea: Unregister-ScheduledTask -TaskName "Bot noticias macro"

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
$usuario = "$env:USERDOMAIN\$env:USERNAME"

# 1. Entorno de Python
if (-not (Test-Path "$raiz\.venv\Scripts\python.exe")) {
    Write-Host "Creando el entorno de Python..."
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv "$raiz\.venv" }
    else { python -m venv "$raiz\.venv" }
}
Write-Host "Instalando dependencias..."
& "$raiz\.venv\Scripts\python.exe" -m pip install -q -r "$raiz\requirements.txt"

# 2. Secretos
if (-not (Test-Path "$raiz\.env")) {
    Copy-Item "$raiz\.env.example" "$raiz\.env"
    Write-Host "Pega los secretos en el Bloc de notas, guarda y ciérralo para continuar."
    Start-Process notepad "$raiz\.env" -Wait
}

# 3. Tarea programada
$accion = New-ScheduledTaskAction -Execute "$raiz\.venv\Scripts\pythonw.exe" -Argument "`"$raiz\bot\local.py`"" -WorkingDirectory $raiz

$diaria = New-ScheduledTaskTrigger -Daily -At 7:00
$diaria.Repetition = (New-ScheduledTaskTrigger -Once -At 7:00 -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Hours 16)).Repetition
$inicioSesion = New-ScheduledTaskTrigger -AtLogOn -User $usuario
$clase = Get-CimClass -Namespace Root/Microsoft/Windows/TaskScheduler -ClassName MSFT_TaskSessionStateChangeTrigger
$desbloqueo = New-CimInstance -CimClass $clase -ClientOnly -Property @{ StateChange = 8; UserId = $usuario }

$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName "Bot noticias macro" -Action $accion -Trigger @($diaria, $inicioSesion, $desbloqueo) -Settings $ajustes -Principal $principal -Force `
    -Description "Bot de Telegram de calendario macro y noticias ($raiz\bot\local.py)" | Select-Object TaskName, State

Write-Host "Listo. Registro de corridas: $raiz\logs\local.log"
