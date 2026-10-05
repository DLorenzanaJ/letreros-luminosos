"""Programa de consola: ventas de letreros luminosos con soporte IA."""
import sys

from app import catalogo, cotizador
from app.repositorio import RepositorioJSON
from app.soporte_ia import AsistenteSoporte, crear_proveedor
from app.ventas import Ventas


def pedir_si_no(texto):
    return input(f"{texto} (s/n): ").strip().lower().startswith("s")


def menu_cotizar(ventas):
    print("Tipos:", ", ".join(c for c, _, _ in catalogo.listar_tipos()))
    try:
        cot = cotizador.cotizar(input("Tipo: "), input("Ancho (m): "), input("Alto (m): "),
                                rgb=pedir_si_no("Colores RGB"),
                                instalacion=pedir_si_no("Instalacion"))
    except ValueError as error:
        print(f"Error: {error}")
        return
    print(f"Subtotal ${cot.subtotal:,.2f} | IVA ${cot.iva:,.2f} | Total ${cot.total:,.2f}")
    if pedir_si_no("Registrar pedido"):
        pedido = ventas.registrar_pedido(input("Cliente: "), cot)
        print(f"Pedido #{pedido['id']} registrado. Total con descuento: ${pedido['total']:,.2f}")


def menu_soporte(asistente):
    print(f"Soporte IA ({asistente.proveedor.nombre}). Escriba 'salir' para volver.")
    while True:
        mensaje = input("Usted: ").strip()
        if mensaje.lower() == "salir":
            return
        print("Asistente:", asistente.atender(mensaje)["respuesta"])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    repo = RepositorioJSON("datos")
    ventas, asistente = Ventas(repo), AsistenteSoporte(repo, crear_proveedor())
    opciones = "1) Catalogo  2) Cotizar/Pedido  3) Pedidos  4) Soporte IA  5) Tickets  0) Salir"
    while True:
        print("\n" + opciones)
        op = input("Opcion: ").strip()
        if op == "1":
            for clave, nombre, precio in catalogo.listar_tipos():
                print(f"{clave}: {nombre} - ${precio:,.0f}/m2")
        elif op == "2":
            menu_cotizar(ventas)
        elif op == "3":
            for p in ventas.listar():
                print(f"#{p['id']} {p['cliente']} ${p['total']:,.2f} [{p['estado']}]")
        elif op == "4":
            menu_soporte(asistente)
        elif op == "5":
            for t in asistente.tickets_abiertos():
                print(f"#{t['id']} {t['cliente']} ({t['severidad']}): {t['descripcion']}")
        elif op == "0":
            return


if __name__ == "__main__":
    main()
