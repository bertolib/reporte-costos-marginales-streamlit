# Actualizar los datos de la plataforma web

Este procedimiento actualiza la base real de Supabase que consulta la web.
No requiere abrir Streamlit localmente ni GitHub Desktop. El computador debe
tener conexion a Internet y conservar Python, las dependencias del proyecto,
el archivo `.env` con las credenciales de Supabase y el acceso Git ya configurado.
No comparta ni suba `.env` a GitHub.

## Opcion sencilla: doble clic

1. Deje un solo archivo `.tsv` nuevo en `data`. Los anteriores pueden quedar
   guardados en `data/procesados`; esa subcarpeta no se carga automaticamente.
2. Abra `Actualizar_datos_web.bat` en la carpeta principal del proyecto.
3. Espere los mensajes `DATOS ACTUALIZADOS Y VERIFICADOS` y
   `RESPALDO PUBLICADO EN GITHUB`. No cierre la ventana mientras trabaja.
4. Recargue el enlace habitual de Streamlit y revise el ultimo dato disponible
   y la fecha de carga. Las correcciones del mismo periodo pueden tardar hasta
   cinco minutos en verse, por la cache.

## Opcion por PowerShell

```powershell
cd "C:\python_local\python_pruebas\automatizaciones\reporte_costosmarginales_VERSION_WEB"
python scripts/actualizar_web.py --publicar-respaldo
```

Para comprobar el archivo sin modificar Supabase ni publicar nada:

```powershell
python scripts/actualizar_web.py --solo-validar
```

Para elegir expresamente un archivo si hay varios en `data`:

```powershell
python scripts/actualizar_web.py --archivo "data/2026_11_REAL-DEF.tsv" --publicar-respaldo
```

## Que realiza

- Valida las cinco series, los duplicados y los intervalos de 15 minutos de dias completos.
- Con `--publicar-respaldo`, comprueba antes de cargar que Git este en `main`,
  sin cambios pendientes y sincronizado con `origin/main`. No publica desarrollo pendiente.
- Lee el historico actual desde Supabase y guarda una copia previa completa en
  `output/processed/supabase_backup_*.csv.gz`.
- Inserta o actualiza solamente los registros del archivo elegido, registrando
  la fecha de carga. No elimina registros historicos.
- Vuelve a leer Supabase y verifica tanto lo actualizado como los datos que no
  debian cambiar. Si falla la verificacion, no reemplaza el respaldo de la web.
- Genera el CSV historico local y renueva el respaldo comprimido y su metadata.
- Con `--publicar-respaldo`, crea un commit exclusivamente de los dos archivos
  de `database/snapshots` y lo envia a GitHub. Streamlit recoge ese respaldo.

Sin `--publicar-respaldo`, se actualizan Supabase y el respaldo local, pero no
se envia este ultimo a GitHub.

## Si aparece un error

No tome la operacion como completada si faltan los mensajes de exito.
Si falla antes de cargar, corrija lo indicado y vuelva a ejecutar.
Si falla durante la carga, puede haber lotes aplicados: conserve el respaldo
previo y vuelva a ejecutar el mismo archivo para completar los registros.
Si Supabase ya quedo verificado pero falla el envio a GitHub, el programa lo
indica; revise la conexion o autenticacion y ejecute `git push origin main`.
Si Git tiene cambios pendientes de desarrollo, no los publique sin revisarlos.

Para este proyecto ya estan instaladas las dependencias. En otro computador,
instale primero Python y Git y ejecute `python -m pip install -r requirements.txt`;
configure por separado las credenciales y el acceso a GitHub.
