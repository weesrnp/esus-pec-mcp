from casos_tools import ContextoFalso
from pec_mcp.tools import unidades


def _capturar(monkeypatch):
    consultas = []
    monkeypatch.setattr(unidades, "query_all", lambda conn, sql, params=None: consultas.append((sql, params)) or [])
    return consultas


def test_unidades_filtra_pelo_codigo_cnes_estavel(monkeypatch):
    consultas = _capturar(monkeypatch)
    unidades.listar_unidades_saude(ContextoFalso())
    sql, params = consultas[0]
    # O filtro usa o código CNES; o nome do tipo só aparece no SELECT.
    assert "tu.co_tipo_unidade_cnes = ANY(%s)" in sql
    assert "no_tipo_unidade_saude ILIKE" not in sql
    assert "no_tipo_unidade_saude =" not in sql
    assert params[0] == [1, 2, 32, 40, 71, 72, 74]
    assert "COALESCE(us.st_ativo, 0) = 1" in sql


def test_unidades_pode_listar_todas(monkeypatch):
    consultas = _capturar(monkeypatch)
    unidades.listar_unidades_saude(ContextoFalso(), apenas_atencao_primaria=False, incluir_inativas=True)
    sql, params = consultas[0]
    assert "co_tipo_unidade_cnes = ANY" not in sql
    assert "st_ativo, 0) = 1" not in sql
    assert params == ()
