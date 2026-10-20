"""
Tools para registros de medições clínicas (antropometria, PA, HGT).

Cada tool consolida dados de DUAS fontes distintas via UNION ALL:
1. PEC (atendimento clínico) — tabela tl_medicao
2. Visita domiciliar (CDS) — tabela tb_fat_visita_domiciliar

O tipo de profissional é derivado do CBO:
  - 225xxx → "médico"
  - 2235xx → "enfermeiro"
  - 515105 → "ACS"
  - outros  → descrição CBO original
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from mcp.server.fastmcp import Context

from ..db import query_all
from ..models import AntropometriaResult, HGTResult, PAResult
from . import get_db_conn, to_iso_datetime


# ──────────────────────────────────────────────────────────────
# Classificação de profissional por CBO
# ──────────────────────────────────────────────────────────────

def _classify_professional(cbo_code: Optional[str], cbo_name: Optional[str]) -> str:
    """Deriva tipo de profissional legível a partir do código CBO."""
    if not cbo_code:
        return "não identificado"
    code = str(cbo_code).strip()
    if code.startswith("225"):
        return "médico"
    if code.startswith("2235"):
        return "enfermeiro"
    if code == "515105":
        return "ACS"
    if code.startswith("5151"):
        return "agente de saúde"
    if code.startswith("2232"):
        return "dentista"
    return str(cbo_name).lower() if cbo_name else "outro"


# ──────────────────────────────────────────────────────────────
# Joins reutilizáveis
# ──────────────────────────────────────────────────────────────

# PEC: tl_medicao → paciente + profissional
# ATENÇÃO: COALESCE(ap.st_cancelado, 0) = 0 é validado estritamente em test_tool_atendimentos_unit.py
_FROM_PEC = """
    FROM tl_medicao m
    JOIN tb_atend_prof ap  ON ap.co_seq_atend_prof = m.co_atend_prof
                           AND COALESCE(ap.st_cancelado, 0) = 0
    JOIN tb_atend a        ON a.co_seq_atend       = ap.co_atend
    JOIN tb_prontuario pr  ON pr.co_seq_prontuario = a.co_prontuario
    JOIN tb_cidadao c      ON c.co_seq_cidadao     = pr.co_cidadao
    LEFT JOIN tb_lotacao l ON l.co_ator_papel      = ap.co_lotacao
    LEFT JOIN tb_prof p    ON p.co_seq_prof        = l.co_prof
    LEFT JOIN tb_cbo cb    ON cb.co_cbo            = l.co_cbo
"""

# tl_medicao guarda as medidas como varchar. Um "72,5" ou "?" num registro
# derrubaria a consulta inteira com ::numeric; aqui o valor inválido vira NULL.
def _numero_seguro(coluna: str) -> str:
    return (
        f"(CASE WHEN {coluna} ~ '^[0-9]+([.,][0-9]+)?$' "
        f"THEN replace({coluna}, ',', '.')::numeric END)"
    )


_PESO_PEC = _numero_seguro("m.nu_medicao_peso")
_ALTURA_PEC = _numero_seguro("m.nu_medicao_altura")

# Visita domiciliar: tb_fat_visita_domiciliar → paciente + profissional
_FROM_VISITA = """
    FROM tb_fat_visita_domiciliar v
    JOIN tb_fat_cidadao_pec cp     ON cp.co_seq_fat_cidadao_pec = v.co_fat_cidadao_pec
    JOIN tb_dim_tempo t            ON t.co_seq_dim_tempo = v.co_dim_tempo
    JOIN tb_dim_profissional dp    ON dp.co_seq_dim_profissional = v.co_dim_profissional
    JOIN tb_dim_cbo dcbo           ON dcbo.co_seq_dim_cbo = v.co_dim_cbo
"""


def _validate_paciente_id(paciente_id: Any) -> int:
    """Valida e converte paciente_id para inteiro estritamente positivo."""
    if paciente_id is None:
        raise ValueError("paciente_id é obrigatório.")
    pid = int(paciente_id)
    if pid <= 0:
        raise ValueError("paciente_id deve ser um inteiro positivo.")
    return pid


def _build_date_filter_pec(
    data_inicio: Optional[str], data_fim: Optional[str], params: list[Any]
) -> str:
    """Adiciona filtros de data para a fonte PEC (tl_medicao.dt_medicao)."""
    clauses: list[str] = []
    if data_inicio:
        clauses.append("m.dt_medicao >= %s::timestamp")
        params.append(data_inicio)
    if data_fim:
        # dt_medicao é timestamp: "<= 'AAAA-MM-DD'" cortaria o próprio dia.
        clauses.append("m.dt_medicao < (%s::date + 1)")
        params.append(data_fim)
    return " AND ".join(clauses) if clauses else ""


def _build_date_filter_visita(
    data_inicio: Optional[str], data_fim: Optional[str], params: list[Any]
) -> str:
    """Adiciona filtros de data para a fonte visita (tb_dim_tempo.dt_registro)."""
    clauses: list[str] = []
    if data_inicio:
        clauses.append("t.dt_registro >= %s::date")
        params.append(data_inicio)
    if data_fim:
        clauses.append("t.dt_registro <= %s::date")
        params.append(data_fim)
    return " AND ".join(clauses) if clauses else ""


def _to_float(value: Any) -> Optional[float]:
    """Converte valor para float seguro ou retorna None."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ".")) if isinstance(value, str) else float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> Optional[int]:
    """Converte valor numérico em texto para int seguro ou retorna None."""
    if value is None:
        return None
    val_str = str(value).strip()
    return int(val_str) if val_str.isdigit() else None


# ──────────────────────────────────────────────────────────────
# Tool: listar_registros_antropometria
# ──────────────────────────────────────────────────────────────


def listar_registros_antropometria(
    ctx: Context,
    paciente_id: int,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    limite: int = 50,
) -> List[AntropometriaResult]:
    """
    Histórico de peso, altura e IMC de um paciente, consolidando dados
    de atendimentos clínicos (PEC) e visitas domiciliares (ACS).

    O IMC é calculado como peso(kg) / (altura(m))² sempre que peso e
    altura estiverem presentes. Os campos profissional_id/profissional_nome/
    tipo_profissional identificam quem registrou. O campo `origem` indica
    a fonte ("pec" ou "visita_domiciliar").
    """
    pid = _validate_paciente_id(paciente_id)
    safe_limit = max(1, min(int(limite), 200))

    # -- Fonte PEC --
    pec_params: list[Any] = [pid]
    pec_date = _build_date_filter_pec(data_inicio, data_fim, pec_params)
    pec_where = f"AND ({pec_date})" if pec_date else ""

    sql_pec = f"""
        SELECT
            c.co_seq_cidadao                          AS paciente_id,
            {_PESO_PEC}                               AS peso_kg,
            {_ALTURA_PEC}                             AS altura_cm,
            CASE
                WHEN {_PESO_PEC} IS NOT NULL
                 AND {_ALTURA_PEC} > 0
                THEN ROUND(
                    {_PESO_PEC}
                    / (({_ALTURA_PEC} / 100.0) ^ 2), 2)
                ELSE NULL
            END                                       AS imc,
            m.dt_medicao                              AS data_medicao,
            p.co_seq_prof                             AS prof_id,
            COALESCE(p.no_social_profissional, p.no_civil_profissional)                  AS prof_nome,
            cb.co_cbo_2002                            AS cbo_codigo,
            cb.no_cbo                                 AS cbo_nome,
            'pec'                                     AS origem
        {_FROM_PEC}
        WHERE c.co_seq_cidadao = %s
          AND (m.nu_medicao_peso IS NOT NULL OR m.nu_medicao_altura IS NOT NULL)
          {pec_where}
    """

    # -- Fonte Visita --
    vis_params: list[Any] = [pid]
    vis_date = _build_date_filter_visita(data_inicio, data_fim, vis_params)
    vis_where = f"AND ({vis_date})" if vis_date else ""

    sql_vis = f"""
        SELECT
            cp.co_cidadao                             AS paciente_id,
            v.nu_peso                                 AS peso_kg,
            v.nu_altura                               AS altura_cm,
            CASE
                WHEN v.nu_peso IS NOT NULL AND v.nu_peso > 0
                 AND v.nu_altura IS NOT NULL AND v.nu_altura > 0
                THEN ROUND(
                    (v.nu_peso / ((v.nu_altura / 100.0) ^ 2))::numeric, 2)
                ELSE NULL
            END                                       AS imc,
            t.dt_registro::timestamp                  AS data_medicao,
            dp.co_seq_dim_profissional                AS prof_id,
            dp.no_profissional                        AS prof_nome,
            dcbo.nu_cbo                               AS cbo_codigo,
            dcbo.no_cbo                               AS cbo_nome,
            'visita_domiciliar'                       AS origem
        {_FROM_VISITA}
        WHERE cp.co_cidadao = %s
          AND (v.nu_peso IS NOT NULL AND v.nu_peso > 0
               OR v.nu_altura IS NOT NULL AND v.nu_altura > 0)
          {vis_where}
    """

    sql = f"""
        ({sql_pec})
        UNION ALL
        ({sql_vis})
        ORDER BY data_medicao DESC NULLS LAST
        LIMIT %s;
    """
    params = pec_params + vis_params + [safe_limit]

    conn = get_db_conn(ctx)
    rows = query_all(conn, sql, tuple(params))

    results: List[AntropometriaResult] = []
    for row in rows:
        results.append(
            AntropometriaResult(
                paciente_id=int(row["paciente_id"]),
                peso_kg=_to_float(row.get("peso_kg")),
                altura_cm=_to_float(row.get("altura_cm")),
                imc=_to_float(row.get("imc")),
                data_medicao=to_iso_datetime(row.get("data_medicao")),
                profissional_id=int(row["prof_id"]) if row.get("prof_id") else None,
                profissional_nome=row.get("prof_nome"),
                tipo_profissional=_classify_professional(
                    row.get("cbo_codigo"), row.get("cbo_nome")
                ),
                origem=row.get("origem", "pec"),
            )
        )
    return results


# ──────────────────────────────────────────────────────────────
# Tool: listar_registros_pa
# ──────────────────────────────────────────────────────────────


def listar_registros_pa(
    ctx: Context,
    paciente_id: int,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    limite: int = 50,
) -> List[PAResult]:
    """
    Histórico de pressão arterial (PAS/PAD) de um paciente, consolidando
    dados de atendimentos clínicos (PEC) e visitas domiciliares (ACS).

    A PA é armazenada como "PAS/PAD" (ex.: "130/80") e é decomposta em
    valores separados. Os campos profissional_id/profissional_nome/
    tipo_profissional identificam quem aferiu.
    """
    pid = _validate_paciente_id(paciente_id)
    safe_limit = max(1, min(int(limite), 200))

    # -- Fonte PEC --
    pec_params: list[Any] = [pid]
    pec_date = _build_date_filter_pec(data_inicio, data_fim, pec_params)
    pec_where = f"AND ({pec_date})" if pec_date else ""

    sql_pec = f"""
        SELECT
            c.co_seq_cidadao                                     AS paciente_id,
            SPLIT_PART(m.nu_medicao_pressao_arterial, '/', 1)    AS pas_str,
            SPLIT_PART(m.nu_medicao_pressao_arterial, '/', 2)    AS pad_str,
            m.nu_medicao_pressao_arterial                        AS pressao_raw,
            m.dt_medicao                                         AS data_medicao,
            p.co_seq_prof                                        AS prof_id,
            COALESCE(p.no_social_profissional, p.no_civil_profissional)                             AS prof_nome,
            cb.co_cbo_2002                                       AS cbo_codigo,
            cb.no_cbo                                            AS cbo_nome,
            'pec'                                                AS origem
        {_FROM_PEC}
        WHERE c.co_seq_cidadao = %s
          AND m.nu_medicao_pressao_arterial IS NOT NULL
          {pec_where}
    """

    # -- Fonte Visita --
    vis_params: list[Any] = [pid]
    vis_date = _build_date_filter_visita(data_inicio, data_fim, vis_params)
    vis_where = f"AND ({vis_date})" if vis_date else ""

    sql_vis = f"""
        SELECT
            cp.co_cidadao                                        AS paciente_id,
            SPLIT_PART(v.nu_medicao_pressao_arterial, '/', 1)    AS pas_str,
            SPLIT_PART(v.nu_medicao_pressao_arterial, '/', 2)    AS pad_str,
            v.nu_medicao_pressao_arterial                        AS pressao_raw,
            t.dt_registro::timestamp                             AS data_medicao,
            dp.co_seq_dim_profissional                           AS prof_id,
            dp.no_profissional                                   AS prof_nome,
            dcbo.nu_cbo                                          AS cbo_codigo,
            dcbo.no_cbo                                          AS cbo_nome,
            'visita_domiciliar'                                  AS origem
        {_FROM_VISITA}
        WHERE cp.co_cidadao = %s
          AND v.nu_medicao_pressao_arterial IS NOT NULL
          {vis_where}
    """

    sql = f"""
        ({sql_pec})
        UNION ALL
        ({sql_vis})
        ORDER BY data_medicao DESC NULLS LAST
        LIMIT %s;
    """
    params = pec_params + vis_params + [safe_limit]

    conn = get_db_conn(ctx)
    rows = query_all(conn, sql, tuple(params))

    results: List[PAResult] = []
    for row in rows:
        results.append(
            PAResult(
                paciente_id=int(row["paciente_id"]),
                pas=_to_int(row.get("pas_str")),
                pad=_to_int(row.get("pad_str")),
                pressao_raw=row.get("pressao_raw"),
                data_medicao=to_iso_datetime(row.get("data_medicao")),
                profissional_id=int(row["prof_id"]) if row.get("prof_id") else None,
                profissional_nome=row.get("prof_nome"),
                tipo_profissional=_classify_professional(
                    row.get("cbo_codigo"), row.get("cbo_nome")
                ),
                origem=row.get("origem", "pec"),
            )
        )
    return results


# ──────────────────────────────────────────────────────────────
# Tool: listar_registros_hgt
# ──────────────────────────────────────────────────────────────

_GLICEMIA_TIPO = {
    0: "Jejum",
    1: "Pós-prandial",
    2: "Pré-prandial",
    3: "Não especificado",
}

_MOMENTO_FILTER = {
    "jejum": 0,
    "pos_prandial": 1,
    "pre_prandial": 2,
}


def listar_registros_hgt(
    ctx: Context,
    paciente_id: int,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    momento: Optional[str] = None,
    limite: int = 50,
) -> List[HGTResult]:
    """
    Histórico de glicemia capilar (HGT) de um paciente, consolidando
    dados de atendimentos clínicos (PEC) e visitas domiciliares (ACS).

    Retorna o valor em mg/dL e o momento da aferição em texto legível
    (Jejum, Pós-prandial, Pré-prandial). Os campos profissional_id/
    profissional_nome/tipo_profissional identificam quem aferiu.
    Filtro opcional `momento` aceita: "jejum", "pos_prandial", "pre_prandial".
    """
    pid = _validate_paciente_id(paciente_id)
    safe_limit = max(1, min(int(limite), 200))

    momento_tp: Optional[int] = None
    if momento:
        momento_key = momento.strip().lower()
        if momento_key not in _MOMENTO_FILTER:
            raise ValueError(
                f"momento inválido: '{momento}'. Use: jejum, pos_prandial, pre_prandial."
            )
        momento_tp = _MOMENTO_FILTER[momento_key]

    # -- Fonte PEC --
    pec_params: list[Any] = [pid]
    pec_date = _build_date_filter_pec(data_inicio, data_fim, pec_params)
    pec_extra = f"AND ({pec_date})" if pec_date else ""
    if momento_tp is not None:
        pec_extra += " AND m.tp_glicemia = %s"
        pec_params.append(momento_tp)

    sql_pec = f"""
        SELECT
            c.co_seq_cidadao            AS paciente_id,
            m.nu_medicao_glicemia       AS valor_str,
            m.tp_glicemia               AS tp_glicemia,
            m.dt_medicao                AS data_medicao,
            p.co_seq_prof               AS prof_id,
            COALESCE(p.no_social_profissional, p.no_civil_profissional)    AS prof_nome,
            cb.co_cbo_2002              AS cbo_codigo,
            cb.no_cbo                   AS cbo_nome,
            'pec'                       AS origem
        {_FROM_PEC}
        WHERE c.co_seq_cidadao = %s
          AND m.nu_medicao_glicemia IS NOT NULL
          {pec_extra}
    """

    # -- Fonte Visita --
    vis_params: list[Any] = [pid]
    vis_date = _build_date_filter_visita(data_inicio, data_fim, vis_params)
    vis_extra = f"AND ({vis_date})" if vis_date else ""
    if momento_tp is not None:
        vis_extra += " AND dtg.nu_identificador::text = %s::text"
        vis_params.append(momento_tp)

    sql_vis = f"""
        SELECT
            cp.co_cidadao               AS paciente_id,
            v.nu_medicao_glicemia       AS valor_str,
            dtg.co_ordem                AS tp_glicemia,
            t.dt_registro::timestamp    AS data_medicao,
            dp.co_seq_dim_profissional  AS prof_id,
            dp.no_profissional          AS prof_nome,
            dcbo.nu_cbo                 AS cbo_codigo,
            dcbo.no_cbo                 AS cbo_nome,
            'visita_domiciliar'         AS origem
        {_FROM_VISITA}
        LEFT JOIN tb_dim_tipo_glicemia dtg ON dtg.co_seq_dim_tipo_glicemia = v.co_dim_tipo_glicemia
        WHERE cp.co_cidadao = %s
          AND v.nu_medicao_glicemia IS NOT NULL
          {vis_extra}
    """

    sql = f"""
        ({sql_pec})
        UNION ALL
        ({sql_vis})
        ORDER BY data_medicao DESC NULLS LAST
        LIMIT %s;
    """
    params = pec_params + vis_params + [safe_limit]

    conn = get_db_conn(ctx)
    rows = query_all(conn, sql, tuple(params))

    results: List[HGTResult] = []
    for row in rows:
        tp = row.get("tp_glicemia")
        momento_texto = _GLICEMIA_TIPO.get(
            int(tp) if tp is not None else -1,
            "Não informado",
        )
        results.append(
            HGTResult(
                paciente_id=int(row["paciente_id"]),
                valor_mg_dl=_to_float(row.get("valor_str")),
                momento_afericao=momento_texto,
                data_medicao=to_iso_datetime(row.get("data_medicao")),
                profissional_id=int(row["prof_id"]) if row.get("prof_id") else None,
                profissional_nome=row.get("prof_nome"),
                tipo_profissional=_classify_professional(
                    row.get("cbo_codigo"), row.get("cbo_nome")
                ),
                origem=row.get("origem", "pec"),
            )
        )
    return results


__all__ = [
    "listar_registros_antropometria",
    "listar_registros_pa",
    "listar_registros_hgt",
]
