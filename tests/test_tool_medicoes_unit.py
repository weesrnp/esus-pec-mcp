"""
Unit tests para medicoes.py sem necessidade de banco de dados real.
Verifica cálculo de IMC, parsing de PA, filtros de HGT e respeito a cancelados.
"""

from __future__ import annotations

from datetime import datetime
from pec_mcp.tools import medicoes


class _Context:
    state = {"db_conn": object()}


def test_medicoes_from_pec_ignora_cancelados():
    normalized = " ".join(medicoes._FROM_PEC.lower().split())
    assert "coalesce(ap.st_cancelado, 0) = 0" in normalized


def test_listar_registros_antropometria_unit(monkeypatch):
    captured: dict[str, object] = {}

    def fake_query_all(_conn, sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [
            {
                "paciente_id": 1,
                "peso_kg": "70.5",
                "altura_cm": "165.0",
                "imc": "25.89",
                "data_medicao": datetime(2026, 2, 1, 10, 0),
                "prof_id": 10,
                "prof_nome": "Dr. Silva",
                "cbo_codigo": "225125",
                "cbo_nome": "Médico",
                "origem": "pec",
            }
        ]

    monkeypatch.setattr(medicoes, "query_all", fake_query_all)
    result = medicoes.listar_registros_antropometria(
        _Context(), paciente_id=1, limite=10
    )

    assert len(result) == 1
    assert result[0]["paciente_id"] == 1
    assert result[0]["peso_kg"] == 70.5
    assert result[0]["altura_cm"] == 165.0
    assert result[0]["imc"] == 25.89
    assert result[0]["tipo_profissional"] == "médico"
    assert captured["params"][-1] == 10


def test_listar_registros_pa_unit(monkeypatch):
    def fake_query_all(_conn, sql, params):
        return [
            {
                "paciente_id": 1,
                "pas_str": "120",
                "pad_str": "80",
                "pressao_raw": "120/80",
                "data_medicao": datetime(2026, 2, 1, 10, 0),
                "prof_id": 10,
                "prof_nome": "Enf. Maria",
                "cbo_codigo": "223505",
                "cbo_nome": "Enfermeiro",
                "origem": "pec",
            }
        ]

    monkeypatch.setattr(medicoes, "query_all", fake_query_all)
    result = medicoes.listar_registros_pa(_Context(), paciente_id=1, limite=5)

    assert len(result) == 1
    assert result[0]["pas"] == 120
    assert result[0]["pad"] == 80
    assert result[0]["tipo_profissional"] == "enfermeiro"


def test_listar_registros_hgt_unit(monkeypatch):
    captured: dict[str, object] = {}

    def fake_query_all(_conn, sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [
            {
                "paciente_id": 1,
                "valor_str": "110",
                "tp_glicemia": 0,
                "data_medicao": datetime(2026, 2, 1, 10, 0),
                "prof_id": 15,
                "prof_nome": "ACS Joao",
                "cbo_codigo": "515105",
                "cbo_nome": "Agente Comunitario",
                "origem": "visita_domiciliar",
            }
        ]

    monkeypatch.setattr(medicoes, "query_all", fake_query_all)
    result = medicoes.listar_registros_hgt(
        _Context(), paciente_id=1, momento="jejum", limite=20
    )

    assert len(result) == 1
    assert result[0]["valor_mg_dl"] == 110.0
    assert result[0]["momento_afericao"] == "Jejum"
    assert result[0]["tipo_profissional"] == "ACS"
    assert "m.tp_glicemia = %s" in str(captured["sql"])
