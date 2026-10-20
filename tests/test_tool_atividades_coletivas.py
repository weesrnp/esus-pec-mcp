from __future__ import annotations

from datetime import date
import pytest

from casos_tools import ContextoFalso
from pec_mcp.tools import atividades_coletivas


def test_listar_atividades_coletivas_filtros_e_pts(monkeypatch):
    consultas = []

    def fake_query_all(conn, sql, params):
        consultas.append((sql, params))
        return [
            {
                "atividade_id": 100,
                "data_atividade": date(2026, 3, 15),
                "unidade_cnes": "1234567",
                "unidade_nome": "UBS Central",
                "equipe_ine": "0001234567",
                "equipe_nome": "eMulti Ampliada",
                "responsavel_nome": "Dra. Juliana Prado",
                "cbo_codigo": "251510",
                "cbo_descricao": "Psicologo clinico",
                "tipo_atividade": "Reuniao de Equipe",
                "num_participantes": 8,
                "num_avaliacoes_alteradas": 0,
                "temas_reuniao_str": "Discussao de Caso / PTS, Planejamento",
                "temas_saude_str": "Saude Mental",
                "praticas_saude_str": "Matriciamento",
                "is_pse": 0,
                "is_pts": 1,
            }
        ]

    monkeypatch.setattr(atividades_coletivas, "query_all", fake_query_all)

    resultado = atividades_coletivas.listar_atividades_coletivas(
        ContextoFalso(),
        ine_equipe="0001234567",
        apenas_emulti=True,
        apenas_pts=True,
        tipo_atividade=1,
        limite=20,
    )

    assert len(resultado) == 1
    row = resultado[0]
    assert row["atividade_id"] == 100
    assert row["is_pts"] is True
    assert row["equipe_ine"] == "0001234-567"
    assert "Discussao de Caso / PTS" in row["temas_reuniao"]
    assert "Saude Mental" in row["temas_saude"]

    sql, params = consultas[0]
    assert "fci.st_tema_reuniao_disc_proj_tera = 1" in sql
    assert "fac.co_dim_tipo_atividade = %s" in sql
    assert params[-1] == 20


def test_consultar_participacao_coletiva_anonimizacao_e_validacao(monkeypatch):
    def fake_query_all(conn, sql, params):
        return [
            {
                "atividade_id": 100,
                "paciente_id": 42,
                "no_cidadao": "Carlos Eduardo Lima",
                "data_atividade": date(2026, 3, 15),
                "tipo_atividade": "Atendimento em Grupo",
                "peso_kg": 75.2,
                "altura_cm": 172.0,
                "st_avaliacao_alterada": 1,
                "st_cessou_habito_fumar": 1,
                "st_abandonou_grupo": 0,
            }
        ]

    monkeypatch.setattr(atividades_coletivas, "query_all", fake_query_all)

    resultado = atividades_coletivas.consultar_participacao_coletiva(
        ContextoFalso(),
        atividade_id=100,
    )

    assert len(resultado) == 1
    row = resultado[0]
    assert row["paciente_initials"] == "CEL"
    assert row["peso_kg"] == 75.2
    assert row["st_cessou_habito_fumar"] is True

    with pytest.raises(ValueError, match="Informe atividade_id ou paciente_id"):
        atividades_coletivas.consultar_participacao_coletiva(ContextoFalso())


def test_listar_profissionais_atividade_coletiva_classifica_emulti(monkeypatch):
    def fake_query_all(conn, sql, params):
        return [
            {
                "atividade_id": 100,
                "profissional_id": 10,
                "profissional_nome": "Dra. Juliana Prado",
                "cbo_codigo": "251510",
                "cbo_descricao": "Psicologo clinico",
                "equipe_ine": "0001234567",
            },
            {
                "atividade_id": 100,
                "profissional_id": 20,
                "profissional_nome": "Dr. Fernando Santos",
                "cbo_codigo": "223208",
                "cbo_descricao": "Cirurgiao-dentista",
                "equipe_ine": "0001234567",
            },
        ]

    monkeypatch.setattr(atividades_coletivas, "query_all", fake_query_all)

    resultado = atividades_coletivas.listar_profissionais_atividade_coletiva(
        ContextoFalso(),
        atividade_id=100,
    )

    assert len(resultado) == 2
    assert resultado[0]["is_emulti"] is True  # 251510 é CBO de eMulti
    assert resultado[1]["is_emulti"] is False  # 223208 é eSB / eSF
    assert resultado[0]["equipe_ine"] == "0001234-567"

    with pytest.raises(ValueError, match="atividade_id deve ser um inteiro positivo"):
        atividades_coletivas.listar_profissionais_atividade_coletiva(ContextoFalso(), atividade_id=0)
