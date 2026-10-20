from __future__ import annotations

from datetime import date
import pytest

from casos_tools import ContextoFalso
from pec_mcp.tools import pse


def test_listar_acoes_pse_mapeamento_e_filtros(monkeypatch):
    consultas = []

    def fake_query_all(conn, sql, params):
        consultas.append((sql, params))
        return [
            {
                "atividade_id": 300,
                "inep_escola": "41096501",
                "nome_escola": "Colegio Estadual Duque de Caxias",
                "data_atividade": date(2026, 3, 20),
                "equipe_ine": "0001234567",
                "equipe_nome": "Equipe 1",
                "responsavel_nome": "Dra. Helena Fontes",
                "cbo_codigo": "223505",
                "num_participantes": 45,
                "verificacao_vacinal": 1,
                "avaliacao_antropometrica": 1,
                "saude_bucal_escovacao": 1,
                "saude_bucal_fluor": 0,
                "saude_ocular": 0,
                "saude_auditiva": 0,
            }
        ]

    monkeypatch.setattr(pse, "query_all", fake_query_all)

    resultado = pse.listar_acoes_pse(
        ContextoFalso(),
        inep_escola="41096501",
        ine_equipe="0001234567",
        acao_tematica="vacinacao",
        limite=30,
    )

    assert len(resultado) == 1
    row = resultado[0]
    assert row["atividade_id"] == 300
    assert row["inep_escola"] == "41096501"
    assert row["equipe_ine"] == "0001234-567"
    assert row["verificacao_vacinal"] is True
    assert row["avaliacao_antropometrica"] is True
    assert row["saude_bucal_escovacao"] is True
    assert row["saude_ocular"] is False

    sql, params = consultas[0]
    assert "inep.nu_identificador LIKE %s" in sql
    assert "de.nu_ine LIKE %s" in sql
    assert "ext.st_prat_saude_situacao_vacinal = 1" in sql
    assert params[-1] == 30
