"""Registro de pedidos, descuentos por volumen y estados."""
from datetime import datetime

from app.cotizador import IVA, Cotizacion

DESCUENTOS = [(25000.0, 0.10), (10000.0, 0.05)]
TRANSICIONES = {
    "nuevo": ["produccion", "cancelado"],
    "produccion": ["entregado", "cancelado"],
    "entregado": [],
    "cancelado": [],
}


def calcular_descuento(subtotal):
    for umbral, porcentaje in DESCUENTOS:
        if subtotal >= umbral:
            return porcentaje
    return 0.0


class Ventas:
    def __init__(self, repo):
        self.repo = repo

    def registrar_pedido(self, cliente, cotizacion: Cotizacion):
        if not str(cliente).strip():
            raise ValueError("El nombre del cliente es obligatorio")
        pct = calcular_descuento(cotizacion.subtotal)
        descuento = round(cotizacion.subtotal * pct, 2)
        base = cotizacion.subtotal - descuento
        iva = round(base * IVA, 2)
        pedido = {
            "id": self.repo.siguiente_id("pedidos"),
            "cliente": str(cliente).strip(),
            "cotizacion": cotizacion.a_dict(),
            "descuento_pct": pct,
            "descuento": descuento,
            "iva": iva,
            "total": round(base + iva, 2),
            "estado": "nuevo",
            "fecha": datetime.now().isoformat(timespec="seconds"),
        }
        return self.repo.agregar("pedidos", pedido)

    def cambiar_estado(self, id_pedido, nuevo_estado):
        pedido = next((p for p in self.repo.cargar("pedidos") if p["id"] == id_pedido), None)
        if pedido is None:
            raise KeyError(f"No existe el pedido {id_pedido}")
        if nuevo_estado not in TRANSICIONES.get(pedido["estado"], []):
            raise ValueError(f"No se puede pasar de {pedido['estado']} a {nuevo_estado}")
        return self.repo.actualizar("pedidos", id_pedido, {"estado": nuevo_estado})

    def listar(self, estado=None):
        pedidos = self.repo.cargar("pedidos")
        return [p for p in pedidos if estado is None or p["estado"] == estado]

    def total_vendido(self):
        return round(sum(p["total"] for p in self.listar() if p["estado"] != "cancelado"), 2)
