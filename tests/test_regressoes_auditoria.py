"""
Regressões dos defeitos encontrados na auditoria de outubro/2026.

Cada teste fixa um bug que existia: se ele voltar, o teste quebra.
"""

from __future__ import annotations

import pytest

from casos_tools import ContextoFalso
from pec_mcp import db as db_module
from pec_mcp.domain.patient import mascarar_texto_livre
from pec_mcp.tools import (
    atendimentos,
    atividades_coletivas,
    gestantes,
    medicoes,
    obter_codigos_condicao_saude as codigos,
    paciente,
    saude_bucal,
    sem_consulta,
    visitas_acs,
)


def _capturar(monkeypatch, modulo, nome="query_all", retorno=None):
    consultas = []

    def falso(conn, sql, params=None):
        consultas.append((sql, params))
        return [] if retorno is None else retorno

    monkeypatch.setattr(modulo, nome, falso)
    return consultas


# ── texto livre ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "texto, proibido",
    [
        ("CPF 529.982.247-25 confirmado", "529.982.247-25"),
        ("cpf 52998224725", "52998224725"),
        ("CNS 898 0011 6012 5871", "898 0011 6012 5871"),
        ("ligar (49) 99999-8888 amanhã", "99999-8888"),
        ("tel 4999998888", "4999998888"),
        ("e-mail fulano@exemplo.com.br", "fulano@exemplo.com.br"),
    ],
)
def test_texto_livre_mascara_identificadores(texto, proibido):
    assert proibido not in mascarar_texto_livre(texto)


def test_texto_livre_preserva_dados_clinicos():
    texto = "PA 150/95, HGT 110 mg/dL, peso 72,5 kg em 10/03/2024, dieta 1500 2000 kcal"
    assert mascarar_texto_livre(texto) == texto


def test_soap_e_condicoes_saem_mascarados(monkeypatch):
    linha = {
        "atendimento_id": 1,
        "paciente_id": 1,
        "soap_s": "Paciente informa CPF 529.982.247-25",
        "condicoes": [{"condition_id": 1, "observacao": "ligar 49 99999-8888"}],
    }
    _capturar(monkeypatch, atendimentos, retorno=[linha])
    [r] = atendimentos.listar_ultimos_atendimentos_soap(ContextoFalso(), paciente_id=1)
    assert "529.982.247-25" not in r["soap_s"]
    assert "99999-8888" not in r["condicoes"][0]["observacao"]


def test_soap_sem_limite_usa_padrao(monkeypatch):
    consultas = _capturar(monkeypatch, atendimentos)
    atendimentos.listar_ultimos_atendimentos_soap(ContextoFalso(), paciente_id=1, limite=None)
    sql, params = consultas[0]
    assert sql.rstrip().endswith("LIMIT %s")
    assert params[-1] == 50


# ── códigos de condição ─────────────────────────────────────────


@pytest.mark.parametrize("codigo", ["E11", "E11.9", "E119", "I10"])
def test_regex_de_cid_aceita_codigo_com_e_sem_ponto(codigo):
    assert codigos._CID_CODE_RE.match(codigo)


def test_normalizacao_colapsa_espacos_e_acha_preset():
    resultado = codigos.obter_codigos_condicao_saude(ContextoFalso(), "  Diabetes   Mellitus ")
    assert resultado["source"] == "preset"
    assert resultado["condition"] == "diabetes"


# ── identificadores consistentes entre tools ────────────────────


def test_visitas_acs_devolve_co_cidadao_e_filtra_unidade_por_cnes(monkeypatch):
    consultas = _capturar(monkeypatch, visitas_acs)
    visitas_acs.listar_visitas_acs(ContextoFalso(), unidade_saude_id=3)
    sql, params = consultas[0]
    assert "cp.co_cidadao                  AS paciente_pec_id" in sql
    assert "v.co_fat_cidadao_pec           AS paciente_pec_id" not in sql
    assert "us.co_seq_unidade_saude = %s" in sql
    assert "v.co_dim_unidade_saude = %s" not in sql


# ── gestantes e busca ativa ─────────────────────────────────────


def test_gestantes_liga_usg_pelo_prontuario(monkeypatch):
    consultas = _capturar(monkeypatch, gestantes)
    gestantes.listar_gestantes(ContextoFalso())
    sql = consultas[0][0]
    assert "ex.co_exame_requisitado = pn.co_seq_pre_natal" not in sql
    assert "er.co_prontuario = pn.co_prontuario" in sql
    assert "LIMIT 1" in sql  # no máximo uma USG por gestação
    assert "COALESCE(c.st_faleceu, 0) = 0" in sql


@pytest.mark.parametrize("tool", ["contar", "listar"])
def test_busca_ativa_exclui_obitos(monkeypatch, tool):
    nome = "query_one" if tool == "contar" else "query_all"
    retorno = {"total": 0} if tool == "contar" else None
    consultas = _capturar(monkeypatch, sem_consulta, nome, retorno)
    getattr(sem_consulta, f"{tool}_pacientes_sem_consulta")(ContextoFalso(), tipo="hipertensao")
    assert "COALESCE(c.st_faleceu, 0) = 0" in consultas[0][0]


# ── datas e glicemia ────────────────────────────────────────────


def test_data_fim_inclui_o_dia_inteiro(monkeypatch):
    consultas = _capturar(monkeypatch, medicoes)
    medicoes.listar_registros_pa(ContextoFalso(), paciente_id=1, data_fim="2024-12-31")
    sql = consultas[0][0]
    assert "m.dt_medicao < (%s::date + 1)" in sql
    assert "m.dt_medicao <= %s::timestamp" not in sql


def test_peso_e_altura_em_texto_nao_derrubam_a_consulta(monkeypatch):
    consultas = _capturar(monkeypatch, medicoes)
    medicoes.listar_registros_antropometria(ContextoFalso(), paciente_id=1)
    sql = consultas[0][0]
    assert "m.nu_medicao_peso::numeric" not in sql
    assert "m.nu_medicao_peso ~ '^[0-9]+([.,][0-9]+)?$'" in sql


def test_valor_com_virgula_vira_numero():
    assert medicoes._to_float("72,5") == 72.5
    assert medicoes._to_float("abc") is None


@pytest.mark.parametrize("modulo, tool", [(medicoes, "listar_registros_pa"), (atendimentos, "listar_ultimos_atendimentos_soap")])
def test_nome_do_profissional_usa_nome_civil_sem_nome_social(monkeypatch, modulo, tool):
    consultas = _capturar(monkeypatch, modulo)
    getattr(modulo, tool)(ContextoFalso(), paciente_id=1)
    assert "COALESCE(p.no_social_profissional, p.no_civil_profissional)" in consultas[0][0]


def test_codigo_cid_com_ponto_vira_formato_do_banco():
    from pec_mcp.tools.filters import build_condition_filters

    _, params = build_condition_filters(cid_codes=["I11.0", "e11"])
    assert params[0] == ["I110%", "E11%"]
    assert codigos._code_like("E11.9", codigos._CID_CODE_RE) == "E119%"


# ── saúde bucal ─────────────────────────────────────────────────


@pytest.mark.parametrize("codigo", ["ABPO010", "ABPO015", "ABPO016"])
def test_preventivos_abpo01x_nao_sao_exodontia(codigo):
    assert saude_bucal._is_preventivo(codigo)
    assert not saude_bucal._is_exodontia(codigo)


def test_b3_conta_so_exodontia_de_permanente():
    assert saude_bucal._is_exodontia("04.14.02.013-8")
    assert saude_bucal._is_exodontia("ABPO012")
    assert not saude_bucal._is_exodontia("04.14.02.012-0")  # decíduo
    assert not saude_bucal._is_exodontia("ABPO011")  # decíduo


# ── atividades coletivas ────────────────────────────────────────


def test_pts_nao_multiplica_linhas(monkeypatch):
    consultas = _capturar(monkeypatch, atividades_coletivas)
    atividades_coletivas.listar_atividades_coletivas(ContextoFalso(), apenas_pts=True)
    sql = consultas[0][0]
    assert "LEFT JOIN tb_fat_atvdd_coletiva_int" not in sql
    assert sql.count("EXISTS (SELECT 1 FROM tb_fat_atvdd_coletiva_int") == 2


# ── busca por nome ──────────────────────────────────────────────


def test_prefixo_de_nome_escapa_curingas(monkeypatch):
    consultas = _capturar(monkeypatch, paciente)
    paciente.capturar_paciente(ContextoFalso(), name_starts_with="%_x")
    assert consultas[0][1][0] == "\\%\\_x%"


def test_prefixo_de_nome_curto_demais_e_recusado():
    with pytest.raises(ValueError, match="2 caracteres"):
        paciente.capturar_paciente(ContextoFalso(), name_starts_with="%")


# ── conexão ─────────────────────────────────────────────────────


def test_conexao_reabre_depois_de_cair(monkeypatch):
    abertas = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql, params=None):
            pass

    class Conn:
        def __init__(self):
            self.closed = 0
            abertas.append(self)

        def set_session(self, **kwargs):
            pass

        def cursor(self, *a, **k):
            return Cursor()

        def close(self):
            self.closed = 1

    monkeypatch.setattr(db_module, "get_connection", lambda dsn: Conn())
    conexao = db_module.ConexaoSomenteLeitura("dsn")
    conexao.cursor()
    abertas[0].closed = 2  # psycopg2 marca 2 quando o servidor derruba a conexão
    conexao.cursor()
    assert len(abertas) == 2
