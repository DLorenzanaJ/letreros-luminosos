"""Técnicas de estimación: juicio de expertos, análoga, tres puntos y puntos de función."""
import csv
import json
import math

PESOS_PF = {  # IFPUG: (baja, media, alta)
    "EI": (3, 4, 6), "EO": (4, 5, 7), "EQ": (3, 4, 6), "ILF": (7, 10, 15), "EIF": (5, 7, 10)}
NIVEL = {"baja": 0, "media": 1, "alta": 2}


def juicio_expertos(datos):
    por_modulo = {}
    for modulo, valores in datos["estimaciones_horas"].items():
        por_modulo[modulo] = {"valores": valores, "promedio": round(sum(valores) / len(valores), 2),
                              "minimo": min(valores), "maximo": max(valores)}
    total = round(sum(m["promedio"] for m in por_modulo.values()), 2)
    return {"expertos": datos["expertos"], "por_modulo": por_modulo, "total": total}


def estimacion_analoga(datos, sloc_actual):
    base = datos["horas_reales"] / datos["sloc"]
    horas = round(base * sloc_actual * datos["factor_ajuste"], 2)
    return {"proyecto_anterior": datos["proyecto_anterior"], "horas_anterior": datos["horas_reales"],
            "sloc_anterior": datos["sloc"], "sloc_actual": sloc_actual,
            "horas_por_sloc": round(base, 4), "factor_ajuste": datos["factor_ajuste"],
            "justificacion": datos["justificacion"], "horas": horas}


def tres_puntos(ruta_csv):
    modulos, suma_var = {}, 0.0
    with open(ruta_csv, encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            o, m, p = (float(fila[k]) for k in ("optimista", "mas_probable", "pesimista"))
            esperado, sigma = (o + 4 * m + p) / 6, (p - o) / 6
            modulos[fila["modulo"]] = {"O": o, "M": m, "P": p, "esperado": round(esperado, 2),
                                       "sigma": round(sigma, 2)}
            suma_var += sigma ** 2
    total = round(sum(v["esperado"] for v in modulos.values()), 2)
    sigma_total = round(math.sqrt(suma_var), 2)
    return {"por_modulo": modulos, "total": total, "sigma_total": sigma_total,
            "rango_95": [round(total - 2 * sigma_total, 2), round(total + 2 * sigma_total, 2)]}


def puntos_funcion(datos):
    detalle, ufp = [], 0
    resumen = {tipo: {"cantidad": 0, "puntos": 0} for tipo in PESOS_PF}
    for c in datos["componentes"]:
        peso = PESOS_PF[c["tipo"]][NIVEL[c["complejidad"]]]
        detalle.append({**c, "peso": peso})
        resumen[c["tipo"]]["cantidad"] += 1
        resumen[c["tipo"]]["puntos"] += peso
        ufp += peso
    vaf = round(0.65 + 0.01 * sum(datos["gsc"]), 2)
    pf = round(ufp * vaf, 2)
    return {"detalle": detalle, "resumen": resumen, "ufp": ufp, "suma_gsc": sum(datos["gsc"]),
            "vaf": vaf, "pf": pf, "horas_por_pf": datos["horas_por_pf"],
            "horas": round(pf * datos["horas_por_pf"], 2)}


def estimar_todo(ruta_datos, ruta_csv, sloc_actual, horas_reales):
    with open(ruta_datos, encoding="utf-8") as archivo:
        datos = json.load(archivo)
    est = {
        "juicio_expertos": juicio_expertos(datos["juicio_expertos"]),
        "analoga": estimacion_analoga(datos["analoga"], sloc_actual),
        "tres_puntos": tres_puntos(ruta_csv),
        "puntos_funcion": puntos_funcion(datos["puntos_funcion"]),
    }
    horas = {"Juicio de expertos": est["juicio_expertos"]["total"],
             "Estimación análoga": est["analoga"]["horas"],
             "Tres puntos (PERT)": est["tres_puntos"]["total"],
             "Puntos de función": est["puntos_funcion"]["horas"]}
    est["comparativo"] = [
        {"tecnica": t, "horas": h, "real": horas_reales,
         "desviacion_pct": round((h - horas_reales) / horas_reales * 100, 1)}
        for t, h in horas.items()]
    return est
