"""Catálogo de letreros luminosos y reglas de medidas."""

CATALOGO = {
    "neon_led": {
        "nombre": "Neón LED flexible",
        "precio_m2": 2800.0,
        "descripcion": "Tubo LED flexible, bajo consumo y colores vivos. "
                       "Ideal para cafeterías, bares y decoración.",
    },
    "acrilico": {
        "nombre": "Letras de acrílico con luz",
        "precio_m2": 1900.0,
        "descripcion": "Letras corpóreas de acrílico con iluminación LED. "
                       "Económico y de buena visibilidad.",
    },
    "caja_luz": {
        "nombre": "Caja de luz (anuncio luminoso)",
        "precio_m2": 2300.0,
        "descripcion": "Estructura con lona o acrílico iluminada por dentro. "
                       "Muy visible de día y de noche en fachadas.",
    },
}

PRECIO_INSTALACION = 900.0
RECARGO_RGB = 0.15
MEDIDA_MIN = 0.20
MEDIDA_MAX = 5.0
AREA_MIN_FACTURABLE = 0.25


def listar_tipos():
    return [(clave, d["nombre"], d["precio_m2"]) for clave, d in CATALOGO.items()]


def obtener_tipo(clave):
    clave_limpia = str(clave).strip().lower()
    if clave_limpia not in CATALOGO:
        raise ValueError(f"Tipo de letrero no existe: {clave}")
    return CATALOGO[clave_limpia]


def comparar(clave_a, clave_b):
    a, b = obtener_tipo(clave_a), obtener_tipo(clave_b)
    return (f"{a['nombre']}: {a['descripcion']} (${a['precio_m2']:,.0f}/m2)\n"
            f"{b['nombre']}: {b['descripcion']} (${b['precio_m2']:,.0f}/m2)")
