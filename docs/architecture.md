# Energy Market Intelligence Platform

## Objetivo

Plataforma interna para analizar costos marginales del Sistema Electrico Nacional
con foco ejecutivo, trazabilidad de datos y crecimiento gradual hacia base de datos,
IA y reportabilidad automatizada.

## Principios

- El Excel es fuente de lectura, no almacenamiento de la aplicacion.
- Streamlit contiene presentacion, no reglas de negocio.
- El modelo canonico usa formato largo para facilitar filtros, graficos y PostgreSQL.
- La IA futura debe explicar con evidencia y separar hechos, estimaciones y supuestos.

## Capas

- `domain`: entidades, catalogos y enumeraciones del negocio.
- `infrastructure`: repositorios y adaptadores de datos.
- `analytics`: agregaciones, estadisticas, heatmaps y anomalias.
- `application`: servicios y casos de uso.
- `presentation`: paginas Streamlit, componentes y estilos.

## Modelo Canonico Inicial

Cada observacion se normaliza con estas columnas:

- `timestamp`
- `node_id`
- `node_name`
- `zone`
- `value`
- `unit`
- `granularity`
- `scenario`
- `source`

## Fuente Actual

Archivo: `CM acumulado 2025-2026.xlsx`

Hojas usadas en la primera iteracion:

- `Datos CMg Horario`
- `Datos CMg 15min`
- ` CMg Diario`

Las hojas de graficos y pivots se tratan como referencia del proceso actual, no
como fuente canonica.
