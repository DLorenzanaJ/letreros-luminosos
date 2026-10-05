from calidad import pruebas_ia


def test_pruebas_ia_todas_pasan_sin_red():
    resultado = pruebas_ia.ejecutar(con_red=False)
    assert resultado["pasan"] == resultado["total"] == 12
