"""
Ferramenta para identificação anonimizada de cidadãos/pacientes no e-SUS PEC.

Garante conformidade com a LGPD: nenhum identificador direto (CPF, CNS, RG,
nome da mãe, endereço, contato) é selecionado no banco ou exposto na saída.
Nomes são convertidos em iniciais maiúsculas e datas de nascimento em idade textual.
"""

from __future__ import annotations

from typing import List, Optional

from mcp.server.fastmcp import Context

from ..db import query_all
from ..domain.patient import compute_age_display, to_initials
from ..models import PatientCaptureResult
from . import get_db_conn
from .filters import build_patient_filters

_MAX_LIMIT: int = 200
_DEFAULT_LIMIT: int = 50

_SQL_PACIENTES = """
SELECT
    c.co_seq_cidadao AS paciente_id,
    c.no_cidadao     AS nome_paciente,
    c.dt_nascimento  AS data_nascimento,
    c.no_sexo        AS sexo
FROM tb_cidadao c
{where_clause}
ORDER BY c.co_seq_cidadao ASC
LIMIT %s;
"""


def _format_patient_row(row: dict) -> PatientCaptureResult:
    """Converte linha do banco para PatientCaptureResult com anonimização estrita."""
    sexo_val = str(row.get("sexo")) if row.get("sexo") is not None else None
    return PatientCaptureResult(
        paciente_id=int(row["paciente_id"]),
        name=to_initials(row.get("nome_paciente")),
        age=compute_age_display(row.get("data_nascimento")),
        sex=sexo_val,
    )


def capturar_paciente(
    ctx: Context,
    paciente_id: Optional[int] = None,
    name_starts_with: Optional[str] = None,
    sex: Optional[str] = None,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    unidade_saude_id: Optional[int] = None,
    equipe_id: Optional[int] = None,
    micro_area: Optional[str] = None,
    limite: int = _DEFAULT_LIMIT,
) -> List[PatientCaptureResult]:
    """
    Retorna dados mínimos de pacientes sem identificadores diretos (somente leitura).

    Exige ao menos um critério (id, prefixo de nome, sexo ou faixa etária) para evitar varreduras amplas.
    Aceita filtro opcional de unidade de saúde (atendimento ou vinculação por CNES),
    equipe (co_seq_equipe) e microárea (nu_micro_area atual via cadastro individual).
    """
    safe_limit = max(1, min(int(limite), _MAX_LIMIT))

    clauses, params = build_patient_filters(
        paciente_id=paciente_id,
        name_prefix=name_starts_with,
        sex=sex,
        age_min=age_min,
        age_max=age_max,
        unidade_saude_id=unidade_saude_id,
        equipe_id=equipe_id,
        micro_area=micro_area,
        alias="c",
    )

    if not clauses:
        raise ValueError("Informe pelo menos um critério (id, prefixo de nome, sexo ou idade).")

    where_clause = "WHERE " + " AND ".join(clauses)
    sql = _SQL_PACIENTES.format(where_clause=where_clause)

    conn = get_db_conn(ctx)
    query_params = tuple(params + [safe_limit])
    rows = query_all(conn, sql, query_params)

    return [_format_patient_row(row) for row in rows]


__all__ = ["capturar_paciente"]
