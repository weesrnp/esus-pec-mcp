"""
Ferramentas para auditoria e acompanhamento clínico de Saúde Bucal (eSB / Indicadores B1-B6).
Baseado nas tabelas fato do Data Warehouse do e-SUS PEC:
  - tb_fat_atendimento_odonto: consultas e atendimentos odontológicos individuais;
  - tb_fat_atend_odonto_proced: procedimentos realizados na cadeira odontológica;
  - tb_fat_atend_odonto_problemas: diagnósticos, condições e problemas bucais.
"""

from __future__ import annotations

import re
from typing import List, Optional

from mcp.server.fastmcp import Context

from ..db import query_all
from ..domain.patient import to_initials
from ..models import (
    AtendimentoOdontoResult,
    ProblemaOdontoResult,
    ProcedimentoOdontoResult,
)
from . import get_db_conn, to_iso_date

_TETO_SAUDE_BUCAL = 200

# Conjuntos de códigos SIGTAP e equivalências CDS (ABPO*).
# B3 conta exodontia de dente PERMANENTE: 04.14.02.013-8, 04.14.02.014-6 e ABPO012.
# Exodontia de decíduo (04.14.02.012-0 / ABPO011) fica fora do indicador.
_EXODONTIAS_SIGTAP = frozenset({"0414020138", "0414020146", "ABPO012"})
_PREVENTIVOS_SIGTAP = frozenset(
    {
        "0101020058",
        "0101020066",
        "0101020074",
        "0101020082",
        "0101020104",
        "0101020120",
        "0307030040",
        "ABPO003",  # cariostático
        "ABPO004",  # selante
        "ABPO005",  # flúor tópico
        "ABPO010",  # evidenciação de placa
        "ABPO015",  # orientação de higiene bucal
        "ABPO016",  # profilaxia
    }
)
_TRA_ART_SIGTAP = frozenset({"0307010074"})


def _format_sigtap(code: Optional[str]) -> Optional[str]:
    """Formata código SIGTAP de 10 dígitos para a máscara padrão XX.XX.XX.XXX-X."""
    if not code:
        return None
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    if len(digits) == 10:
        return f"{digits[0:2]}.{digits[2:4]}.{digits[4:6]}.{digits[6:9]}-{digits[9]}"
    return str(code)


def _format_ine(code: Optional[str]) -> Optional[str]:
    """Formata código INE de 10 dígitos com separador para evitar colisão com regex de telefone."""
    if not code:
        return None
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    if len(digits) == 10:
        return f"{digits[:7]}-{digits[7:]}"
    return str(code)


def _is_exodontia(code: Optional[str]) -> bool:
    if not code:
        return False
    clean = re.sub(r"[.\-]", "", str(code).strip())
    return clean in _EXODONTIAS_SIGTAP


def _is_preventivo(code: Optional[str]) -> bool:
    if not code:
        return False
    clean = re.sub(r"[.\-]", "", str(code).strip())
    return clean in _PREVENTIVOS_SIGTAP


def _is_tra_art(code: Optional[str]) -> bool:
    if not code:
        return False
    clean = re.sub(r"[.\-]", "", str(code).strip())
    return clean in _TRA_ART_SIGTAP


_SQL_ATENDIMENTOS_ODONTO = """
SELECT
    fao.co_seq_fat_atd_odnt AS atendimento_id,
    cp.co_cidadao AS paciente_id,
    c.no_cidadao,
    t.dt_registro::text AS data_hora,
    dprof.no_profissional AS profissional_nome,
    dcbo.nu_cbo AS cbo_codigo,
    dcbo.no_cbo AS cbo_descricao,
    du.nu_cnes AS unidade_cnes,
    du.no_unidade_saude AS unidade_nome,
    de.nu_ine AS equipe_ine,
    dtc.ds_tipo_consulta_odonto AS tipo_consulta,
    dta.ds_tipo_atendimento AS tipo_atendimento,
    COALESCE(fao.st_gestante, 0) AS st_gestante,
    COALESCE(fao.st_conduta_tratamento_concluid, 0) AS st_conduta_tratamento_concluid,
    COALESCE(fao.st_fornecimento_escova_dental, 0) AS st_fornecimento_escova_dental,
    COALESCE(fao.st_fornecimento_creme_dental, 0) AS st_fornecimento_creme_dental,
    COALESCE(fao.st_fornecimento_fio_dental, 0) AS st_fornecimento_fio_dental,
    COALESCE(fao.st_vigil_abscesso_dentoalveola, 0) AS st_vigil_abscesso_dentoalveola,
    COALESCE(fao.st_vigil_dor_dente, 0) AS st_vigil_dor_dente
FROM tb_fat_atendimento_odonto fao
JOIN tb_fat_cidadao_pec cp ON cp.co_seq_fat_cidadao_pec = fao.co_fat_cidadao_pec
LEFT JOIN tb_cidadao c ON c.co_seq_cidadao = cp.co_cidadao
LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fao.co_dim_tempo
LEFT JOIN tb_dim_profissional dprof ON dprof.co_seq_dim_profissional = fao.co_dim_profissional_1
LEFT JOIN tb_dim_cbo dcbo ON dcbo.co_seq_dim_cbo = fao.co_dim_cbo_1
LEFT JOIN tb_dim_unidade_saude du ON du.co_seq_dim_unidade_saude = fao.co_dim_unidade_saude_1
LEFT JOIN tb_dim_equipe de ON de.co_seq_dim_equipe = fao.co_dim_equipe_1
LEFT JOIN tb_dim_tipo_consulta_odonto dtc ON dtc.co_seq_dim_tipo_cnsulta_odonto = fao.co_dim_tipo_consulta
LEFT JOIN tb_dim_tipo_atendimento dta ON dta.co_seq_dim_tipo_atendimento = fao.co_dim_tipo_atendimento
WHERE 1=1
  {where_clauses}
ORDER BY fao.co_seq_fat_atd_odnt DESC
LIMIT %s;
"""


def listar_atendimentos_odonto(
    ctx: Context,
    paciente_id: Optional[int] = None,
    cbo_codigo: Optional[str] = None,
    apenas_primeira_consulta: bool = False,
    apenas_tratamento_concluido: bool = False,
    apenas_gestantes: bool = False,
    limite: int = 50,
) -> List[AtendimentoOdontoResult]:
    """
    Lista consultas odontológicas individuais da equipe de Saúde Bucal (eSB).

    Permite auditar atendimentos com conduta de tratamento concluído (Indicador B2),
    primeira consulta odontológica programática (Indicador B1) e vigilância em saúde bucal.
    """
    conn = get_db_conn(ctx)
    safe_limit = max(1, min(int(limite), _TETO_SAUDE_BUCAL))

    where_clauses: list[str] = []
    params: list = []

    if paciente_id is not None:
        if int(paciente_id) <= 0:
            raise ValueError("paciente_id deve ser um inteiro positivo.")
        where_clauses.append("AND cp.co_cidadao = %s")
        params.append(int(paciente_id))

    if cbo_codigo and cbo_codigo.strip():
        clean_cbo = re.sub(r"\D", "", cbo_codigo.strip())
        where_clauses.append("AND dcbo.nu_cbo LIKE %s")
        params.append(f"{clean_cbo}%")

    if apenas_primeira_consulta:
        # co_dim_tipo_consulta é chave substituta; o código LEDI fica em nu_identificador
        # (1 = primeira consulta odontológica programática).
        where_clauses.append("AND dtc.nu_identificador::text = '1'")

    if apenas_tratamento_concluido:
        where_clauses.append("AND fao.st_conduta_tratamento_concluid = 1")

    if apenas_gestantes:
        where_clauses.append("AND fao.st_gestante = 1")

    where_sql = "\n  ".join(where_clauses)
    sql = _SQL_ATENDIMENTOS_ODONTO.format(where_clauses=where_sql)
    params.append(safe_limit)

    rows = query_all(conn, sql, tuple(params))
    return [
        AtendimentoOdontoResult(
            atendimento_id=int(row.get("atendimento_id") or 0),
            paciente_id=int(row.get("paciente_id") or 0),
            paciente_initials=to_initials(row.get("no_cidadao")),
            data_hora=to_iso_date(row.get("data_hora")),
            profissional_nome=row.get("profissional_nome"),
            cbo_codigo=row.get("cbo_codigo"),
            cbo_descricao=row.get("cbo_descricao"),
            unidade_cnes=row.get("unidade_cnes"),
            unidade_nome=row.get("unidade_nome"),
            equipe_ine=_format_ine(row.get("equipe_ine")),
            tipo_consulta=row.get("tipo_consulta"),
            tipo_atendimento=row.get("tipo_atendimento"),
            st_gestante=bool(row.get("st_gestante")),
            st_tratamento_concluido=bool(row.get("st_conduta_tratamento_concluid")),
            fornecimento_escova=bool(row.get("st_fornecimento_escova_dental")),
            fornecimento_creme=bool(row.get("st_fornecimento_creme_dental")),
            fornecimento_fio=bool(row.get("st_fornecimento_fio_dental")),
            vigilancia_abscesso=bool(row.get("st_vigil_abscesso_dentoalveola")),
            vigilancia_dor_dente=bool(row.get("st_vigil_dor_dente")),
        )
        for row in rows
    ]


_SQL_PROCEDIMENTOS_ODONTO = """
SELECT
    cp.co_cidadao AS paciente_id,
    fop.co_fat_atd_odnt AS atendimento_id,
    dp.co_proced AS codigo_sigtap,
    dp.ds_proced AS nome_procedimento,
    COALESCE(fop.qt_procedimentos, 1) AS quantidade,
    t.dt_registro::text AS data_realizacao,
    dprof.no_profissional AS profissional_nome,
    dcbo.nu_cbo AS cbo_codigo,
    dcbo.no_cbo AS cbo_descricao
FROM tb_fat_atend_odonto_proced fop
JOIN tb_fat_cidadao_pec cp ON cp.co_seq_fat_cidadao_pec = fop.co_fat_cidadao_pec
LEFT JOIN tb_dim_procedimento dp ON dp.co_seq_dim_procedimento = fop.co_dim_procedimento
LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fop.co_dim_tempo
LEFT JOIN tb_dim_profissional dprof ON dprof.co_seq_dim_profissional = fop.co_dim_profissional_1
LEFT JOIN tb_dim_cbo dcbo ON dcbo.co_seq_dim_cbo = fop.co_dim_cbo_1
WHERE cp.co_cidadao = %s
  {where_clauses}
ORDER BY fop.co_seq_fat_atend_odonto_proced DESC
LIMIT %s;
"""


def listar_procedimentos_odonto(
    ctx: Context,
    paciente_id: int,
    codigo_sigtap: Optional[str] = None,
    grupo: Optional[str] = None,
    limite: int = 50,
) -> List[ProcedimentoOdontoResult]:
    """
    Lista procedimentos clínicos realizados na cadeira odontológica.

    Permite auditar exodontias de dentes permanentes (Indicador B3), procedimentos
    preventivos individuais (Indicador B4) e restaurações atraumáticas TRA/ART (Indicador B6).
    """
    if paciente_id is None or int(paciente_id) <= 0:
        raise ValueError("paciente_id deve ser um inteiro positivo.")

    conn = get_db_conn(ctx)
    pid = int(paciente_id)
    safe_limit = max(1, min(int(limite), _TETO_SAUDE_BUCAL))

    where_clauses: list[str] = []
    params: list = [pid]

    if codigo_sigtap and codigo_sigtap.strip():
        clean_code = re.sub(r"[.\-]", "", codigo_sigtap.strip())
        where_clauses.append("AND dp.co_proced LIKE %s")
        params.append(f"{clean_code}%")

    if grupo and grupo.strip().lower() != "todos":
        g = grupo.strip().lower()
        # Mesmos conjuntos usados nas flags is_*, para SQL e Python não divergirem.
        codigos = None
        if g in ("exodontia", "exodontias"):
            codigos = _EXODONTIAS_SIGTAP
        elif g in ("preventivo", "preventivos"):
            codigos = _PREVENTIVOS_SIGTAP
        elif g in ("tra_art", "art", "tra"):
            codigos = _TRA_ART_SIGTAP
        else:
            raise ValueError("grupo inválido. Use: exodontia, preventivo, tra_art ou todos.")
        where_clauses.append(
            "AND REGEXP_REPLACE(dp.co_proced, '[^0-9A-Za-z]', '', 'g') = ANY(%s)"
        )
        params.append(sorted(codigos))

    where_sql = "\n  ".join(where_clauses)
    sql = _SQL_PROCEDIMENTOS_ODONTO.format(where_clauses=where_sql)
    params.append(safe_limit)

    rows = query_all(conn, sql, tuple(params))
    return [
        ProcedimentoOdontoResult(
            paciente_id=int(row.get("paciente_id") or pid),
            atendimento_id=(
                int(row.get("atendimento_id"))
                if row.get("atendimento_id") is not None
                else None
            ),
            codigo_sigtap=_format_sigtap(row.get("codigo_sigtap")),
            nome_procedimento=row.get("nome_procedimento"),
            quantidade=int(row.get("quantidade") or 1),
            data_realizacao=to_iso_date(row.get("data_realizacao")),
            profissional_nome=row.get("profissional_nome"),
            cbo_codigo=row.get("cbo_codigo"),
            cbo_descricao=row.get("cbo_descricao"),
            is_exodontia=_is_exodontia(row.get("codigo_sigtap")),
            is_preventivo=_is_preventivo(row.get("codigo_sigtap")),
            is_tra_art=_is_tra_art(row.get("codigo_sigtap")),
        )
        for row in rows
    ]


_SQL_PROBLEMAS_ODONTO = """
SELECT
    cp.co_cidadao AS paciente_id,
    c.no_cidadao,
    fopr.co_fat_atd_odnt AS atendimento_id,
    dcid.nu_cid AS cid_code,
    dcid.no_cid AS cid_description,
    dciap.nu_ciap AS ciap_code,
    dciap.no_ciap AS ciap_description,
    dsp.ds_situacao_problema AS situacao,
    t.dt_registro::text AS data_inicio,
    dprof.no_profissional AS profissional_nome,
    dcbo.nu_cbo AS cbo_codigo
FROM tb_fat_atend_odonto_problemas fopr
JOIN tb_fat_cidadao_pec cp ON cp.co_seq_fat_cidadao_pec = fopr.co_fat_cidadao_pec
LEFT JOIN tb_cidadao c ON c.co_seq_cidadao = cp.co_cidadao
LEFT JOIN tb_dim_cid dcid ON dcid.co_seq_dim_cid = fopr.co_dim_cid
LEFT JOIN tb_dim_ciap dciap ON dciap.co_seq_dim_ciap = fopr.co_dim_ciap
LEFT JOIN tb_dim_situacao_problema dsp ON dsp.co_seq_dim_situacao = fopr.co_dim_situacao_problema
LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fopr.co_dim_tempo
LEFT JOIN tb_dim_profissional dprof ON dprof.co_seq_dim_profissional = fopr.co_dim_profissional_1
LEFT JOIN tb_dim_cbo dcbo ON dcbo.co_seq_dim_cbo = fopr.co_dim_cbo_1
WHERE cp.co_cidadao = %s
  {where_clauses}
ORDER BY fopr.co_seq_fat_atnd_odonto_probl DESC
LIMIT %s;
"""


def listar_problemas_odonto(
    ctx: Context,
    paciente_id: int,
    cid_codigo: Optional[str] = None,
    ciap_codigo: Optional[str] = None,
    limite: int = 50,
) -> List[ProblemaOdontoResult]:
    """
    Lista diagnósticos e problemas odontológicos (CID-10 e CIAP-2) do paciente.
    """
    if paciente_id is None or int(paciente_id) <= 0:
        raise ValueError("paciente_id deve ser um inteiro positivo.")

    conn = get_db_conn(ctx)
    pid = int(paciente_id)
    safe_limit = max(1, min(int(limite), _TETO_SAUDE_BUCAL))

    where_clauses: list[str] = []
    params: list = [pid]

    if cid_codigo and cid_codigo.strip():
        clean_cid = cid_codigo.strip().upper().replace(".", "")
        where_clauses.append("AND UPPER(dcid.nu_cid) LIKE %s")
        params.append(f"{clean_cid}%")

    if ciap_codigo and ciap_codigo.strip():
        clean_ciap = ciap_codigo.strip().upper()
        where_clauses.append("AND UPPER(dciap.nu_ciap) LIKE %s")
        params.append(f"{clean_ciap}%")

    where_sql = "\n  ".join(where_clauses)
    sql = _SQL_PROBLEMAS_ODONTO.format(where_clauses=where_sql)
    params.append(safe_limit)

    rows = query_all(conn, sql, tuple(params))
    return [
        ProblemaOdontoResult(
            paciente_id=int(row.get("paciente_id") or pid),
            paciente_initials=to_initials(row.get("no_cidadao")),
            atendimento_id=(
                int(row.get("atendimento_id"))
                if row.get("atendimento_id") is not None
                else None
            ),
            cid_code=row.get("cid_code"),
            cid_description=row.get("cid_description"),
            ciap_code=row.get("ciap_code"),
            ciap_description=row.get("ciap_description"),
            situacao=row.get("situacao"),
            data_inicio=to_iso_date(row.get("data_inicio")),
            profissional_nome=row.get("profissional_nome"),
            cbo_codigo=row.get("cbo_codigo"),
        )
        for row in rows
    ]


__all__ = [
    "listar_atendimentos_odonto",
    "listar_procedimentos_odonto",
    "listar_problemas_odonto",
]
