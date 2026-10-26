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
datos hasta 2026-10-18 23:45 (archivo `2026_10_REAL-DEF.tsv`,
cargado el 2026-10-26). Se verificaron los 1.728 registros de octubre contra
Supabase: 1.344 actualizados y 384 nuevos; total historico de 62.976 registros.
Se guardo un respaldo previo de octubre en `output/processed/`.
La seccion Contexto Mercado Electrico puede depender
de archivos locales que aun no se han migrado a la nube.

Al recargar el reporte, la fecha mas reciente de Supabase forma parte de la
clave de cache. Ademas, los datos en cache vencen a los cinco minutos para
reflejar correcciones dentro del mismo rango de fechas.
