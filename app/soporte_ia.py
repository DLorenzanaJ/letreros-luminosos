"""Asistente de soporte con IA para clientes y vendedores.

Diseño: la lógica verificable (cotizar, diagnosticar, crear tickets) es
determinista y vive en este módulo. La IA (Claude o Gemini) redacta la respuesta final
a partir de esos datos verificados, así nunca inventa precios. Si no hay API
key, o la IA falla, el asistente responde con el modo local basado en reglas.
"""
import json
import os
import re
import unicodedata
import urllib.request
from datetime import datetime

from app import catalogo, cotizador

SISTEMA = (
    "Eres el asistente de soporte de una empresa que vende letreros luminosos. "
    "Responde en español, claro y amable, en máximo 120 palabras. Usa SOLO los "
    "datos verificados del sistema; no cambies precios, medidas ni pasos de "
    "seguridad. Si hay riesgo eléctrico, pide desconectar el letrero primero."
)

REGLAS_FALLA = [
    (("humedad", "agua", "chispa", "quemado", "olor", "lluvia"), "alta",
     "Posible riesgo electrico. 1) Desconecte el letrero de inmediato. "
     "2) No lo toque si esta mojado. 3) Un tecnico lo revisara en 24 horas."),
    (("no enciende", "no prende", "no funciona", "apagado", "sin luz"), "media",
     "Sin encendido. 1) Revise que el enchufe y el contacto tengan corriente. "
     "2) Verifique el transformador (LED indicador). 3) Revise conectores "
     "flojos. 4) Si sigue igual, un tecnico agendara visita."),
    (("parpadea", "intermitente", "tenue", "falla", "mitad"), "baja",
     "Luz inestable. 1) Revise que los conectores esten firmes. 2) Pruebe en "
     "otro contacto. 3) Si persiste, puede ser el transformador: se agenda "
     "revision."),
]

PALABRAS_TIPO = {"neon": "neon_led", "acrilico": "acrilico", "caja": "caja_luz"}
PATRON_MEDIDAS = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:m|mts|metros)?\s*(?:x|por|×)\s*(\d+(?:[.,]\d+)?)")


def _normalizar(texto):
    descompuesto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


class ProveedorLocal:
    """Modo sin API key: devuelve el borrador verificado tal cual."""
    nombre = "local (reglas)"
    usa_ia = False
    llamadas_ok = 0
    llamadas_fallidas = 0

    def generar(self, sistema, usuario, borrador):
        return borrador


class _ProveedorIA:
    """Base de los proveedores con IA real: cuenta llamadas exitosas y fallidas."""
    usa_ia = True

    def __init__(self):
        self.llamadas_ok = 0
        self.llamadas_fallidas = 0

    def completar(self, sistema, mensaje):
        try:
            texto = self._llamar(sistema, mensaje)
        except Exception:
            self.llamadas_fallidas += 1
            raise
        self.llamadas_ok += 1
        return texto

    def generar(self, sistema, usuario, borrador):
        return self.completar(sistema, (
            f"Mensaje del cliente: {usuario}\n\nDatos verificados del sistema:\n{borrador}\n\n"
            "Redacta la respuesta final para el cliente."))


class ProveedorClaude(_ProveedorIA):
    """Modo con IA: Claude (Anthropic)."""
    nombre = "Claude (API de Anthropic)"

    def __init__(self, api_key=None, modelo=None, cliente=None):
        super().__init__()
        if cliente is None:
            import anthropic
            cliente = anthropic.Anthropic(api_key=api_key)
        self.cliente = cliente
        self.modelo = modelo or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    def _llamar(self, sistema, mensaje):
        respuesta = self.cliente.messages.create(
            model=self.modelo, max_tokens=1500, system=sistema,
            messages=[{"role": "user", "content": mensaje}])
        return "".join(b.text for b in respuesta.content if getattr(b, "type", "") == "text")


def _enviar_http(url, cabeceras, cuerpo, tiempo=30):
    peticion = urllib.request.Request(url, data=json.dumps(cuerpo).encode("utf-8"),
                                      headers=cabeceras, method="POST")
    with urllib.request.urlopen(peticion, timeout=tiempo) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


class ProveedorGemini(_ProveedorIA):
    """Modo con IA: Gemini (Google AI Studio, tiene nivel gratuito). Sin librerías extra."""
    nombre = "Gemini (API de Google)"

    def __init__(self, api_key, modelo=None, enviar=None):
        super().__init__()
        self.api_key = api_key
        self.modelo = modelo or os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self._enviar = enviar or _enviar_http

    def _llamar(self, sistema, mensaje):
        url = ("https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.modelo}:generateContent")
        cuerpo = {"system_instruction": {"parts": [{"text": sistema}]},
                  "contents": [{"role": "user", "parts": [{"text": mensaje}]}],
                  "generationConfig": {"maxOutputTokens": 1500}}
        cabeceras = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        respuesta = self._enviar(url, cabeceras, cuerpo)
        partes = respuesta["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in partes)


def crear_proveedor():
    """Claude si hay ANTHROPIC_API_KEY, Gemini si hay GEMINI_API_KEY; si no, modo local."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return ProveedorClaude(api_key=os.getenv("ANTHROPIC_API_KEY"))
        except Exception:
            pass
    clave = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if clave:
        return ProveedorGemini(clave)
    return ProveedorLocal()


class AsistenteSoporte:
    def __init__(self, repo, proveedor=None, reloj=None):
        self.repo = repo
        self.proveedor = proveedor or ProveedorLocal()
        self.reloj = reloj or datetime.now
        self.fallos_proveedor = 0

    def clasificar(self, mensaje):
        texto = _normalizar(mensaje)
        if any(p in texto for regla in REGLAS_FALLA for p in regla[0]):
            return "falla"
        if PATRON_MEDIDAS.search(texto) or any(
                p in texto for p in ("cotiz", "precio", "cuanto cuesta", "cuanto sale")):
            return "cotizar"
        if any(p in texto for p in ("diferencia", "tipos", "catalogo", "material",
                                     "neon", "acrilico", "caja")):
            return "catalogo"
        return "otro"

    def atender(self, mensaje, cliente="Cliente"):
        texto = _normalizar(mensaje)
        intencion = self.clasificar(mensaje)
        ticket = cotizacion = None
        if intencion == "falla":
            borrador, ticket = self._falla(texto, cliente, mensaje)
        elif intencion == "cotizar":
            borrador, cotizacion = self._cotizar(texto)
        elif intencion == "catalogo":
            borrador = self._catalogo(texto)
        else:
            borrador = ("Puedo ayudarle a conocer el catalogo, cotizar un letrero "
                        "(indique medidas, por ejemplo 1.2 x 0.6) o reportar una falla.")
        return {"intencion": intencion, "respuesta": self._redactar(mensaje, borrador),
                "ticket": ticket, "cotizacion": cotizacion}

    def _redactar(self, mensaje, borrador):
        try:
            texto = self.proveedor.generar(SISTEMA, mensaje, borrador)
            return texto.strip() or borrador
        except Exception:
            self.fallos_proveedor += 1
            return borrador

    def _tipos_mencionados(self, texto):
        posiciones = [(texto.find(p), c) for p, c in PALABRAS_TIPO.items() if p in texto]
        return [clave for _, clave in sorted(posiciones)]

    def _catalogo(self, texto):
        tipos = self._tipos_mencionados(texto)
        if len(tipos) >= 2:
            return catalogo.comparar(tipos[0], tipos[1])
        if len(tipos) == 1:
            d = catalogo.obtener_tipo(tipos[0])
            return f"{d['nombre']}: {d['descripcion']} (${d['precio_m2']:,.0f}/m2)"
        lineas = [f"{n}: ${p:,.0f}/m2" for _, n, p in catalogo.listar_tipos()]
        return "Tipos disponibles: " + "; ".join(lineas)

    def _cotizar(self, texto):
        medidas = PATRON_MEDIDAS.search(texto)
        if not medidas:
            return "Para cotizar necesito las medidas, por ejemplo: 1.2 x 0.6 metros.", None
        ancho, alto = (float(g.replace(",", ".")) for g in medidas.groups())
        tipos = self._tipos_mencionados(texto)
        tipo = tipos[0] if tipos else "neon_led"
        try:
            cot = cotizador.cotizar(tipo, ancho, alto, rgb=("rgb" in texto or "colores" in texto),
                                    instalacion="instal" in texto)
        except ValueError as error:
            return f"No pude cotizar: {error}", None
        nombre = catalogo.obtener_tipo(tipo)["nombre"]
        return (f"Cotizacion {nombre} {ancho} x {alto} m: subtotal ${cot.subtotal:,.2f}, "
                f"IVA ${cot.iva:,.2f}, total ${cot.total:,.2f}."), cot

    def _falla(self, texto, cliente, mensaje):
        for palabras, severidad, pasos in REGLAS_FALLA:
            if any(p in texto for p in palabras):
                ticket = self._crear_ticket(cliente, mensaje, severidad)
                return (f"Ticket #{ticket['id']} creado (severidad {severidad}). {pasos}"), ticket
        raise RuntimeError("clasificacion inconsistente")  # pragma: no cover

    def _crear_ticket(self, cliente, descripcion, severidad):
        ticket = {"id": self.repo.siguiente_id("tickets"), "cliente": cliente,
                  "descripcion": descripcion, "severidad": severidad, "estado": "abierto",
                  "creado": self.reloj().isoformat(timespec="seconds"),
                  "resuelto": None, "minutos_resolucion": None}
        return self.repo.agregar("tickets", ticket)

    def resolver_ticket(self, id_ticket):
        ticket = next((t for t in self.repo.cargar("tickets") if t["id"] == id_ticket), None)
        if ticket is None:
            raise KeyError(f"No existe el ticket {id_ticket}")
        if ticket["estado"] == "resuelto":
            raise ValueError("El ticket ya estaba resuelto")
        ahora = self.reloj()
        minutos = round((ahora - datetime.fromisoformat(ticket["creado"])).total_seconds() / 60, 2)
        return self.repo.actualizar("tickets", id_ticket, {
            "estado": "resuelto", "resuelto": ahora.isoformat(timespec="seconds"),
            "minutos_resolucion": minutos})

    def tickets_abiertos(self):
        return [t for t in self.repo.cargar("tickets") if t["estado"] == "abierto"]
