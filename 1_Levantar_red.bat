@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RDPV - Red distribuida (coordinador, bus, monitor, nodos, liquidadores)
echo ============================================================
echo  RDPV - Levantando la red distribuida
echo ============================================================
echo.
echo  Se iniciaran como procesos independientes:
echo    - 1 coordinador      (puerto 9000)
echo    - 1 bus de eventos   (puerto 9200)
echo    - 1 monitor          (UDP 9300)
echo    - 4 nodos de punto de venta (9101 a 9104)
echo    - 2 liquidadores
echo.
echo  Deja ESTA ventana abierta. Ctrl+C detiene toda la red.
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] No se encontro "python" en el PATH.
  echo Instala Python 3.11+ o usa "py" en lugar de "python".
  pause
  exit /b 1
)

python levantar.py --nodos 4 --liquidadores 2 --hilos-por-nodo 8 --cupo-por-nodo 5000000000

echo.
echo La red se detuvo.
pause
