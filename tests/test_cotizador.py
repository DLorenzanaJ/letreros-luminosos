import pytest

from app import cotizador


def test_cotizar_neon_basico():
    cot = cotizador.cotizar("neon_led", 1.0, 1.0)
    assert cot.subtotal == 2800.0


def test_cotizar_con_rgb_e_instalacion():
    cot = cotizador.cotizar("acrilico", 1.0, 1.0, rgb=True, instalacion=True)
    assert cot.subtotal == round(1900 + 285 + 900, 2)


def test_iva_16_por_ciento():
    cot = cotizador.cotizar("caja_luz", 2.0, 1.0)
    assert cot.iva == round(cot.subtotal * 0.16, 2)
    assert cot.total == round(cot.subtotal + cot.iva, 2)


def test_area_minima_facturable():
    cot = cotizador.cotizar("acrilico", 0.3, 0.3)
    assert cot.area_facturable == 0.25


def test_medida_fuera_de_rango():
    with pytest.raises(ValueError):
        cotizador.cotizar("neon_led", 9, 1)


def test_medida_no_numerica():
    with pytest.raises(ValueError):
        cotizador.cotizar("neon_led", "abc", 1)
