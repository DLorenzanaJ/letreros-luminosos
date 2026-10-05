import pytest

from app import catalogo


def test_listar_tipos_devuelve_tres():
    assert len(catalogo.listar_tipos()) == 3


def test_obtener_tipo_inexistente_falla():
    with pytest.raises(ValueError):
        catalogo.obtener_tipo("holograma")


def test_comparar_incluye_ambos_tipos():
    texto = catalogo.comparar("neon_led", "caja_luz")
    assert "Neón" in texto and "Caja de luz" in texto
