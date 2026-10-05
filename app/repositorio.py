"""Capa de almacenamiento. Hoy usa archivos JSON; en la Fase 2 se reemplaza
por SQLite manteniendo la misma interfaz (cargar, guardar, agregar, ...)."""
import json
import os


class RepositorioJSON:
    def __init__(self, carpeta="datos"):
        self.carpeta = carpeta
        os.makedirs(carpeta, exist_ok=True)

    def _ruta(self, nombre):
        return os.path.join(self.carpeta, f"{nombre}.json")

    def cargar(self, nombre):
        ruta = self._ruta(nombre)
        if not os.path.exists(ruta):
            return []
        try:
            with open(ruta, encoding="utf-8") as archivo:
                return json.load(archivo)
        except json.JSONDecodeError:
            # Recuperabilidad: se conserva el archivo dañado y se inicia vacío
            os.replace(ruta, ruta + ".corrupto")
            return []

    def guardar(self, nombre, registros):
        with open(self._ruta(nombre), "w", encoding="utf-8") as archivo:
            json.dump(registros, archivo, ensure_ascii=False, indent=2)

    def agregar(self, nombre, registro):
        registros = self.cargar(nombre)
        registros.append(registro)
        self.guardar(nombre, registros)
        return registro

    def siguiente_id(self, nombre):
        return max((r["id"] for r in self.cargar(nombre)), default=0) + 1

    def actualizar(self, nombre, id_, cambios):
        registros = self.cargar(nombre)
        for registro in registros:
            if registro["id"] == id_:
                registro.update(cambios)
                self.guardar(nombre, registros)
                return registro
        raise KeyError(f"No existe el registro {id_} en {nombre}")
