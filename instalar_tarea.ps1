# Registra en el Programador de tareas de Windows la tarea «Bot noticias macro»,
# que corre bot/local.py cada hora de 7:00 a 22:00, al iniciar sesión y al
# desbloquear la PC (local.py decide si hay algo que hacer). Se ejecuta una sola vez:
#   powershell -ExecutionPolicy Bypass -File instalar_tarea.ps1
# Para quitarla: Unregister-ScheduledTask -TaskName "Bot noticias macro"

$raiz = $PSScriptRoot
$usuario = "$env:USERDOMAIN\$env:USERNAME"

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
