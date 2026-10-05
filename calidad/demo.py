"""Demostración del sistema: genera la salida real que se documenta en el reporte."""
import shutil
import sys
from datetime import datetime, timedelta

from app import catalogo, cotizador
from app.repositorio import RepositorioJSON
from app.soporte_ia import AsistenteSoporte, crear_proveedor
from app.ventas import Ventas

CARPETA = "salidas/demo_datos"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    shutil.rmtree(CARPETA, ignore_errors=True)
    repo = RepositorioJSON(CARPETA)
    ventas = Ventas(repo)
    ahora = [datetime(2026, 10, 2, 9, 0)]  # reloj simulado para tickets

    def reloj():
        return ahora[0]

    proveedor = crear_proveedor()
    asistente = AsistenteSoporte(repo, proveedor, reloj)

    print("=== 1. CATALOGO ===")
    for clave, nombre, precio in catalogo.listar_tipos():
        print(f"{clave:<9} {nombre:<32} ${precio:>7,.0f}/m2")

    print("\n=== 2. COTIZACIONES Y PEDIDOS ===")
    casos = [("Cafe Luna", "neon_led", 1.2, 0.6, True, True),
             ("Taller Ruiz", "caja_luz", 4.0, 2.0, False, True),
             ("Plaza Centro", "caja_luz", 5.0, 3.0, True, True)]
    for cliente, tipo, ancho, alto, rgb, inst in casos:
        cot = cotizador.cotizar(tipo, ancho, alto, rgb, inst)
        pedido = ventas.registrar_pedido(cliente, cot)
        print(f"Pedido #{pedido['id']} {cliente}: {tipo} {ancho}x{alto} m | subtotal "
              f"${cot.subtotal:,.2f} | desc {pedido['descuento_pct']:.0%} | total ${pedido['total']:,.2f}")
    ventas.cambiar_estado(1, "produccion")
    ventas.cambiar_estado(1, "entregado")
    print(f"Pedido #1 -> {ventas.listar('entregado')[0]['estado']}")
    print(f"Total vendido: ${ventas.total_vendido():,.2f}")

    print(f"\n=== 3. SOPORTE IA (modo: {proveedor.nombre}) ===")
    mensajes = ["Quiero un letrero neon de 1.2 x 0.6 m para mi cafeteria",
                "Que diferencia hay entre neon y caja de luz?",
                "Mi letrero no enciende", "Le entro agua al letrero y huele a quemado"]
    for mensaje in mensajes:
        r = asistente.atender(mensaje, cliente="Cliente demo")
        print(f"Cliente : {mensaje}\nIA      : [{r['intencion']}] {r['respuesta']}\n")
        ahora[0] += timedelta(minutes=15)

    print(f"Respuestas donde la IA fallo y se uso el modo local: {asistente.fallos_proveedor}")
    print("\n=== 4. TICKETS (reloj simulado) ===")
    for ticket, minutos in zip(asistente.tickets_abiertos(), (45, 120)):
        ahora[0] = datetime.fromisoformat(ticket["creado"]) + timedelta(minutes=minutos)
        r = asistente.resolver_ticket(ticket["id"])
        print(f"Ticket #{r['id']} ({r['severidad']}) resuelto en {r['minutos_resolucion']} min")


if __name__ == "__main__":
    main()
