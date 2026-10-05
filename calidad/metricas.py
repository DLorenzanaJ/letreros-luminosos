"""Cálculo de métricas de producto, proceso y proyecto + informe de calidad.

Todo el reporte se genera a partir de salidas/metrics.json, por eso los
números del documento siempre coinciden con la ejecución del programa.
"""
import csv
import glob
import json
import os
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

from radon.complexity import cc_rank, cc_visit
from radon.metrics import mi_visit
from radon.raw import analyze

from calidad import estimaciones
from calidad.requisitos import REQUISITOS

SALIDAS = "salidas"
FORMATO_FECHA = "%Y-%m-%d %H:%M"


def medir_producto(carpeta="app"):
    modulos, funciones = {}, []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "*.py"))):
        nombre = os.path.basename(ruta)[:-3]
        if nombre == "__init__":
            continue
        with open(ruta, encoding="utf-8") as archivo:
            fuente = archivo.read()
        bloques = cc_visit(fuente)
        valores = [b.complexity for b in bloques] or [0]
        modulos[nombre] = {
            "sloc": analyze(fuente).sloc, "funciones": len(bloques),
            "cc_promedio": round(sum(valores) / len(valores), 2), "cc_maxima": max(valores),
            "rango_max": cc_rank(max(valores)), "indice_mantenibilidad": round(mi_visit(fuente, True), 1)}
        funciones += [{"modulo": nombre, "funcion": b.name, "cc": b.complexity,
                       "rango": cc_rank(b.complexity)} for b in bloques]
    sloc = sum(m["sloc"] for m in modulos.values())
    todos = [f["cc"] for f in funciones]
    funciones.sort(key=lambda f: -f["cc"])
    return {"modulos": modulos, "sloc": sloc, "kloc": round(sloc / 1000, 3),
            "funciones_total": len(funciones), "cc_promedio": round(sum(todos) / len(todos), 2),
            "cc_maxima": max(todos), "top_funciones": funciones[:8],
            "mi_promedio": round(sum(m["indice_mantenibilidad"] for m in modulos.values()) / len(modulos), 1)}


def correr_pruebas():
    os.makedirs(SALIDAS, exist_ok=True)
    comando = [sys.executable, "-m", "pytest", "--cov=app", "--cov-report=term-missing",
               f"--cov-report=json:{SALIDAS}/coverage.json", f"--junitxml={SALIDAS}/junit.xml",
               "-v", "--no-header", "-p", "no:cacheprovider"]
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proceso = subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", env=entorno)
    with open(f"{SALIDAS}/salida_pruebas.txt", "w", encoding="utf-8") as archivo:
        archivo.write(proceso.stdout + proceso.stderr)
    return proceso.returncode


def leer_resultados():
    suite = ET.parse(f"{SALIDAS}/junit.xml").getroot().find("testsuite")
    aprobadas, todas = set(), []
    for caso in suite.iter("testcase"):
        fallo = caso.find("failure") is not None or caso.find("error") is not None
        todas.append(caso.get("name"))
        if not fallo:
            aprobadas.add(caso.get("name"))
    with open(f"{SALIDAS}/coverage.json", encoding="utf-8") as archivo:
        cov = json.load(archivo)
    por_archivo = {os.path.basename(r)[:-3]: {"cobertura": round(d["summary"]["percent_covered"], 1),
                                              "sentencias": d["summary"]["num_statements"],
                                              "no_cubiertas": d["summary"]["missing_lines"]}
                   for r, d in cov["files"].items()}
    pruebas = {"total": len(todas), "aprobadas": len(aprobadas), "fallidas": len(todas) - len(aprobadas),
               "tiempo_s": round(float(suite.get("time")), 2),
               "tasa_exito": round(len(aprobadas) / len(todas) * 100, 1)}
    return pruebas, {"total": round(cov["totals"]["percent_covered"], 1), "por_archivo": por_archivo}, aprobadas


def evaluar_requisitos(aprobadas, cobertura, cc_prom):
    resultado = []
    for id_, texto, tipo, pruebas in REQUISITOS:
        ok = all(p in aprobadas for p in pruebas)
        resultado.append({"id": id_, "requisito": texto, "tipo": tipo, "pruebas": len(pruebas),
                          "cumple": ok})
    cumplidos = sum(r["cumple"] for r in resultado)
    return {"detalle": resultado, "cumplidos": cumplidos, "total": len(resultado),
            "porcentaje": round(cumplidos / len(resultado) * 100, 1)}


def _fecha(texto):
    return datetime.strptime(texto, FORMATO_FECHA)


def medir_defectos(ruta, producto):
    with open(ruta, encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    horas = lambda a, b: (_fecha(b) - _fecha(a)).total_seconds() / 3600
    for f in filas:
        f["mttd"] = horas(f["fecha_introduccion"], f["fecha_deteccion"])
        f["mttr"] = horas(f["fecha_deteccion"], f["fecha_resolucion"])
    total = len(filas)
    cuenta = lambda clave, valor: sum(1 for f in filas if f[clave] == valor)
    criticos = lambda fase: sum(1 for f in filas if f["severidad"] == "critica" and f["fase_deteccion"] == fase)
    cp, cprod = criticos("pruebas"), criticos("produccion")
    por_modulo = {}
    for modulo, datos in producto["modulos"].items():
        n = sum(1 for f in filas if f["modulo"] == modulo)
        por_modulo[modulo] = {"defectos": n, "densidad": round(n / (datos["sloc"] / 1000), 1)}
    return {
        "total": total, "por_fase": {f: cuenta("fase_deteccion", f) for f in ("revision", "pruebas", "produccion")},
        "por_severidad": {s: cuenta("severidad", s) for s in ("critica", "alta", "media", "baja")},
        "por_origen": {o: cuenta("origen", o) for o in ("IA", "humano")},
        "densidad_kloc": round(total / producto["kloc"], 1), "por_modulo": por_modulo,
        "mttd_horas": round(sum(f["mttd"] for f in filas) / total, 2),
        "mttr_horas": round(sum(f["mttr"] for f in filas) / total, 2),
        "criticos_pruebas": cp, "criticos_produccion": cprod,
        "eficacia_pruebas": round(cp / (cp + cprod) * 100, 1) if cp + cprod else 100.0,
        "eficacia_revision": round(cuenta("fase_deteccion", "revision") / total * 100, 1),
        "bitacora": [{k: f[k] for k in ("id", "modulo", "severidad", "fase_deteccion", "origen",
                                          "descripcion")} | {"mttd": round(f["mttd"], 1), "mttr": round(f["mttr"], 1)}
                     for f in filas]}


def medir_proyecto(ruta, defectos):
    with open(ruta, encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))
    modulos, sprints = [], {}
    for f in filas:
        est, real = float(f["horas_estimadas"]), float(f["horas_reales"])
        dens = defectos["por_modulo"].get(f["modulo"], {}).get("densidad")
        modulos.append({"modulo": f["modulo"], "sprint": int(f["sprint"]), "estimadas": est, "reales": real,
                        "desviacion_pct": round((real - est) / est * 100, 1), "densidad": dens})
        s = sprints.setdefault(int(f["sprint"]), {"estimadas": 0.0, "reales": 0.0, "defectos": 0})
        s["estimadas"] += est
        s["reales"] += real
        s["defectos"] += defectos["por_modulo"].get(f["modulo"], {}).get("defectos", 0)
    for s in sprints.values():
        s["desviacion_pct"] = round((s["reales"] - s["estimadas"]) / s["estimadas"] * 100, 1)
    est_t, real_t = sum(m["estimadas"] for m in modulos), sum(m["reales"] for m in modulos)
    return {"modulos": modulos, "sprints": {str(k): v for k, v in sorted(sprints.items())},
            "horas_estimadas": est_t, "horas_reales": real_t,
            "desviacion_pct": round((real_t - est_t) / est_t * 100, 1),
            "eficacia_revision": defectos["eficacia_revision"]}


def medir_tickets(carpeta=f"{SALIDAS}/demo_datos"):
    ruta = os.path.join(carpeta, "tickets.json")
    if not os.path.exists(ruta):
        return {"total": 0, "resueltos": 0, "minutos_promedio": 0.0}
    with open(ruta, encoding="utf-8") as archivo:
        tickets = json.load(archivo)
    resueltos = [t for t in tickets if t["estado"] == "resuelto"]
    prom = sum(t["minutos_resolucion"] for t in resueltos) / len(resueltos) if resueltos else 0.0
    return {"total": len(tickets), "resueltos": len(resueltos), "minutos_promedio": round(prom, 1)}


def informe_calidad(m):
    p, d, pr = m["producto"], m["defectos"], m["proyecto"]
    criterios = [
        ("Pruebas aprobadas", "100 %", m["pruebas"]["tasa_exito"], 100, ">=", "%", "Idoneidad funcional"),
        ("Cumplimiento de requisitos", "100 %", m["requisitos"]["porcentaje"], 100, ">=", "%", "Idoneidad funcional"),
        ("Cobertura de código", ">= 80 %", m["cobertura"]["total"], 80, ">=", "%", "Idoneidad funcional"),
        ("Complejidad ciclomática máxima", "<= 10", p["cc_maxima"], 10, "<=", "", "Mantenibilidad"),
        ("Eficacia de las pruebas (críticos)", ">= 70 %", d["eficacia_pruebas"], 70, ">=", "%", "Fiabilidad"),
        ("MTTR", "<= 24 h", d["mttr_horas"], 24, "<=", " h", "Fiabilidad"),
        ("Densidad de defectos", "<= 50 /KLOC", d["densidad_kloc"], 50, "<=", "", "Fiabilidad"),
        ("Desviación de esfuerzo total", "<= 30 %", pr["desviacion_pct"], 30, "<=", "%", "Gestión"),
    ]
    filas = []
    for nombre, meta, valor, umbral, op, unidad, car in criterios:
        ok = valor >= umbral if op == ">=" else valor <= umbral
        filas.append({"criterio": nombre, "meta": meta, "resultado": f"{valor}{unidad}",
                      "cumple": bool(ok), "caracteristica": car})
    cumplen = sum(f["cumple"] for f in filas)
    return {"criterios": filas, "cumplen": cumplen, "total": len(filas),
            "grado_cumplimiento": round(cumplen / len(filas) * 100, 1)}


def interpretar(m, proveedor):
    p, d = m["producto"], m["defectos"]
    nivel = "baja (código fácil de mantener y probar)" if p["cc_maxima"] <= 10 else "moderada: hay funciones por simplificar"
    borrador = (
        f"Complejidad ciclomática promedio {p['cc_promedio']} y máxima {p['cc_maxima']}: complejidad {nivel}. "
        f"Cobertura {m['cobertura']['total']} % con {m['pruebas']['total']} pruebas, todas aprobadas "
        f"en {m['pruebas']['tiempo_s']} s. " if m["pruebas"]["fallidas"] == 0 else
        f"Hay {m['pruebas']['fallidas']} pruebas fallidas que deben corregirse antes de liberar. ")
    borrador += (
        f"Densidad de {d['densidad_kloc']} defectos/KLOC (valor citado por McConnell para software entregado: 15 a 50). "
        f"MTTD {d['mttd_horas']} h y MTTR {d['mttr_horas']} h; el defecto que llegó a producción "
        f"muestra que debe reforzarse la validación de severidad. Eficacia de pruebas {d['eficacia_pruebas']} % "
        f"y de revisión {d['eficacia_revision']} %. Desviación de esfuerzo {m['proyecto']['desviacion_pct']} %.")
    try:
        texto = proveedor.generar(
            "Eres un analista de calidad de software. Explica métricas en español, en máximo 150 palabras, "
            "sin cambiar ninguna cifra.", "Interpreta estas métricas del proyecto.", borrador)
        return texto.strip() or borrador
    except Exception:
        return borrador


def calcular_todo(proveedor, ejecutar_pruebas=True):
    from calidad.revision_ia import ejecutar_revision
    from calidad import pruebas_ia
    if ejecutar_pruebas:
        correr_pruebas()
    producto = medir_producto()
    pruebas, cobertura, aprobadas = leer_resultados()
    defectos = medir_defectos("calidad/defectos.csv", producto)
    proyecto = medir_proyecto("calidad/proyecto.csv", defectos)
    m = {"generado": datetime.now().isoformat(timespec="seconds"), "sistema": platform.platform(),
         "python": platform.python_version(), "modo_ia": proveedor.nombre,
         "producto": producto, "pruebas": pruebas, "cobertura": cobertura,
         "requisitos": evaluar_requisitos(aprobadas, cobertura, producto["cc_promedio"]),
         "defectos": defectos, "proyecto": proyecto, "tickets": medir_tickets(),
         "revision_ia": ejecutar_revision(proveedor),
         "estimaciones": estimaciones.estimar_todo("calidad/datos_estimacion.json", "calidad/proyecto.csv",
                                                   producto["sloc"], proyecto["horas_reales"])}
    m["calidad"] = informe_calidad(m)
    m["interpretacion_ia"] = interpretar(m, proveedor)
    m["pruebas_ia"] = pruebas_ia.ejecutar(con_red=os.getenv("PRUEBAS_IA_SIN_RED") != "1")
    pruebas_ia.escribir_log(m["pruebas_ia"])
    m["ia_llamadas"] = {"ok": proveedor.llamadas_ok, "fallidas": proveedor.llamadas_fallidas}
    with open(f"{SALIDAS}/metrics.json", "w", encoding="utf-8") as archivo:
        json.dump(m, archivo, ensure_ascii=False, indent=2)
    return m
