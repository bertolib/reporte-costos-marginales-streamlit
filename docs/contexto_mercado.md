# Contexto Mercado Electrico en local y en Streamlit Cloud

La seccion conserva los graficos y controles desarrollados localmente:

- Generacion diaria por tecnologia, con filtros de fechas y tipos de energia.
- Historia mensual del CMg y precio del carbon.
- Historia diaria del CMg y proyecciones CEN.
- Tarjetas y matriz de proyecciones CEN.
- Evolucion de proyecciones por mes objetivo, comparada con el promedio real
  de Mejillones 110 que ya carga la aplicacion desde Supabase o su respaldo.

## Fuentes y cortes de la primera publicacion

Exportacion verificada el 2026-11-13 a partir de los Excel existentes:

| Informacion | Archivo local | Corte disponible |
| --- | --- | --- |
| Generacion por tecnologia | Generacion por tipo de tecnologia.xlsx (con acento en el nombre real) | 2026-03-04 |
| Precio carbon | CM acumulado 2025-2026.xlsx | 2026-03-04 |
| CMg diario y mensual | CM acumulado 2025-2026.xlsx | 2026-09-21 |
| Ultima emision de proyecciones CEN | CM acumulado 2025-2026.xlsx | agosto 2026 |

Las fechas de corte de las fuentes se muestran en cada seccion. Exportar hoy
un archivo no significa que sus datos esten actualizados a hoy.

## Como se publican

Los Excel originales siguen siendo fuentes locales y no se suben a GitHub.
`scripts/export_market_context.py` extrae solamente las tablas necesarias a
`database/market_context/`: tres CSV comprimidos y `metadata.json`.

El exportador verifica los valores tras comprimir y volver a leer los archivos.
El manifiesto registra filas, tamanos, hashes de datos y fuentes y fecha de
exportacion. El lector de la web comprueba esos hashes y cantidades.

Modo por defecto `CONTEXT_DATA_SOURCE=auto`:

- Si ambos Excel estan disponibles, la version local los lee directamente.
- Si no estan, como ocurre en Streamlit Cloud, se usan las tablas publicadas.
- Para probar localmente exactamente los datos publicados, configure
  `CONTEXT_DATA_SOURCE=published`. Tambien se admite `excel` para exigir los originales.

Esto no crea nuevas tablas ni modifica Supabase. Sus costos marginales siguen
actualizandose por el proceso TSV existente. El contexto se renueva por separado.

## Actualizar el contexto

1. Actualice los dos Excel en la carpeta principal conservando los nombres
   configurados en `config/settings.py`.
2. Para generar y revisar la exportacion local:

   ```powershell
   python scripts/export_market_context.py
   ```

3. Para exportar y publicar en un solo paso, desde `main` limpio y sincronizado:

   ```powershell
   python scripts/export_market_context.py --publicar
   ```

El segundo comando requiere comenzar sin cambios pendientes: si primero hizo
una exportacion para revisar, publique esos archivos revisados mediante Git.
El comando con `--publicar` guarda un commit solo de `database/market_context`
y lo envia a `origin/main`. El despliegue recoge las nuevas tablas y la cache
cambia al actualizarse los archivos.

La matriz CEN mantiene la misma lectura de la version local: las ultimas 19
filas bajo la cabecera localizada en la hoja ` CMg Diario`. Si cambia la
estructura del Excel, revise el lector antes de publicar otra exportacion.
