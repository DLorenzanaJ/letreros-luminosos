# Sistema de ventas de letreros luminosos con soporte IA (DevOps)

## Ejecutar en Windows (PowerShell)
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_all.py          # demo + pruebas + metricas + reporte Word
python main.py             # usar el programa
```
IA real (opcional; sin clave usa el modo local). Gratis con Gemini (Google AI Studio):
```
$env:GEMINI_API_KEY = "tu-clave"; python run_all.py
```
O con Claude: `$env:ANTHROPIC_API_KEY = "tu-clave"`. Modelo opcional: `$env:GEMINI_MODEL`.

## Antes de entregar (IMPORTANTE)
1. Edita `reporte_config.json` con tu nombre, matricula, materia y profesor.
2. Reemplaza los datos de ejemplo con los TUYOS: `calidad/proyecto.csv` (horas),
   `calidad/defectos.csv` (fechas y defectos reales de tu bitacora) y
   `calidad/datos_estimacion.json` (expertos y proyecto anterior).
3. Toma capturas y guardalas en `capturas/`: `consola_windows.png`,
   `github_repositorio.png`, `github_actions.png`.
4. Ejecuta `python run_all.py` y abre el .docx (acepta actualizar campos para el indice).

## Docker
```
docker build -t letreros . ; docker run --rm letreros
```
