"""
Ferramenta para consulta dos últimos atendimentos clínicos SOAP de um paciente.

Recupera registros de evolução clínica (subjetivo, objetivo, avaliação, plano) e
problemas/condições diagnosticados por médicos e enfermeiros, ignorando atendimentos
cancelados (coalesce(ap.st_cancelado, 0) = 0).
"""

from __future__ import annotations

import json
from typing import Any, List, Optional

from mcp.server.fastmcp import Context

from ..db import query_all
from ..domain.patient import mascarar_texto_livre
from ..models import AtendimentoSOAPResult
from . import get_db_conn, to_iso_datetime

_MAX_LIMIT: int = 200
_DEFAULT_LIMIT: int = 50

_SQL_ATENDIMENTOS_BASE = """
SELECT
    ap.co_seq_atend_prof          AS atendimento_id,
    pr.co_cidadao                 AS paciente_id,
    a.dt_inicio                   AS data_hora,
    cb.co_cbo_2002                AS cbo_codigo,
    cb.no_cbo                     AS cbo_descricao,
    COALESCE(p.no_social_profissional, p.no_civil_profissional) AS profissional,
    ap.tp_atend_prof              AS tipo_profissional_id,
    ap.tp_atend                   AS tipo_atendimento_id,
    es.ds_subjetivo               AS soap_s,
    eo.ds_objetivo                AS soap_o,
    ea.ds_avaliacao               AS soap_a,
    ep.ds_plano                   AS soap_p,
    COALESCE(cond.condicoes, '[]') AS condicoes
FROM tb_atend_prof ap
JOIN tb_atend       a   ON a.co_seq_atend       = ap.co_atend
JOIN tb_prontuario  pr  ON pr.co_seq_prontuario = a.co_prontuario
LEFT JOIN tb_lotacao l  ON l.co_ator_papel      = ap.co_lotacao
LEFT JOIN tb_prof    p  ON p.co_seq_prof        = l.co_prof
LEFT JOIN tb_cbo     cb ON cb.co_cbo            = l.co_cbo
LEFT JOIN tb_evolucao_subjetivo es ON es.co_atend_prof = ap.co_seq_atend_prof
LEFT JOIN tb_evolucao_objetivo  eo ON eo.co_atend_prof = ap.co_seq_atend_prof
LEFT JOIN tb_evolucao_avaliacao ea ON ea.co_atend_prof = ap.co_seq_atend_prof
LEFT JOIN tb_evolucao_plano     ep ON ep.co_atend_prof = ap.co_seq_atend_prof
LEFT JOIN LATERAL (
    SELECT json_agg(
        jsonb_build_object(
            'condition_id', p2.co_seq_problema,
            'cid_code', cid2.nu_cid10,
            'cid_description', cid2.no_cid10,
            'ciap_code', ciap2.co_ciap,
            'ciap_description', ciap2.ds_ciap,
            'observacao', pe2.ds_observacao,
            'dt_inicio_condicao', pe2.dt_inicio_problema,
            'dt_fim_condicao', pe2.dt_fim_problema,
            'situacao_id', pe2.co_situacao_problema
        )
        ORDER BY pe2.dt_inicio_problema DESC NULLS LAST, p2.co_seq_problema
    ) AS condicoes
    FROM tb_problema_evolucao pe2
    JOIN tb_problema p2 ON p2.co_unico_problema = pe2.co_unico_problema
    LEFT JOIN tb_cid10 cid2 ON cid2.co_cid10 = p2.co_cid10
    LEFT JOIN tb_ciap ciap2 ON ciap2.co_seq_ciap = p2.co_ciap
    WHERE pe2.co_atend_prof = ap.co_seq_atend_prof
) cond ON TRUE
WHERE pr.co_cidadao = %s
  AND COALESCE(ap.st_cancelado, 0) = 0
  AND (
        cb.co_cbo_2002 LIKE '225%%'   -- médicos
     OR cb.co_cbo_2002 LIKE '2235%%'  -- enfermeiros
      )
ORDER BY a.dt_inicio DESC NULLS LAST
"""


def _parse_soap_conditions(raw_condicoes: Any) -> list:
    """Extrai e valida lista de condições retornadas pelo json_agg do PostgreSQL."""
    parsed: Any = raw_condicoes
    if isinstance(raw_condicoes, str):
        try:
            parsed = json.loads(raw_condicoes)
        except Exception:
            return []
    if not isinstance(parsed, list):
        return []
    for item in parsed:
        if isinstance(item, dict) and item.get("observacao") is not None:
            item["observacao"] = mascarar_texto_livre(item["observacao"])
    return parsed


def _format_atendimento_row(row: dict) -> AtendimentoSOAPResult:
    """Converte linha do banco para AtendimentoSOAPResult preservando o contrato de chaves."""
    return AtendimentoSOAPResult(
        atendimento_id=int(row["atendimento_id"]),
        paciente_id=int(row["paciente_id"]),
        data_hora=to_iso_datetime(row.get("data_hora")),
        cbo_codigo=str(row.get("cbo_codigo")) if row.get("cbo_codigo") is not None else None,
        cbo_descricao=str(row.get("cbo_descricao")) if row.get("cbo_descricao") is not None else None,
        profissional=str(row.get("profissional")) if row.get("profissional") is not None else None,
        tipo_profissional_id=str(row.get("tipo_profissional_id"))
        if row.get("tipo_profissional_id") is not None
        else None,
        tipo_atendimento_id=str(row.get("tipo_atendimento_id"))
        if row.get("tipo_atendimento_id") is not None
        else None,
        soap_s=mascarar_texto_livre(row.get("soap_s")),
        soap_o=mascarar_texto_livre(row.get("soap_o")),
        soap_a=mascarar_texto_livre(row.get("soap_a")),
        soap_p=mascarar_texto_livre(row.get("soap_p")),
        condicoes=_parse_soap_conditions(row.get("condicoes")),
    )


def listar_ultimos_atendimentos_soap(
    ctx: Context,
    paciente_id: int,
    limite: Optional[int] = _DEFAULT_LIMIT,
) -> List[AtendimentoSOAPResult]:
    """
    Recupera últimos atendimentos SOAP do paciente (médicos e enfermeiros).

    Atendimentos profissionais cancelados são ignorados porque não representam
    atendimentos clínicos concluídos ou válidos. CPF, CNS, telefone e e-mail
    digitados no texto do SOAP saem mascarados.
    """
    if paciente_id is None:
        raise ValueError("paciente_id é obrigatório para consultar histórico de atendimento.")

    paciente_id_int = int(paciente_id)
    if paciente_id_int <= 0:
        raise ValueError("paciente_id deve ser um inteiro positivo.")

    # Sem limite explícito vale o padrão: o histórico inteiro de SOAP de um
    # paciente não deve sair numa chamada só.
    pedido = _DEFAULT_LIMIT if limite is None else int(limite)
    safe_limit = max(1, min(pedido, _MAX_LIMIT))

    conn = get_db_conn(ctx)
    sql = f"{_SQL_ATENDIMENTOS_BASE} LIMIT %s"
    params = [paciente_id_int, safe_limit]

    rows = query_all(conn, sql, tuple(params))

    return [_format_atendimento_row(row) for row in rows]


__all__ = ["listar_ultimos_atendimentos_soap"]
