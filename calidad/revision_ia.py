"""Revisión de código asistida por IA.

Modo con IA (Claude o Gemini): la IA analiza cada módulo y devuelve hallazgos en JSON.
Modo local: reglas estáticas con AST y complejidad ciclomática (radon).
Siempre se ejecutan las reglas locales; la IA agrega hallazgos si está disponible.
"""
import ast
import glob
import json
import os

from radon.complexity import cc_visit

SISTEMA = ("Eres un revisor de código Python experto en calidad de software. Responde SOLO "
           "con un arreglo JSON, sin texto adicional.")
INSTRUCCION = ('Revisa este módulo y devuelve un arreglo JSON (máximo 5 elementos) con '
               'objetos {"linea": int, "regla": "IA-xx", "severidad": "baja|media|alta", '
               '"descripcion": str, "sugerencia_prueba": str}. Busca defectos reales o '
               'casos límite sin probar.')


def revisar_estatico(carpeta="app"):
    hallazgos = []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "*.py"))):
        if ruta.endswith("__init__.py"):
            continue
        with open(ruta, encoding="utf-8") as archivo:
            fuente = archivo.read()
        nombre = os.path.basename(ruta)
        for nodo in ast.walk(ast.parse(fuente)):
            if isinstance(nodo, ast.FunctionDef):
                largo = nodo.end_lineno - nodo.lineno + 1
                if largo >= 8 and not ast.get_docstring(nodo):
                    hallazgos.append(_h(nombre, nodo.lineno, "R01", "baja",
                                        f"Función '{nodo.name}' de {largo} líneas sin docstring",
                                        f"Documentar y probar casos límite de {nodo.name}"))
                if len(nodo.args.args) > 5:
                    hallazgos.append(_h(nombre, nodo.lineno, "R02", "baja",
                                        f"Función '{nodo.name}' con demasiados parámetros",
                                        "Agrupar parámetros en un objeto"))
            if isinstance(nodo, ast.ExceptHandler) and nodo.type is None:
                hallazgos.append(_h(nombre, nodo.lineno, "R03", "media",
                                    "except sin tipo captura errores inesperados",
                                    "Capturar excepciones específicas"))
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                    and nodo.func.id == "open"
                    and not any(k.arg == "encoding" for k in nodo.keywords)):
                hallazgos.append(_h(nombre, nodo.lineno, "R04", "baja",
                                    "open() sin encoding explícito (falla en Windows con acentos)",
                                    "Agregar encoding='utf-8'"))
        for bloque in cc_visit(fuente):
            if bloque.complexity >= 10:
                hallazgos.append(_h(nombre, bloque.lineno, "R05", "media",
                                    f"Complejidad ciclomática {bloque.complexity} en '{bloque.name}'",
                                    "Dividir la función y cubrir cada rama con pruebas"))
    return hallazgos


def _h(archivo, linea, regla, severidad, descripcion, sugerencia):
    return {"archivo": archivo, "linea": linea, "regla": regla, "severidad": severidad,
            "descripcion": descripcion, "sugerencia_prueba": sugerencia, "origen": "reglas"}


def revisar_con_ia(proveedor, carpeta="app"):
    hallazgos = []
    for ruta in sorted(glob.glob(os.path.join(carpeta, "*.py"))):
        if ruta.endswith("__init__.py"):
            continue
        with open(ruta, encoding="utf-8") as archivo:
            codigo = archivo.read()
        try:
            texto = proveedor.completar(SISTEMA, f"{INSTRUCCION}\n\n{codigo}")
            inicio, fin = texto.find("["), texto.rfind("]")
            for item in json.loads(texto[inicio:fin + 1]):
                hallazgos.append({"archivo": os.path.basename(ruta), "linea": item.get("linea", 0),
                                  "regla": item.get("regla", "IA"),
                                  "severidad": item.get("severidad", "baja"),
                                  "descripcion": item.get("descripcion", ""),
                                  "sugerencia_prueba": item.get("sugerencia_prueba", ""),
                                  "origen": "IA"})
        except Exception:
            continue  # si la IA falla en un archivo, se conservan las reglas locales
    return hallazgos


def ejecutar_revision(proveedor, carpeta="app"):
    hallazgos = revisar_estatico(carpeta)
    modo = "local (reglas estáticas)"
    if getattr(proveedor, "usa_ia", False):
        antes = proveedor.llamadas_ok
        hallazgos += revisar_con_ia(proveedor, carpeta)
        if proveedor.llamadas_ok > antes:
            modo = f"{proveedor.nombre} + reglas estáticas"
        else:
            modo = "reglas estáticas (la IA no respondió)"
    por_regla = {}
    for h in hallazgos:
        por_regla[h["regla"]] = por_regla.get(h["regla"], 0) + 1
    return {"modo": modo, "total": len(hallazgos), "por_regla": por_regla, "hallazgos": hallazgos}
