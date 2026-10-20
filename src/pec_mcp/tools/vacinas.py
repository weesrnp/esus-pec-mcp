"""
Tool para listar o histórico vacinal (imunobiológicos e doses) de um paciente.
Utiliza as tabelas fato e dimensão do Data Warehouse do e-SUS PEC (tb_fat_vacinacao_vacina).
"""

from __future__ import annotations

from typing import Any, List, Optional

from mcp.server.fastmcp import Context

from ..db import query_all
from ..models import VacinaResult
from . import get_db_conn, to_iso_date

_SQL_VACINAS = """
SELECT
    cp.co_cidadao AS paciente_id,
    imuno.no_imunobiologico AS imunobiologico,
    imuno.sg_imunobiologico AS sigla,
    dose.no_dose_imunobiologico AS dose,
    t.dt_registro AS data_aplicacao,
    fvv.no_lote AS lote,
    CASE WHEN COALESCE(fvv.st_registro_anterior, 0) = 1 THEN 'transcrita' ELSE 'aplicada' END AS origem_registro,
    CASE WHEN COALESCE(imuno.st_registro_valido, 1) <> 0 THEN true ELSE false END AS registro_valido
FROM tb_fat_vacinacao_vacina fvv
JOIN tb_fat_vacinacao fv ON fv.co_seq_fat_vacinacao = fvv.co_fat_vacinacao
JOIN tb_fat_cidadao_pec cp ON cp.co_seq_fat_cidadao_pec = fv.co_fat_cidadao_pec
LEFT JOIN tb_dim_imunobiologico imuno ON imuno.co_seq_dim_imunobiologico = fvv.co_dim_imunobiologico
LEFT JOIN tb_dim_dose_imunobiologico dose ON dose.co_seq_dim_dose_imunobiologico = fvv.co_dim_dose_imunobiologico
LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = COALESCE(fvv.co_dim_tempo_vacina_aplicada, fv.co_dim_tempo)
WHERE cp.co_cidadao = %s
{extra_filters}
ORDER BY t.dt_registro DESC NULLS LAST, fvv.co_seq_fat_vacinacao_vacina DESC
LIMIT %s;
"""


def _validate_paciente_id(paciente_id: Any) -> int:
    """Valida e converte paciente_id para inteiro estritamente positivo."""
    if paciente_id is None:
        raise ValueError("paciente_id é obrigatório.")
    pid = int(paciente_id)
    if pid <= 0:
        raise ValueError("paciente_id deve ser um inteiro positivo.")
    return pid


def _to_str_or_none(value: Any) -> Optional[str]:
    """Converte valor para string ou None se nulo."""
    return str(value) if value is not None else None


def _row_to_vacina_result(row: dict[str, Any], pid: int) -> VacinaResult:
    """Mapeia linha bruta do banco para o contrato estrito VacinaResult."""
    return VacinaResult(
        paciente_id=pid,
        imunobiologico=_to_str_or_none(row.get("imunobiologico")),
        sigla=_to_str_or_none(row.get("sigla")),
        dose=_to_str_or_none(row.get("dose")),
        data_aplicacao=to_iso_date(row.get("data_aplicacao")),
        lote=_to_str_or_none(row.get("lote")),
        origem_registro=str(row.get("origem_registro", "aplicada")),
        registro_valido=bool(row.get("registro_valido", True)),
    )


def listar_vacinas_paciente(
    ctx: Context,
    paciente_id: int,
    imunobiologico: Optional[str] = None,
    apenas_validas: bool = True,
    limite: int = 100,
) -> List[VacinaResult]:
    """
    Lista o histórico vacinal registrado para um paciente (PNI / e-SUS PEC).

    Retorna imunobiológico, sigla, dose, data de aplicação, lote, origem (aplicada na UBS
    ou transcrição de caderneta) e flag de validade.

    `tb_fat_vacinacao_vacina` não tem flag de validade própria: `registro_valido`
    vem de `tb_dim_imunobiologico.st_registro_valido` (ETL em duas fases do DW).
    Só o valor 0 marca registro inválido; NULL é dimensão ainda não consolidada
    pelo ETL noturno e continua visível, para não esconder doses do dia.
    """
    pid = _validate_paciente_id(paciente_id)
    safe_limit = max(1, min(int(limite), 200))

    filters: list[str] = []
    params: list[Any] = [pid]

    if apenas_validas:
        filters.append("AND COALESCE(imuno.st_registro_valido, 1) <> 0")

    if imunobiologico and imunobiologico.strip():
        term = f"%{imunobiologico.strip().upper()}%"
        filters.append("AND (imuno.no_imunobiologico ILIKE %s OR imuno.sg_imunobiologico ILIKE %s)")
        params.extend([term, term])

    extra_filters = "\n".join(filters)
    params.append(safe_limit)

    sql = _SQL_VACINAS.format(extra_filters=extra_filters)
    conn = get_db_conn(ctx)
    rows = query_all(conn, sql, tuple(params))

    return [_row_to_vacina_result(row, pid) for row in rows]


__all__ = ["listar_vacinas_paciente"]
