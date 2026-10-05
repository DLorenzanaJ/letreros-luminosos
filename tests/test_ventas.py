import pytest

from app import cotizador
from app.repositorio import RepositorioJSON
from app.ventas import Ventas, calcular_descuento


@pytest.fixture
def ventas(tmp_path):
    return Ventas(RepositorioJSON(str(tmp_path)))


def test_descuento_5(ventas):
    assert calcular_descuento(10000) == 0.05


def test_descuento_10(ventas):
    assert calcular_descuento(30000) == 0.10
    assert calcular_descuento(500) == 0.0


def test_registrar_pedido_persiste(ventas):
    cot = cotizador.cotizar("neon_led", 1.2, 0.6)
    pedido = ventas.registrar_pedido("Cafe Luna", cot)
    assert pedido["id"] == 1 and pedido["estado"] == "nuevo"
    assert len(ventas.listar()) == 1
    assert ventas.total_vendido() == pedido["total"]


def test_cliente_obligatorio(ventas):
    with pytest.raises(ValueError):
        ventas.registrar_pedido("  ", cotizador.cotizar("neon_led", 1, 1))


def test_transicion_valida(ventas):
    ventas.registrar_pedido("Ana", cotizador.cotizar("acrilico", 1, 1))
    assert ventas.cambiar_estado(1, "produccion")["estado"] == "produccion"


def test_transicion_invalida(ventas):
    ventas.registrar_pedido("Ana", cotizador.cotizar("acrilico", 1, 1))
    with pytest.raises(ValueError):
        ventas.cambiar_estado(1, "entregado")
    with pytest.raises(KeyError):
        ventas.cambiar_estado(99, "produccion")


def test_cancelado_no_suma_al_total(ventas):
    ventas.registrar_pedido("Ana", cotizador.cotizar("acrilico", 1, 1))
    ventas.cambiar_estado(1, "cancelado")
    assert ventas.total_vendido() == 0
