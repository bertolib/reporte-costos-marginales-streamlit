# Reporte publicado

- Reporte compartible (Streamlit Community Cloud): https://reporte-costos-marginales-app-6pambvkjk5hw3v8va9vjti.streamlit.app/
- Repositorio: https://github.com/bertolib/reporte-costos-marginales-streamlit
- Entrada: `main` / `app.py`.
- Administracion de datos (Supabase): https://supabase.com/dashboard/project/wbpfjrdfaftkzuyapeed
- `http://127.0.0.1:8501` es solamente la version local.

El reporte ya esta publicado; para compartirlo se usa la URL de Streamlit.
Si Streamlit lo suspende por inactividad, abrir el reporte y pulsar
`Yes, get this app back up!`.

Los datos de costos marginales se leen desde Supabase. Ultima carga verificada:
datos hasta 2026-11-05 23:45, con ultima carga el 2026-11-13 y un total
historico de 64.704 registros, segun el respaldo verificado vigente.
Se guardo un respaldo previo de la ventana actualizada en `output/processed/`.
La seccion Contexto Mercado Electrico utiliza tablas compactas verificadas en
`database/market_context/` cuando los Excel locales no estan disponibles.
Los costos marginales reales usados para comparar proyecciones provienen de
la misma fuente Supabase o respaldo que utiliza el resumen.
Consulte `docs/contexto_mercado.md` para ver fuentes, fechas de corte y el
procedimiento de actualizacion independiente de estos datos.

Al recargar el reporte, la fecha mas reciente de Supabase forma parte de la
clave de cache. Ademas, los datos en cache vencen a los cinco minutos para
reflejar correcciones dentro del mismo rango de fechas.

## Recuperacion ante caidas de Supabase

El 2026-11-12 se verifico un error de conexion en la web y un fallo de
resolucion DNS para el servidor de Supabase desde el entorno local.
No se pudo verificar el estado administrativo del proyecto sin iniciar sesion.

La app incluye `database/snapshots/cmg_verified.csv.gz`, un respaldo comprimido
de los 64.704 registros historicos verificados hasta 2026-11-05 23:45,
renovado el 2026-11-13. La conexion con Supabase fue restaurada y verificada
el 2026-11-12.
Si falla la conexion o la API de Supabase, el resumen y el detalle usan ese
respaldo y muestran un aviso con su fecha de corte. La siguiente ejecucion
vuelve a intentar la fuente en linea automaticamente.
El respaldo debe renovarse despues de cada carga validada en Supabase;
no contiene credenciales ni reemplaza la base en linea.
