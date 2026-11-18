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
| Generacion por tecnologia | Generación por tipo de tecnologia.xlsx | 2026-03-04 |
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

1. Actualice las fuentes que correspondan en la carpeta principal del proyecto:
   - `Generación por tipo de tecnologia.xlsx`: hoja `Hoja1`, con la tabla diaria
     por tecnologia. Si actualiza los datos de origen, actualice tambien la
     tabla dinamica antes de guardar.
   - `CM acumulado 2025-2026.xlsx`: hoja ` CMg Diario`, que contiene el historico
     de CMg, combustibles y la matriz `PROYECCIONES CEN`.
   Puede renovar solo uno de los Excel; el otro conserva su informacion actual.
   Deben permanecer ambos archivos, con sus nombres, hojas y estructura actuales.
   Guarde los libros en Excel despues de actualizar formulas o tablas dinamicas;
   el programa lee los valores guardados, no recalcula Excel.
2. Opcionalmente, compruebe las fuentes sin cambiar los datos publicados:

   ```powershell
   python scripts/export_market_context.py --solo-validar
   ```

3. Haga doble clic en `Actualizar_contexto_web.bat` en la carpeta principal.
   Alternativamente, para exportar y publicar desde PowerShell, desde `main`
   limpio y sincronizado:

   ```powershell
   python scripts/export_market_context.py --publicar
   ```

4. Espere `CONTEXTO EXPORTADO Y VERIFICADO` y `CONTEXTO PUBLICADO EN GITHUB`.
   Recargue Streamlit y revise las fechas de corte de cada seccion. Si el
   despliegue sigue ejecutando la version anterior, reinicie la app desde
   Streamlit Cloud.

La validacion es opcional: la publicacion siempre valida antes de reemplazar
las tablas. `--solo-validar` utiliza una carpeta temporal que se elimina y no
deja cambios pendientes en Git. Sin ninguna opcion, el script exporta a
`database/market_context` solo localmente; si uso ese modo, revise y publique
esos archivos mediante Git antes de volver a utilizar `--publicar`.
El comando con `--publicar` guarda un commit solo de `database/market_context`
y lo envia a `origin/main`. El despliegue recoge las nuevas tablas y la cache
cambia al actualizarse los archivos.

Los Excel originales no se publican. No se descarga informacion nueva del CEN
automaticamente: primero debe actualizar los libros locales. Ejecutar el
proceso con los mismos Excel conserva los mismos cortes de informacion.

## Dos procesos independientes

| Que actualizar | Entrada | Ejecutable | Destino |
| --- | --- | --- | --- |
| Costos marginales de las barras | TSV en `data` | `Actualizar_datos_web.bat` | Supabase y respaldo |
| Contexto Mercado Electrico | Los dos Excel de la carpeta principal | `Actualizar_contexto_web.bat` | Tablas de contexto publicadas en GitHub |

La unica conexion entre ambos es la comparacion con el promedio real de
Mejillones: el contexto lee esa serie del reporte actualizado, sin modificarla.

## Actualizar solamente el carbon del grafico mensual

El grafico mensual tiene una serie independiente de cierres diarios de futuros
de carbon Newcastle (NCFMc1), expresada en USD por tonelada. El CMg mensual
conserva su fuente del Excel y su unidad USD/MWh. El grafico muestra un solo
eje con promedios mensuales: CMg en azul y carbon en amarillo discontinuo.
Por defecto conserva los valores originales, con las unidades en la leyenda
y un aviso de que las distancias entre series no representan diferencias de costo.
El selector tambien permite ver indices base 100, tomando el primer mes comun
con valores distintos de cero (enero de 2013 en el historico actual).
No se completan meses sin datos ni se extrapola el CMg hasta la fecha del carbon.

Descargue de Investing.com un CSV con frecuencia diaria y columnas `Date` y
`Price`, conservando el formato original en ingles (fechas mes/dia/ano).
Guarde un unico CSV dentro de `data_cme`, por ejemplo `data_cme/carbon`.
El importador busca tambien en subcarpetas y los archivos originales no se
suben a GitHub. El archivo debe cubrir desde antes del ultimo dato guardado
para no dejar un hueco en el historico.

Desde la carpeta del proyecto:

```powershell
python scripts/update_coal_prices.py --solo-validar
python scripts/update_coal_prices.py --publicar
```

Si hay varios CSV, elija uno expresamente con `--archivo "ruta/al/archivo.csv"`.
La publicacion exige `main` limpio y sincronizado, igual que los otros procesos.

Se respaldan los precios anteriores en `output/processed`. El CSV es la fuente
prioritaria para su ventana de fechas, conservando sesiones de negociacion
sin rellenar fines de semana; el historico fuera de esa ventana se conserva.
El programa informa las coincidencias y revisiones respecto al historico.

Los resultados verificados quedan en `database/market_context/coal_prices.csv.gz`
y `coal_metadata.json`. Su publicacion no modifica Supabase, la generacion,
las proyecciones ni los valores del CMg. La exportacion general desde Excel
conserva estos dos archivos y no reemplaza la actualizacion del carbon.

Primera importacion: 224 cierres desde 2026-01-02 hasta 2026-11-12; 44 fechas
superpuestas (34 coincidentes y 10 revisadas), mas 180 sesiones nuevas.

La matriz CEN mantiene la misma lectura de la version local: las ultimas 19
filas bajo la cabecera localizada en la hoja ` CMg Diario`. Si cambia la
estructura del Excel, revise el lector antes de publicar otra exportacion.
