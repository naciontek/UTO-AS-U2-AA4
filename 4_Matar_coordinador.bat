@echo off
chcp 65001 >nul
title RDPV - Detener solo el coordinador
echo ============================================================
echo  Deteniendo UNICAMENTE el proceso del coordinador
echo ============================================================
echo.
echo  El resto de la red (bus, monitor, nodos y liquidadores)
echo  sigue funcionando. Esto simula una particion de red.
echo.
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*rdpv.coordinador*' }; if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('  Coordinador detenido (PID ' + $_.ProcessId + ')') } } else { Write-Host '  No se encontro ningun coordinador en ejecucion.' }"
echo.
pause
