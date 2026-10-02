# Diccionario De Datos Inicial

## Observaciones De Costos Marginales

| Campo | Descripcion |
| --- | --- |
| `timestamp` | Fecha y hora normalizada de la observacion. |
| `node_id` | Identificador estable de la barra. |
| `node_name` | Nombre ejecutivo de la barra. |
| `zone` | Zona analitica: Norte, Centro, Sur o Sistema. |
| `value` | Costo marginal en USD/MWh. |
| `unit` | Unidad del valor. |
| `granularity` | `hourly`, `15min` o `daily`. |
| `scenario` | `actual` para datos observados y `projected` para fechas futuras. |
| `source` | Archivo de origen. |

## Barras Iniciales

| node_id | Barra | Zona |
| --- | --- | --- |
| `cmg_mej_110` | Mejillones 110 | Norte |
| `cmg_chacaya_110` | Chacaya 110 | Norte |
| `alto_jahuel_220` | Alto Jahuel 220 | Centro |
| `charrua_220` | Charrua 220 | Sur |

## Regla De Escenario

En esta primera version, toda observacion con `timestamp` posterior al dia actual
se clasifica como `projected`. La regla debera reemplazarse por una marca explicita
cuando el Excel o una futura base de datos incluyan esa metadata.
