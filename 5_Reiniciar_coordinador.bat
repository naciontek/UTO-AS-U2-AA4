@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RDPV - Reiniciar el coordinador
echo ============================================================
echo  Reiniciando el coordinador
echo ============================================================
echo.
echo  Los nodos se volveran a registrar solos y reenviaran las
echo  apuestas que quedaron en su bitacora local.
echo.
echo  Deja esta ventana abierta. Ctrl+C lo detiene.
echo ============================================================
echo.
python -m rdpv.coordinador
pause
