"""Cálculo de cotizaciones de letreros luminosos."""
from dataclasses import dataclass, asdict

from app import catalogo

IVA = 0.16


@dataclass
class Cotizacion:
    tipo: str
    ancho: float
    alto: float
    area_facturable: float
    rgb: bool
    instalacion: bool
    subtotal_letrero: float
    recargo_rgb: float
    costo_instalacion: float
    subtotal: float
    iva: float
    total: float

    def a_dict(self):
        return asdict(self)


def validar_medida(valor, nombre):
    try:
        medida = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"La medida '{nombre}' debe ser un número")
    if not catalogo.MEDIDA_MIN <= medida <= catalogo.MEDIDA_MAX:
        raise ValueError(
            f"La medida '{nombre}' debe estar entre "
            f"{catalogo.MEDIDA_MIN} y {catalogo.MEDIDA_MAX} m")
    return medida


def cotizar(tipo, ancho_m, alto_m, rgb=False, instalacion=False):
    datos = catalogo.obtener_tipo(tipo)
    ancho = validar_medida(ancho_m, "ancho")
    alto = validar_medida(alto_m, "alto")
    area = max(ancho * alto, catalogo.AREA_MIN_FACTURABLE)
    base = area * datos["precio_m2"]
    recargo = base * catalogo.RECARGO_RGB if rgb else 0.0
    montaje = catalogo.PRECIO_INSTALACION if instalacion else 0.0
    subtotal = base + recargo + montaje
    iva = subtotal * IVA
    return Cotizacion(
        tipo=str(tipo).strip().lower(), ancho=ancho, alto=alto,
        area_facturable=round(area, 4), rgb=rgb, instalacion=instalacion,
        subtotal_letrero=round(base, 2), recargo_rgb=round(recargo, 2),
        costo_instalacion=montaje, subtotal=round(subtotal, 2),
        iva=round(iva, 2), total=round(subtotal + iva, 2))
