"""Pruebas de funcionamiento del asistente de IA y de tolerancia a fallos.

Genera la evidencia que se documenta en el reporte (sección 7). Los casos usan
proveedores simulados para ser repetibles; además hace UNA llamada real con una
clave falsa (si hay internet) para registrar cómo responde la API de verdad.
"""
import os
import shutil
import sys
import urllib.error

from app.repositorio import RepositorioJSON
from app.soporte_ia import AsistenteSoporte, ProveedorGemini, ProveedorLocal, _enviar_http

BASE = "salidas/pruebas_ia_datos"
CASOS = [
    ("Quiero un letrero neon de 1.2 x 0.6 m para mi cafeteria", "cotizar, total $2,338.56"),
    ("Que diferencia hay entre neon y caja de luz?", "catalogo, compara productos"),
    ("Mi letrero no enciende", "falla, ticket media"),
    ("Le entro agua al letrero y huele a quemado", "falla, ticket alta, indica desconectar"),
    ("hola", "otro"),
    ("cuanto cuesta un letrero", "cotizar, pide medidas"),
    ("Quiero un letrero neon de 9 x 1", "cotizar, rechaza medida"),
]


def describir(r):
    partes = [r["intencion"]]
    if r["cotizacion"] is not None:
        partes.append(f"total ${r['cotizacion'].total:,.2f}")
    if r["ticket"] is not None:
        partes.append(f"ticket {r['ticket']['severidad']}")
    texto = r["respuesta"]
    if r["intencion"] == "catalogo" and "Neón" in texto and "Caja de luz" in texto:
        partes.append("compara productos")
    if "Desconecte" in texto:
        partes.append("indica desconectar")
    if "necesito las medidas" in texto:
        partes.append("pide medidas")
    if "No pude cotizar" in texto:
        partes.append("rechaza medida")
    return ", ".join(partes)


def _asistente(nombre, proveedor):
    carpeta = os.path.join(BASE, nombre)
    shutil.rmtree(carpeta, ignore_errors=True)
    return AsistenteSoporte(RepositorioJSON(carpeta), proveedor)


def _correr(asistente):
    return [asistente.atender(mensaje, cliente="Prueba") for mensaje, _ in CASOS]


def _fallar(error):
    def enviar(url, cabeceras, cuerpo):
        raise error
    return enviar


def _respuesta(texto):
    return lambda url, cabeceras, cuerpo: {"candidates": [{"content": {"parts": [{"text": texto}]}}]}


def ejecutar(con_red=True):
    shutil.rmtree(BASE, ignore_errors=True)
    n = len(CASOS)
    local = _correr(_asistente("local", ProveedorLocal()))
    asistente_rows = []
    for i, ((mensaje, esperado), r) in enumerate(zip(CASOS, local), 1):
        obtenido = describir(r)
        asistente_rows.append({"n": i, "mensaje": mensaje, "esperado": esperado,
                               "obtenido": obtenido, "ok": obtenido == esperado})
    textos_local = [r["respuesta"] for r in local]

    escenarios = [
        ("Sin conexión (ConnectionError)", _fallar(ConnectionError("sin red")), n, "reglas"),
        ("Clave rechazada (HTTP 403)",
         _fallar(urllib.error.HTTPError("https://x", 403, "Forbidden", {}, None)), n, "reglas"),
        ("Tiempo de espera agotado", _fallar(TimeoutError("lento")), n, "reglas"),
        ("Respuesta vacía de la IA", _respuesta(""), 0, "reglas"),
        ("IA disponible (simulada)", _respuesta("Respuesta redactada por la IA"), 0, "ia"),
    ]
    fallos_rows = []
    for k, (nombre, enviar, fallos_esp, esperado) in enumerate(escenarios):
        proveedor = ProveedorGemini("clave-simulada", enviar=enviar)
        asistente = _asistente(f"esc{k}", proveedor)
        textos = [r["respuesta"] for r in _correr(asistente)]
        if esperado == "reglas":
            coinciden = sum(1 for a, b in zip(textos, textos_local) if a == b)
        else:
            coinciden = sum(1 for a in textos if a == "Respuesta redactada por la IA")
        ok = coinciden == n and asistente.fallos_proveedor == fallos_esp
        fallos_rows.append({"escenario": nombre, "mensajes": n, "esperado": esperado,
                            "coinciden": coinciden, "fallos": asistente.fallos_proveedor,
                            "fallos_esperados": fallos_esp, "ok": ok})

    real = {"ejecutada": False, "resultado": "no se ejecutó (sin red solicitada)", "respondio_con_reglas": None}
    if con_red:
        enviar = lambda u, h, c: _enviar_http(u, h, c, tiempo=8)
        proveedor = ProveedorGemini("clave-falsa", enviar=enviar)
        try:
            proveedor.completar("prueba", "hola")
            motivo = "la API aceptó la clave falsa (inesperado)"
        except urllib.error.HTTPError as error:
            motivo = f"el servicio rechazó la solicitud (HTTP {error.code})"
        except urllib.error.URLError:
            motivo = "sin conexión a internet"
        except Exception as error:
            motivo = f"error {type(error).__name__}"
        r = _asistente("real", proveedor).atender("Mi letrero no enciende", cliente="Prueba")
        real = {"ejecutada": True, "resultado": motivo,
                "respondio_con_reglas": "Ticket #" in r["respuesta"] and "Revise" in r["respuesta"]}

    total = n + len(escenarios)
    pasan = sum(x["ok"] for x in asistente_rows) + sum(x["ok"] for x in fallos_rows)
    return {"asistente": asistente_rows, "fallos": fallos_rows, "real": real, "total": total, "pasan": pasan}


def escribir_log(res, ruta="salidas/salida_pruebas_ia.txt"):
    lineas = ["=== A. ASISTENTE (proveedor local, repetible) ==="]
    for x in res["asistente"]:
        lineas.append(f"[{'OK' if x['ok'] else 'FALLA'}] {x['n']}. {x['mensaje']}")
        lineas.append(f"      esperado: {x['esperado']} | obtenido: {x['obtenido']}")
    lineas.append("\n=== B. SIMULACION DE FALLAS DE LA IA ===")
    for x in res["fallos"]:
        lineas.append(f"[{'OK' if x['ok'] else 'FALLA'}] {x['escenario']}: {x['coinciden']}/{x['mensajes']} "
                      f"respuestas correctas, fallos contados {x['fallos']}")
    lineas.append("\n=== C. LLAMADA REAL CON CLAVE FALSA ===")
    real = res["real"]
    lineas.append(f"Resultado de la llamada: {real['resultado']}")
    if real["ejecutada"]:
        lineas.append(f"El asistente respondio con reglas: {'si' if real['respondio_con_reglas'] else 'no'}")
    lineas.append(f"\nPruebas de IA aprobadas: {res['pasan']} de {res['total']}")
    with open(ruta, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")
    return "\n".join(lineas)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    resultado = ejecutar(con_red=os.getenv("PRUEBAS_IA_SIN_RED") != "1")
    print(escribir_log(resultado))
    sys.exit(0 if resultado["pasan"] == resultado["total"] else 1)
