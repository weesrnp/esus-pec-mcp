"""
Tool para listar unidades de saúde cadastradas no PEC.
"""

from __future__ import annotations

from typing import List

from mcp.server.fastmcp import Context

from ..cache import cached_dimension
from ..db import query_all
from ..models import HealthUnitResult
from . import get_db_conn

# Tipos de estabelecimento da Atenção Primária (tb_tipo_unidade_saude.co_tipo_unidade_cnes):
# 01 posto de saúde, 02 centro de saúde/UBS, 32 e 40 unidades móveis (fluvial e terrestre),
# 71 centro de apoio à saúde da família, 72 atenção à saúde indígena, 74 polo academia da saúde.
# O filtro usa o código CNES, que é estável entre versões; o nome do tipo só vai na saída.
TIPOS_CNES_APS = (1, 2, 32, 40, 71, 72, 74)

_SQL_LISTAR_UNIDADES = """
SELECT
    us.co_seq_unidade_saude   AS unidade_id,
    us.nu_cnes                AS cnes,
    us.no_unidade_saude       AS nome,
    us.co_localidade_endereco AS localidade_id,
    us.st_ativo               AS ativo,
    tu.co_tipo_unidade_cnes   AS tipo_cnes,
    tu.no_tipo_unidade_saude  AS tipo_descricao
FROM tb_unidade_saude us
LEFT JOIN tb_tipo_unidade_saude tu ON tu.co_seq_tipo_unidade_saude = us.tp_unidade_saude
WHERE 1=1
{filtros}
ORDER BY us.no_unidade_saude;
"""


@cached_dimension(ttl_seconds=3600)
def listar_unidades_saude(
    ctx: Context,
    apenas_atencao_primaria: bool = True,
    incluir_inativas: bool = False,
) -> List[HealthUnitResult]:
    """
    Lista as unidades de saúde do PEC para popular filtros (unidade_saude_id).

    Por padrão traz só as unidades ativas da Atenção Primária (UBS, postos,
    unidades móveis, apoio à saúde da família, saúde indígena e academia da saúde).
    Use apenas_atencao_primaria=False para incluir pronto atendimento, hospital,
    secretaria e demais tipos, e incluir_inativas=True para unidades desativadas.
    """

    filtros: list[str] = []
    params: list = []
    if apenas_atencao_primaria:
        filtros.append("AND tu.co_tipo_unidade_cnes = ANY(%s)")
        params.append(list(TIPOS_CNES_APS))
    if not incluir_inativas:
        filtros.append("AND COALESCE(us.st_ativo, 0) = 1")

    sql = _SQL_LISTAR_UNIDADES.format(filtros="\n".join(filtros))
    conn = get_db_conn(ctx)
    rows = query_all(conn, sql, tuple(params))

    results: List[HealthUnitResult] = []
    for row in rows:
        results.append(
            HealthUnitResult(
                unidade_id=int(row["unidade_id"]),
                cnes=str(row.get("cnes")) if row.get("cnes") is not None else None,
                name=str(row.get("nome")) if row.get("nome") is not None else None,
                localidade_id=int(row["localidade_id"]) if row.get("localidade_id") is not None else None,
                is_active=bool(row.get("ativo")),
                tipo_cnes=int(row["tipo_cnes"]) if row.get("tipo_cnes") is not None else None,
                tipo_unidade=str(row.get("tipo_descricao")) if row.get("tipo_descricao") is not None else None,
            )
        )
    return results


__all__ = ["TIPOS_CNES_APS", "listar_unidades_saude"]
