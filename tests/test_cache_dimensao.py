"""Testes unitários da camada de cache LRU/TTL para dimensões estáticas (Pilar 4)."""

import time
from unittest.mock import MagicMock

from pec_mcp.cache import _CACHE, cached_dimension, clear_dimension_cache


def test_cached_dimension_armazena_e_reutiliza():
    clear_dimension_cache()
    mock_db = MagicMock(return_value=[{"id": 1, "nome": "UBS Central"}])

    @cached_dimension(ttl_seconds=10)
    def consulta_ubs(ctx, apenas_ativas=True):
        return mock_db()

    ctx1 = MagicMock()
    ctx2 = MagicMock()

    # Primeira chamada: executa a função
    res1 = consulta_ubs(ctx1, apenas_ativas=True)
    assert res1 == [{"id": 1, "nome": "UBS Central"}]
    assert mock_db.call_count == 1

    # Segunda chamada com outro contexto MCP: usa o cache
    res2 = consulta_ubs(ctx2, apenas_ativas=True)
    assert res2 == [{"id": 1, "nome": "UBS Central"}]
    assert mock_db.call_count == 1

    # Chamada com parâmetro diferente: nova consulta
    consulta_ubs(ctx1, apenas_ativas=False)
    assert mock_db.call_count == 2


def test_cached_dimension_expira_apos_ttl():
    clear_dimension_cache()
    mock_fn = MagicMock(return_value="resultado")

    @cached_dimension(ttl_seconds=1)
    def consulta_rapida(ctx):
        return mock_fn()

    consulta_rapida(MagicMock())
    assert mock_fn.call_count == 1

    # Espera expirar o TTL de 1 segundo
    time.sleep(1.1)
    consulta_rapida(MagicMock())
    assert mock_fn.call_count == 2
