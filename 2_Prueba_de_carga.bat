@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RDPV - Prueba de carga
echo ============================================================
echo  RDPV - Prueba de carga contra los 4 nodos
echo ============================================================
echo.
echo  Requiere que la red ya este levantada (script 1).
echo  Se enviaran 5000 apuestas con 100 hilos concurrentes.
echo.
pause

python -m pruebas.cliente_carga --nodos 127.0.0.1:9101 127.0.0.1:9102 127.0.0.1:9103 127.0.0.1:9104 --total 5000 --hilos-cliente 100 --salida resultados\demo_carga.json

echo.
echo ============================================================
echo  Resultado guardado en resultados\demo_carga.json
echo ============================================================
pause
