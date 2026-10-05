"""Ejecuta todo el flujo: demo -> pruebas -> métricas -> reporte Word."""
import os
import subprocess
import sys

from app.soporte_ia import crear_proveedor
from calidad import metricas


def paso(texto):
    print(f"\n>>> {texto}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    os.makedirs("salidas", exist_ok=True)
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    paso("1/4 Ejecutando el programa (demo)")
    demo = subprocess.run([sys.executable, "-m", "calidad.demo"], capture_output=True,
                          text=True, encoding="utf-8", env=entorno)
    with open("salidas/salida_programa.txt", "w", encoding="utf-8") as archivo:
        archivo.write(demo.stdout + demo.stderr)
    print(demo.stdout)
    if demo.returncode != 0:
        print(demo.stderr)
        return 1

    paso("2/4 Pruebas automáticas + cobertura + métricas + revisión IA")
    m = metricas.calcular_todo(crear_proveedor())
    print(f"Pruebas: {m['pruebas']['aprobadas']}/{m['pruebas']['total']} | Cobertura: {m['cobertura']['total']} %")
    print(f"Complejidad prom/máx: {m['producto']['cc_promedio']}/{m['producto']['cc_maxima']} | "
          f"Densidad: {m['defectos']['densidad_kloc']} def/KLOC")
    print(f"MTTD: {m['defectos']['mttd_horas']} h | MTTR: {m['defectos']['mttr_horas']} h | "
          f"Eficacia pruebas: {m['defectos']['eficacia_pruebas']} % | Eficacia revisión: {m['defectos']['eficacia_revision']} %")
    print(f"Grado de cumplimiento de calidad: {m['calidad']['grado_cumplimiento']} %")

    if "--sin-reporte" not in sys.argv:
        paso("3/4 Generando reporte Word")
        import generar_reporte
        print("Reporte:", generar_reporte.generar(m))
    paso("4/4 Listo. Archivos en la carpeta 'salidas'")
    return 0 if m["pruebas"]["fallidas"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
