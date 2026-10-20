"""
Unit tests para vacinas.py sem necessidade de banco de dados real.
Verifica filtros de imunobiológico, status de validação e ordenação de limite.
"""

from __future__ import annotations

from datetime import date
from pec_mcp.tools import vacinas


class _Context:
    state = {"db_conn": object()}


def test_listar_vacinas_paciente_unit(monkeypatch):
    captured: dict[str, object] = {}

    def fake_query_all(_conn, sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [
            {
                "paciente_id": 1,
                "imunobiologico": "Vacina Pentavalente",
                "sigla": "Penta",
                "dose": "1a Dose",
                "data_aplicacao": date(2025, 5, 10),
                "lote": "LOTE999",
                "origem_registro": "aplicada",
                "registro_valido": True,
            }
        ]

    monkeypatch.setattr(vacinas, "query_all", fake_query_all)
    result = vacinas.listar_vacinas_paciente(
        _Context(), paciente_id=1, imunobiologico="penta", apenas_validas=True, limite=25
    )

    assert len(result) == 1
    assert result[0]["paciente_id"] == 1
    assert result[0]["imunobiologico"] == "Vacina Pentavalente"
    assert result[0]["data_aplicacao"] == "2025-05-10"
    assert result[0]["registro_valido"] is True
    assert captured["params"][-1] == 25
    sql_str = str(captured["sql"])
    assert "COALESCE(imuno.st_registro_valido, 1) <> 0" in sql_str
    assert "imuno.no_imunobiologico ILIKE %s" in sql_str
