from datetime import datetime, timedelta

import pytest

from app.repositorio import RepositorioJSON
from app.soporte_ia import AsistenteSoporte, ProveedorClaude, ProveedorGemini, crear_proveedor


class ClaudeFalso:
    """Simula el SDK de Anthropic para pruebas repetibles (sin red)."""
    def __init__(self, falla=False):
        self.falla = falla
        self.messages = self

    def create(self, **kwargs):
        if self.falla:
            raise ConnectionError("sin red")

        class Bloque:
            type = "text"
            text = "Respuesta redactada por la IA"

        class Resp:
            content = [Bloque()]
        return Resp()


@pytest.fixture
def repo(tmp_path):
    return RepositorioJSON(str(tmp_path))


def test_soporte_cotiza_desde_texto(repo):
    r = AsistenteSoporte(repo).atender("Quiero un letrero neon de 1.2 x 0.6 m para mi cafeteria")
    assert r["intencion"] == "cotizar"
    assert r["cotizacion"].total == round(0.72 * 2800 * 1.16, 2)


def test_soporte_pide_medidas_si_faltan(repo):
    r = AsistenteSoporte(repo).atender("cuanto cuesta un letrero")
    assert r["cotizacion"] is None and "medidas" in r["respuesta"]


def test_soporte_falla_crea_ticket(repo):
    r = AsistenteSoporte(repo).atender("Mi letrero no enciende", cliente="Luis")
    assert r["intencion"] == "falla" and r["ticket"]["severidad"] == "media"
    assert len(repo.cargar("tickets")) == 1


def test_soporte_riesgo_electrico_es_alta(repo):
    r = AsistenteSoporte(repo).atender("le entro agua y huele a quemado")
    assert r["ticket"]["severidad"] == "alta" and "Desconecte" in r["respuesta"]


def test_soporte_responde_catalogo(repo):
    r = AsistenteSoporte(repo).atender("Que diferencia hay entre neon y caja de luz?")
    assert r["intencion"] == "catalogo" and "Caja de luz" in r["respuesta"]


def test_soporte_mensaje_otro(repo):
    assert AsistenteSoporte(repo).atender("hola")["intencion"] == "otro"


def test_resolver_ticket_calcula_tiempo(repo):
    horas = iter([datetime(2026, 10, 1, 10, 0), datetime(2026, 10, 1, 10, 0) + timedelta(minutes=45)])
    asistente = AsistenteSoporte(repo, reloj=lambda: next(horas))
    asistente.atender("no prende")
    ticket = asistente.resolver_ticket(1)
    assert ticket["minutos_resolucion"] == 45 and ticket["estado"] == "resuelto"


def test_resolver_ticket_invalido(repo):
    asistente = AsistenteSoporte(repo)
    with pytest.raises(KeyError):
        asistente.resolver_ticket(5)
    asistente.atender("no prende")
    asistente.resolver_ticket(1)
    with pytest.raises(ValueError):
        asistente.resolver_ticket(1)
    assert asistente.tickets_abiertos() == []


def test_soporte_usa_proveedor_ia(repo):
    asistente = AsistenteSoporte(repo, ProveedorClaude(cliente=ClaudeFalso()))
    assert asistente.atender("hola")["respuesta"] == "Respuesta redactada por la IA"


def test_soporte_tolera_fallo_proveedor(repo):
    asistente = AsistenteSoporte(repo, ProveedorClaude(cliente=ClaudeFalso(falla=True)))
    r = asistente.atender("Quiero un letrero acrilico de 1 x 1")
    assert "Cotizacion" in r["respuesta"] and asistente.fallos_proveedor == 1


def _respuesta_gemini(texto):
    return {"candidates": [{"content": {"parts": [{"text": texto}]}}]}


def test_gemini_redacta_y_cuenta_llamadas(repo):
    visto = {}

    def enviar(url, cabeceras, cuerpo):
        visto.update(url=url, clave=cabeceras["x-goog-api-key"])
        return _respuesta_gemini("Respuesta de Gemini")

    proveedor = ProveedorGemini("clave-falsa", enviar=enviar)
    r = AsistenteSoporte(repo, proveedor).atender("hola")
    assert r["respuesta"] == "Respuesta de Gemini" and proveedor.llamadas_ok == 1
    assert "generateContent" in visto["url"] and visto["clave"] == "clave-falsa"


def test_gemini_tolera_fallo_de_red(repo):
    def enviar(url, cabeceras, cuerpo):
        raise ConnectionError("sin internet")

    proveedor = ProveedorGemini("clave-falsa", enviar=enviar)
    asistente = AsistenteSoporte(repo, proveedor)
    r = asistente.atender("Quiero un letrero acrilico de 1 x 1")
    assert "Cotizacion" in r["respuesta"]
    assert asistente.fallos_proveedor == 1 and proveedor.llamadas_fallidas == 1


def test_crear_proveedor_segun_variables(monkeypatch):
    for variable in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    assert crear_proveedor().usa_ia is False
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    assert crear_proveedor().nombre.startswith("Gemini")
