from __future__ import annotations

from datetime import date, datetime
import pytest

from casos_tools import ContextoFalso
from pec_mcp.tools import saude_bucal


def test_listar_atendimentos_odonto_mapeamento_e_anonimizacao(monkeypatch):
    consultas = []

    def fake_query_all(conn, sql, params):
        consultas.append((sql, params))
        return [
            {
                "atendimento_id": 501,
                "paciente_id": 42,
                "no_cidadao": "Joao Pedro da Silva",
                "data_hora": datetime(2026, 4, 10, 10, 30),
                "profissional_nome": "Dr. Fernando Santos",
                "cbo_codigo": "223208",
                "cbo_descricao": "Cirurgiao-dentista - clinico geral",
                "unidade_cnes": "1234567",
                "unidade_nome": "ESF Centro",
                "equipe_ine": "0001234567",
                "tipo_consulta": "Consulta Odontologica Programatica",
                "tipo_atendimento": "Consulta no consultorio",
                "st_gestante": 1,
                "st_conduta_tratamento_concluid": 1,
                "st_fornecimento_escova_dental": 1,
                "st_fornecimento_creme_dental": 1,
                "st_fornecimento_fio_dental": 1,
                "st_vigil_abscesso_dentoalveola": 0,
                "st_vigil_dor_dente": 1,
            }
        ]

    monkeypatch.setattr(saude_bucal, "query_all", fake_query_all)

    resultado = saude_bucal.listar_atendimentos_odonto(
        ContextoFalso(),
        paciente_id=42,
        cbo_codigo="223208",
        apenas_primeira_consulta=True,
        apenas_tratamento_concluido=True,
        apenas_gestantes=True,
        limite=10,
    )

    assert len(resultado) == 1
    row = resultado[0]
    assert row["atendimento_id"] == 501
    assert row["paciente_id"] == 42
    assert row["paciente_initials"] == "JPS"
    assert row["st_gestante"] is True
    assert row["st_tratamento_concluido"] is True
    assert row["fornecimento_escova"] is True
    assert row["vigilancia_dor_dente"] is True

    # Valida parâmetros da query e safe limit
    sql, params = consultas[0]
    assert "fao.co_dim_tipo_consulta = 1" in sql
    assert "fao.st_conduta_tratamento_concluid = 1" in sql
    assert "fao.st_gestante = 1" in sql
    assert params[-1] == 10


def test_listar_atendimentos_odonto_valida_paciente_id():
    with pytest.raises(ValueError, match="paciente_id deve ser um inteiro positivo"):
        saude_bucal.listar_atendimentos_odonto(ContextoFalso(), paciente_id=0)


def test_listar_procedimentos_odonto_classificacao_indicadores(monkeypatch):
    def fake_query_all(conn, sql, params):
        return [
            {
                "paciente_id": 42,
                "atendimento_id": 501,
                "codigo_sigtap": "0414020138",
                "nome_procedimento": "Exodontia dente permanente",
                "quantidade": 1,
                "data_realizacao": date(2026, 4, 10),
                "profissional_nome": "Dr. Fernando Santos",
                "cbo_codigo": "223208",
                "cbo_descricao": "Cirurgiao-dentista",
            },
            {
                "paciente_id": 42,
                "atendimento_id": 501,
                "codigo_sigtap": "0101020074",
                "nome_procedimento": "Aplicacao topica de fluor",
                "quantidade": 1,
                "data_realizacao": date(2026, 4, 10),
                "profissional_nome": "Dr. Fernando Santos",
                "cbo_codigo": "223208",
                "cbo_descricao": "Cirurgiao-dentista",
            },
            {
                "paciente_id": 42,
                "atendimento_id": 501,
                "codigo_sigtap": "0307010074",
                "nome_procedimento": "Tratamento restaurador atraumatico - ART",
                "quantidade": 1,
                "data_realizacao": date(2026, 4, 10),
                "profissional_nome": "Dr. Fernando Santos",
                "cbo_codigo": "223208",
                "cbo_descricao": "Cirurgiao-dentista",
            },
        ]

    monkeypatch.setattr(saude_bucal, "query_all", fake_query_all)

    resultado = saude_bucal.listar_procedimentos_odonto(
        ContextoFalso(),
        paciente_id=42,
        grupo="todos",
    )

    assert len(resultado) == 3

    # Exodontia (B3)
    assert resultado[0]["codigo_sigtap"] == "04.14.02.013-8"
    assert resultado[0]["is_exodontia"] is True
    assert resultado[0]["is_preventivo"] is False
    assert resultado[0]["is_tra_art"] is False

    # Preventivo (B4)
    assert resultado[1]["codigo_sigtap"] == "01.01.02.007-4"
    assert resultado[1]["is_exodontia"] is False
    assert resultado[1]["is_preventivo"] is True
    assert resultado[1]["is_tra_art"] is False

    # TRA / ART (B6)
    assert resultado[2]["codigo_sigtap"] == "03.07.01.007-4"
    assert resultado[2]["is_exodontia"] is False
    assert resultado[2]["is_preventivo"] is False
    assert resultado[2]["is_tra_art"] is True


def test_listar_procedimentos_odonto_filtro_grupo(monkeypatch):
    consultas = []

    def fake_query_all(conn, sql, params):
        consultas.append((sql, params))
        return []

    monkeypatch.setattr(saude_bucal, "query_all", fake_query_all)

    saude_bucal.listar_procedimentos_odonto(
        ContextoFalso(),
        paciente_id=42,
        grupo="exodontia",
    )
    assert "0414020138" in consultas[0][0]

    saude_bucal.listar_procedimentos_odonto(
        ContextoFalso(),
        paciente_id=42,
        grupo="preventivo",
    )
    assert "0101020058" in consultas[1][0]

    saude_bucal.listar_procedimentos_odonto(
        ContextoFalso(),
        paciente_id=42,
        grupo="tra_art",
    )
    assert "0307010074" in consultas[2][0]


def test_listar_problemas_odonto_mapeamento_e_filtros(monkeypatch):
    consultas = []

    def fake_query_all(conn, sql, params):
        consultas.append((sql, params))
        return [
            {
                "paciente_id": 42,
                "no_cidadao": "Maria Clara de Souza",
                "atendimento_id": 501,
                "cid_code": "K02.1",
                "cid_description": "Carie da dentina",
                "ciap_code": "D88",
                "ciap_description": "Carie dentaria",
                "situacao": "Ativo",
                "data_inicio": date(2026, 4, 10),
                "profissional_nome": "Dr. Fernando Santos",
                "cbo_codigo": "223208",
            }
        ]

    monkeypatch.setattr(saude_bucal, "query_all", fake_query_all)

    resultado = saude_bucal.listar_problemas_odonto(
        ContextoFalso(),
        paciente_id=42,
        cid_codigo="K02",
        ciap_codigo="D88",
    )

    assert len(resultado) == 1
    row = resultado[0]
    assert row["paciente_initials"] == "MCS"
    assert row["cid_code"] == "K02.1"
    assert row["ciap_code"] == "D88"
    assert row["situacao"] == "Ativo"

    sql, params = consultas[0]
    assert "UPPER(dcid.nu_cid) LIKE %s" in sql
    assert "UPPER(dciap.nu_ciap) LIKE %s" in sql
    assert params[-1] == 50
