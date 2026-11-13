@echo off
pushd "%~dp0"
echo Actualizacion de Contexto Mercado Electrico
echo Lee los Excel locales, valida sus tablas y publica el contexto en GitHub.
echo Este proceso no modifica Supabase ni carga los archivos TSV de data.
echo.
python scripts\export_market_context.py --publicar
if errorlevel 1 (
    echo.
    echo ERROR: la actualizacion no termino. Revise el mensaje anterior.
)
echo.
pause
popd
