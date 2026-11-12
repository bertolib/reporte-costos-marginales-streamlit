@echo off
pushd "%~dp0"
echo Actualizacion de datos de la plataforma web
echo Este proceso carga los datos en Supabase y publica el respaldo verificado.
echo.
python scripts\actualizar_web.py --publicar-respaldo
echo.
pause
popd
