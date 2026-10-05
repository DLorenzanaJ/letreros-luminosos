import os

import pytest

from app.repositorio import RepositorioJSON


def test_agregar_y_cargar(tmp_path):
    repo = RepositorioJSON(str(tmp_path))
    repo.agregar("x", {"id": 1})
    assert repo.cargar("x") == [{"id": 1}] and repo.siguiente_id("x") == 2


def test_repositorio_recupera_archivo_corrupto(tmp_path):
    repo = RepositorioJSON(str(tmp_path))
    with open(os.path.join(str(tmp_path), "x.json"), "w") as f:
        f.write("{roto")
    assert repo.cargar("x") == []
    assert os.path.exists(os.path.join(str(tmp_path), "x.json.corrupto"))


def test_actualizar_inexistente(tmp_path):
    with pytest.raises(KeyError):
        RepositorioJSON(str(tmp_path)).actualizar("x", 1, {})
