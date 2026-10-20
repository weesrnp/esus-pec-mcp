"""
Ferramentas para auditoria e acompanhamento de Ações Coletivas e Equipe Multiprofissional (eMulti / Indicadores M1 e M2).
Baseado nas tabelas fato do Data Warehouse do e-SUS PEC:
  - tb_fat_atividade_coletiva: cabeçalho da ação, reuniões de equipe, temas e práticas em saúde;
  - tb_fat_atvdd_coletiva_int: pautas de reuniões de equipe (Discussão de Caso / PTS para o Indicador M2);
  - tb_fat_atvdd_coletiva_part: participantes das atividades com proteção estrita de privacidade (sem CPF/CNS);
  - tb_fat_atvdd_coletiva_propart: profissionais participantes e condutores das atividades (matriciamento M2).
"""

from __future__ import annotations

import re
from typing import List, Optional

from mcp.server.fastmcp import Context

from ..db import query_all
from ..domain.patient import to_initials
from ..models import (
    AtividadeColetivaResult,
    ParticipacaoColetivaResult,
    ProfissionalAtividadeColetivaResult,
)
from . import get_db_conn, to_iso_date

_TETO_ATIVIDADES_COLETIVAS = 200

# 28 CBOs oficiais da equipe eMulti (Portaria GM/MS nº 9.584/2025)
EMULTI_CBOS = frozenset(
    {
        "515305",  # Arte Educador
        "251605",  # Assistente Social
        "223445",  # Farmacêutico Clínico/Hospitalar
        "223405",  # Farmacêutico Geral
        "223605",  # Fisioterapeuta Geral
        "223810",  # Fonoaudiólogo
        "225105",  # Médico Acupunturista
        "225120",  # Médico Cardiologista
        "225125",  # Médico Paliativista
        "225135",  # Médico Dermatologista
        "225155",  # Médico Endocrinologista
        "225180",  # Médico Geriatra
        "225250",  # Médico Ginecologista/Obstetra
        "225140",  # Médico Hansenologista
        "225195",  # Médico Homeopata
        "225103",  # Médico Infectologista
        "225124",  # Médico Pediatra
        "225133",  # Médico Psiquiatra
        "223305",  # Médico Veterinário
        "223505",  # Enfermeiro Geral / eMulti
        "223580",  # Enfermeiro Estomaterapeuta
        "223545",  # Enfermeiro Obstétrico
        "223555",  # Enfermeiro Puericultor/Pediátrico
        "223710",  # Nutricionista
        "224140",  # Profissional de Educação Física na Saúde
        "251510",  # Psicólogo Clínico
        "131225",  # Sanitarista
        "223905",  # Terapeuta Ocupacional
    }
)


def _format_ine(code: Optional[str]) -> Optional[str]:
    """Formata código INE de 10 dígitos com separador para evitar colisão com regex de telefone."""
    if not code:
        return None
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    if len(digits) == 10:
        return f"{digits[:7]}-{digits[7:]}"
    return str(code)


def _is_emulti_cbo(code: Optional[str]) -> bool:
    if not code:
        return False
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    return digits in EMULTI_CBOS


def _split_temas(text: Optional[str]) -> list[str]:
    if not text:
        return []
    return [t.strip() for t in text.split(",") if t.strip()]


_SQL_ATIVIDADES_COLETIVAS = """
SELECT
    fac.co_seq_fat_atividade_coletiva AS atividade_id,
    t.dt_registro::text AS data_atividade,
    du.nu_cnes AS unidade_cnes,
    du.no_unidade_saude AS unidade_nome,
    de.nu_ine AS equipe_ine,
    de.no_equipe AS equipe_nome,
    dprof.no_profissional AS responsavel_nome,
    dcbo.nu_cbo AS cbo_codigo,
    dcbo.no_cbo AS cbo_descricao,
    dta.ds_tipo_atividade AS tipo_atividade,
    COALESCE(fac.nu_participantes, 0) AS num_participantes,
    COALESCE(fac.nu_avaliacoes_alteradas, 0) AS num_avaliacoes_alteradas,
    fac.ds_filtro_tema_reuniao AS temas_reuniao_str,
    fac.ds_filtro_tema_para_saude AS temas_saude_str,
    fac.ds_filtro_pratica_em_saude AS praticas_saude_str,
    CASE
        WHEN fac.st_pse_educacao = 1 OR fac.st_pse_saude = 1 OR fac.co_dim_inep IS NOT NULL THEN 1
        ELSE 0
    END AS is_pse,
    COALESCE(fci.st_tema_reuniao_disc_proj_tera, 0) AS is_pts
FROM tb_fat_atividade_coletiva fac
LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fac.co_dim_tempo
LEFT JOIN tb_dim_unidade_saude du ON du.co_seq_dim_unidade_saude = fac.co_dim_unidade_saude
LEFT JOIN tb_dim_equipe de ON de.co_seq_dim_equipe = fac.co_dim_equipe
LEFT JOIN tb_dim_profissional dprof ON dprof.co_seq_dim_profissional = fac.co_dim_profissional
LEFT JOIN tb_dim_cbo dcbo ON dcbo.co_seq_dim_cbo = fac.co_dim_cbo
LEFT JOIN tb_dim_tipo_atividade dta ON dta.co_seq_dim_tipo_atividade = fac.co_dim_tipo_atividade
LEFT JOIN tb_fat_atvdd_coletiva_int fci ON fci.co_fat_atividade_coletiva = fac.co_seq_fat_atividade_coletiva
WHERE 1=1
  {where_clauses}
ORDER BY fac.co_seq_fat_atividade_coletiva DESC
LIMIT %s;
"""


def listar_atividades_coletivas(
    ctx: Context,
    ine_equipe: Optional[str] = None,
    cbo_codigo: Optional[str] = None,
    apenas_emulti: bool = False,
    apenas_pts: bool = False,
    tipo_atividade: Optional[int] = None,
    limite: int = 50,
) -> List[AtividadeColetivaResult]:
    """
    Lista ações coletivas, reuniões de equipe e atendimentos em grupo.

    Permite filtrar atividades conduzidas por profissionais eMulti (Indicador M1)
    e reuniões com Discussão de Caso / Projeto Terapêutico Singular - PTS (Indicador M2).
    """
    conn = get_db_conn(ctx)
    safe_limit = max(1, min(int(limite), _TETO_ATIVIDADES_COLETIVAS))

    where_clauses: list[str] = []
    params: list = []

    if ine_equipe and ine_equipe.strip():
        clean_ine = re.sub(r"\D", "", ine_equipe.strip())
        where_clauses.append("AND de.nu_ine LIKE %s")
        params.append(f"{clean_ine}%")

    if cbo_codigo and cbo_codigo.strip():
        clean_cbo = re.sub(r"\D", "", cbo_codigo.strip())
        where_clauses.append("AND dcbo.nu_cbo LIKE %s")
        params.append(f"{clean_cbo}%")

    if apenas_emulti:
        cbos_sql = ", ".join(f"'{c}'" for c in sorted(EMULTI_CBOS))
        where_clauses.append(f"AND dcbo.nu_cbo IN ({cbos_sql})")

    if apenas_pts:
        where_clauses.append("AND fci.st_tema_reuniao_disc_proj_tera = 1")

    if tipo_atividade is not None and int(tipo_atividade) > 0:
        where_clauses.append("AND fac.co_dim_tipo_atividade = %s")
        params.append(int(tipo_atividade))

    where_sql = "\n  ".join(where_clauses)
    sql = _SQL_ATIVIDADES_COLETIVAS.format(where_clauses=where_sql)
    params.append(safe_limit)

    rows = query_all(conn, sql, tuple(params))
    return [
        AtividadeColetivaResult(
            atividade_id=int(row.get("atividade_id") or 0),
            data_atividade=to_iso_date(row.get("data_atividade")),
            unidade_cnes=row.get("unidade_cnes"),
            unidade_nome=row.get("unidade_nome"),
            equipe_ine=_format_ine(row.get("equipe_ine")),
            equipe_nome=row.get("equipe_nome"),
            responsavel_nome=row.get("responsavel_nome"),
            cbo_codigo=row.get("cbo_codigo"),
            cbo_descricao=row.get("cbo_descricao"),
            tipo_atividade=row.get("tipo_atividade"),
            num_participantes=int(row.get("num_participantes") or 0),
            num_avaliacoes_alteradas=int(row.get("num_avaliacoes_alteradas") or 0),
            temas_reuniao=_split_temas(row.get("temas_reuniao_str")),
            temas_saude=_split_temas(row.get("temas_saude_str")),
            praticas_saude=_split_temas(row.get("praticas_saude_str")),
            is_pse=bool(row.get("is_pse")),
            is_pts=bool(row.get("is_pts")),
        )
        for row in rows
    ]


_SQL_PARTICIPACAO_COLETIVA = """
SELECT
    fcp.co_fat_atividade_coletiva AS atividade_id,
    cp.co_cidadao AS paciente_id,
    c.no_cidadao,
    t.dt_registro::text AS data_atividade,
    dta.ds_tipo_atividade AS tipo_atividade,
    fcp.nu_participante_peso AS peso_kg,
    fcp.nu_participante_altura AS altura_cm,
    COALESCE(fcp.st_avaliacao_alterada, 0) AS st_avaliacao_alterada,
    COALESCE(fcp.st_pcnt_cessou_habito_fumar, 0) AS st_cessou_habito_fumar,
    COALESCE(fcp.st_pcnt_abandonou_grupo, 0) AS st_abandonou_grupo
FROM tb_fat_atvdd_coletiva_part fcp
JOIN tb_fat_atividade_coletiva fac ON fac.co_seq_fat_atividade_coletiva = fcp.co_fat_atividade_coletiva
LEFT JOIN tb_fat_cidadao_pec cp ON cp.co_seq_fat_cidadao_pec = fcp.co_fat_cidadao_pec
LEFT JOIN tb_cidadao c ON c.co_seq_cidadao = cp.co_cidadao
LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fac.co_dim_tempo
LEFT JOIN tb_dim_tipo_atividade dta ON dta.co_seq_dim_tipo_atividade = fac.co_dim_tipo_atividade
WHERE 1=1
  {where_clauses}
ORDER BY fcp.co_seq_fat_atvdd_cltv_part DESC
LIMIT %s;
"""


def consultar_participacao_coletiva(
    ctx: Context,
    atividade_id: Optional[int] = None,
    paciente_id: Optional[int] = None,
    limite: int = 50,
) -> List[ParticipacaoColetivaResult]:
    """
    Consulta o registro anônimo de participantes de atividades coletivas.

    Blindado sob LGPD: não expõe identificadores civis (apenas iniciais e métricas de saúde).
    Exige informar pelo menos atividade_id ou paciente_id.
    """
    has_atv = atividade_id is not None and int(atividade_id) > 0
    has_pac = paciente_id is not None and int(paciente_id) > 0
    if not (has_atv or has_pac):
        raise ValueError("Informe atividade_id ou paciente_id válido.")

    conn = get_db_conn(ctx)
    safe_limit = max(1, min(int(limite), _TETO_ATIVIDADES_COLETIVAS))

    where_clauses: list[str] = []
    params: list = []

    if has_atv:
        where_clauses.append("AND fcp.co_fat_atividade_coletiva = %s")
        params.append(int(atividade_id))  # type: ignore

    if has_pac:
        where_clauses.append("AND cp.co_cidadao = %s")
        params.append(int(paciente_id))  # type: ignore

    where_sql = "\n  ".join(where_clauses)
    sql = _SQL_PARTICIPACAO_COLETIVA.format(where_clauses=where_sql)
    params.append(safe_limit)

    rows = query_all(conn, sql, tuple(params))
    return [
        ParticipacaoColetivaResult(
            atividade_id=int(row.get("atividade_id") or 0),
            paciente_id=(
                int(row.get("paciente_id"))
                if row.get("paciente_id") is not None
                else None
            ),
            paciente_initials=to_initials(row.get("no_cidadao")),
            data_atividade=to_iso_date(row.get("data_atividade")),
            tipo_atividade=row.get("tipo_atividade"),
            peso_kg=(
                float(row.get("peso_kg"))
                if row.get("peso_kg") is not None
                else None
            ),
            altura_cm=(
                float(row.get("altura_cm"))
                if row.get("altura_cm") is not None
                else None
            ),
            st_avaliacao_alterada=bool(row.get("st_avaliacao_alterada")),
            st_cessou_habito_fumar=bool(row.get("st_cessou_habito_fumar")),
            st_abandonou_grupo=bool(row.get("st_abandonou_grupo")),
        )
        for row in rows
    ]


_SQL_PROFISSIONAIS_ATIVIDADE = """
SELECT
    fcpp.co_fat_atividade_coletiva AS atividade_id,
    fcpp.co_dim_profssinal_participante AS profissional_id,
    dprof.no_profissional AS profissional_nome,
    dcbo.nu_cbo AS cbo_codigo,
    dcbo.no_cbo AS cbo_descricao,
    de.nu_ine AS equipe_ine
FROM tb_fat_atvdd_coletiva_propart fcpp
LEFT JOIN tb_dim_profissional dprof ON dprof.co_seq_dim_profissional = fcpp.co_dim_profssinal_participante
LEFT JOIN tb_dim_cbo dcbo ON dcbo.co_seq_dim_cbo = fcpp.co_dim_cbo_participante
LEFT JOIN tb_dim_equipe de ON de.co_seq_dim_equipe = fcpp.co_dim_equipe
WHERE fcpp.co_fat_atividade_coletiva = %s
ORDER BY fcpp.co_seq_fat_atvdd_cltv_propart ASC
LIMIT %s;
"""


def listar_profissionais_atividade_coletiva(
    ctx: Context,
    atividade_id: int,
) -> List[ProfissionalAtividadeColetivaResult]:
    """
    Lista profissionais condutores e participantes de uma atividade coletiva.

    Permite auditar compartilhamento de cuidado e ações conjuntas eMulti / Atenção Primária (Indicador M2).
    """
    if atividade_id is None or int(atividade_id) <= 0:
        raise ValueError("atividade_id deve ser um inteiro positivo.")

    conn = get_db_conn(ctx)
    aid = int(atividade_id)
    safe_limit = 50

    rows = query_all(conn, _SQL_PROFISSIONAIS_ATIVIDADE, (aid, safe_limit))
    return [
        ProfissionalAtividadeColetivaResult(
            atividade_id=aid,
            profissional_id=(
                int(row.get("profissional_id"))
                if row.get("profissional_id") is not None
                else None
            ),
            profissional_nome=row.get("profissional_nome"),
            cbo_codigo=row.get("cbo_codigo"),
            cbo_descricao=row.get("cbo_descricao"),
            is_emulti=_is_emulti_cbo(row.get("cbo_codigo")),
            equipe_ine=_format_ine(row.get("equipe_ine")),
        )
        for row in rows
    ]


__all__ = [
    "EMULTI_CBOS",
    "listar_atividades_coletivas",
    "consultar_participacao_coletiva",
    "listar_profissionais_atividade_coletiva",
]
