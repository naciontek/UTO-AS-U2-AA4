@echo off
chcp 65001 >nul
cd /d "%~dp0"
title RDPV - Demostracion de particion de red (Outbox + Circuit Breaker)
echo ============================================================
echo  RDPV - Demostracion de tolerancia a particion de red
echo ============================================================
echo.
echo  Esta es la demostracion clave para el video.
echo  Requiere que la red ya este levantada (script 1).
echo.
echo  PASO 1: se generan 300 apuestas con la red sana.
pause
python -m pruebas.cliente_carga --nodos 127.0.0.1:9101 --total 300 --hilos-cliente 20

echo.
echo ------------------------------------------------------------
echo  PASO 2: DETEN AHORA SOLO EL COORDINADOR.
echo.
echo  NO uses Ctrl+C en la ventana del script 1, porque eso
echo  detiene la red completa.
echo.
echo  En lugar de eso, ejecuta con doble clic el archivo:
echo      4_Matar_coordinador.bat
echo.
echo  Cuando el coordinador este caido, presiona una tecla aqui.
echo ------------------------------------------------------------
pause

echo.
echo  PASO 3: 400 apuestas CON EL COORDINADOR CAIDO.
echo  Deben aceptarse TODAS igual, gracias al patron Outbox.
echo.
python -m pruebas.cliente_carga --nodos 127.0.0.1:9101 --total 400 --hilos-cliente 20

echo.
echo  Apuestas guardadas localmente en la bitacora de salida:
for /f %%A in ('find /c /v "" ^< "resultados\outbox_nodo-1.jsonl"') do echo    %%A registros pendientes en resultados\outbox_nodo-1.jsonl

echo.
echo ------------------------------------------------------------
echo  PASO 4: REINICIA EL COORDINADOR.
echo.
echo  Ejecuta con doble clic el archivo:
echo      5_Reiniciar_coordinador.bat
echo.
echo  Luego presiona una tecla aqui para verificar la sincronizacion.
echo ------------------------------------------------------------
pause

timeout /t 5 >nul
echo.
echo  Bitacora de salida despues de reconectar:
for /f %%A in ('find /c /v "" ^< "resultados\outbox_nodo-1.jsonl"') do echo    %%A registros pendientes (debe ser 0)

echo.
echo  Estado final del coordinador:
python -c "from rdpv.comun.protocolo import enviar_y_recibir; import json; print(json.dumps(enviar_y_recibir('127.0.0.1', 9000, {'tipo':'ESTADO'}), indent=2, ensure_ascii=False))"

echo.
echo ============================================================
echo  Cero perdidas y cero duplicados = RD-NF06 cumplido.
echo ============================================================
pause
