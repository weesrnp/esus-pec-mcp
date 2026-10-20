"""
Tool para listar histórico de procedimentos clínicos e exames realizados (SIGTAP / e-SUS PEC).
Abrange procedimentos individuais e ambulatoriais (ex.: coleta de citopatológico, ECG, curativos, etc.).
"""

from __future__ import annotations

import re
from typing import List, Optional

from mcp.server.fastmcp import Context

from ..db import query_all
from ..models import ProcedimentoResult
from . import get_db_conn, to_iso_date

_TETO_PROCEDIMENTOS = 200

_SQL_PROCEDIMENTOS = """
WITH proced_individual AS (
    SELECT
        cp.co_cidadao AS paciente_id,
        dp.co_proced AS codigo_sigtap,
        dp.ds_proced AS nome_procedimento,
        t.dt_registro::date AS data_realizacao,
        1 AS quantidade,
        dprof.no_profissional AS profissional_nome,
        dcbo.no_cbo AS cbo_descricao,
        'consulta_individual'::text AS contexto
    FROM tb_fat_atd_ind_procedimentos pr
    JOIN tb_fat_cidadao_pec cp ON cp.co_seq_fat_cidadao_pec = pr.co_fat_cidadao_pec
    -- O subfato guarda o procedimento realizado em co_dim_procedimento_avaliado
    -- (co_dim_procedimento_solicitado é pedido, não execução).
    JOIN tb_dim_procedimento dp ON dp.co_seq_dim_procedimento = pr.co_dim_procedimento_avaliado
    LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = pr.co_dim_tempo
    LEFT JOIN tb_dim_profissional dprof ON dprof.co_seq_dim_profissional = pr.co_dim_profissional_1
    LEFT JOIN tb_dim_cbo dcbo ON dcbo.co_seq_dim_cbo = pr.co_dim_cbo_1
    WHERE cp.co_cidadao = %s
      {individual_filters}
),
proced_ambulatorial AS (
    SELECT
        cp.co_cidadao AS paciente_id,
        dp.co_proced AS codigo_sigtap,
        dp.ds_proced AS nome_procedimento,
        t.dt_registro::date AS data_realizacao,
        1 AS quantidade,
        dprof.no_profissional AS profissional_nome,
        dcbo.no_cbo AS cbo_descricao,
        'sala_procedimentos'::text AS contexto
    FROM tb_fat_proced_atend_proced f
    JOIN tb_fat_cidadao_pec cp ON cp.co_seq_fat_cidadao_pec = f.co_fat_cidadao_pec
    LEFT JOIN tb_dim_procedimento dp ON dp.co_seq_dim_procedimento = f.co_dim_procedimento
    LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = f.co_dim_tempo
    LEFT JOIN tb_dim_profissional dprof ON dprof.co_seq_dim_profissional = f.co_dim_profissional
    LEFT JOIN tb_dim_cbo dcbo ON dcbo.co_seq_dim_cbo = f.co_dim_cbo
    WHERE cp.co_cidadao = %s
      {ambulatorial_filters}
)
SELECT * FROM (
    SELECT * FROM proced_individual
    UNION ALL
    SELECT * FROM proced_ambulatorial
) unificado
ORDER BY data_realizacao DESC NULLS LAST
LIMIT %s;
"""


def _format_sigtap(code: Optional[str]) -> Optional[str]:
    """Formata código SIGTAP de 10 dígitos para a máscara padrão XX.XX.XX.XXX-X."""
    if not code:
        return None
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    if len(digits) == 10:
        return f"{digits[0:2]}.{digits[2:4]}.{digits[4:6]}.{digits[6:9]}-{digits[9]}"
    return str(code)


def _build_procedimentos_filters(
    codigo_sigtap: Optional[str],
    termo_busca: Optional[str],
) -> tuple[str, list]:
    filters = []
    filter_params: list = []

    if codigo_sigtap and codigo_sigtap.strip():
        clean_code = re.sub(r"[.\-]", "", codigo_sigtap.strip())
        filters.append("AND dp.co_proced LIKE %s")
        filter_params.append(f"{clean_code}%")

    if termo_busca and termo_busca.strip():
        term = f"%{termo_busca.strip().upper()}%"
        filters.append("AND dp.ds_proced ILIKE %s")
        filter_params.append(term)

    extra_sql = "\n      ".join(filters)
    return extra_sql, filter_params


def _format_procedimento_row(row: dict, pid: int) -> ProcedimentoResult:
    """Mapeia linha bruta de procedimento para ProcedimentoResult."""
    return ProcedimentoResult(
        paciente_id=pid,
        codigo_sigtap=_format_sigtap(row.get("codigo_sigtap")),
        nome_procedimento=str(row.get("nome_procedimento")) if row.get("nome_procedimento") is not None else None,
        data_realizacao=to_iso_date(row.get("data_realizacao")),
        quantidade=int(row["quantidade"]) if row.get("quantidade") is not None else 1,
        profissional_nome=str(row.get("profissional_nome")) if row.get("profissional_nome") is not None else None,
        cbo_descricao=str(row.get("cbo_descricao")) if row.get("cbo_descricao") is not None else None,
        contexto=str(row.get("contexto", "consulta_individual")),
    )


def listar_procedimentos_clinicos(
    ctx: Context,
    paciente_id: int,
    codigo_sigtap: Optional[str] = None,
    termo_busca: Optional[str] = None,
    limite: int = 50,
) -> List[ProcedimentoResult]:
    """
    Lista procedimentos clínicos e laboratoriais realizados para um paciente no e-SUS PEC.

    Abrange tanto os procedimentos executados durante atendimentos individuais (médicos e enfermagem)
    quanto procedimentos rápidos em salas ambulatoriais (coleta de citopatológico/preventivo, ECG, curativos, etc.).
    """
    if paciente_id is None:
        raise ValueError("paciente_id é obrigatório.")
    pid = int(paciente_id)
    if pid <= 0:
        raise ValueError("paciente_id deve ser um inteiro positivo.")

    safe_limit = max(1, min(int(limite), _TETO_PROCEDIMENTOS))
    extra_sql, filter_params = _build_procedimentos_filters(codigo_sigtap, termo_busca)

    sql = _SQL_PROCEDIMENTOS.format(
        individual_filters=extra_sql,
        ambulatorial_filters=extra_sql,
    )

    params = [pid] + filter_params + [pid] + filter_params + [safe_limit]
    conn = get_db_conn(ctx)
    rows = query_all(conn, sql, tuple(params))

    return [_format_procedimento_row(row, pid) for row in rows]


__all__ = ["listar_procedimentos_clinicos"]
