"""
Ferramentas para auditoria e acompanhamento das ações do Programa Saúde na Escola (PSE).
Baseado nas tabelas fato e dimensões do Data Warehouse do e-SUS PEC:
  - tb_fat_atividade_coletiva + tb_dim_inep: vinculação de ações às escolas cadastradas (código INEP);
  - tb_fat_atvdd_coletiva_ext: catálogo das 14 ações prioritárias do PSE (vacinação, antropometria, saúde bucal, etc.).
"""

from __future__ import annotations

import re
from typing import List, Optional

from mcp.server.fastmcp import Context

from ..db import query_all
from ..models import AcaoPSEResult
from . import get_db_conn, to_iso_date

_TETO_PSE = 200


def _format_ine(code: Optional[str]) -> Optional[str]:
    """Formata código INE de 10 dígitos com separador para evitar colisão com regex de telefone."""
    if not code:
        return None
    digits = "".join(ch for ch in str(code) if ch.isdigit())
    if len(digits) == 10:
        return f"{digits[:7]}-{digits[7:]}"
    return str(code)


_SQL_ACOES_PSE = """
SELECT
    fac.co_seq_fat_atividade_coletiva AS atividade_id,
    inep.nu_identificador AS inep_escola,
    inep.no_estabelecimento AS nome_escola,
    t.dt_registro::text AS data_atividade,
    de.nu_ine AS equipe_ine,
    de.no_equipe AS equipe_nome,
    dprof.no_profissional AS responsavel_nome,
    dcbo.nu_cbo AS cbo_codigo,
    COALESCE(fac.nu_participantes, 0) AS num_participantes,
    COALESCE(ext.st_prat_saude_situacao_vacinal, 0) AS verificacao_vacinal,
    COALESCE(ext.st_prat_saude_antropometria, 0) AS avaliacao_antropometrica,
    COALESCE(ext.st_prat_saude_escov_supervisio, 0) AS saude_bucal_escovacao,
    COALESCE(ext.st_prat_saude_aplic_topi_fluor, 0) AS saude_bucal_fluor,
    COALESCE(ext.st_prat_saude_saude_ocular, 0) AS saude_ocular,
    COALESCE(ext.st_prat_saude_saude_auditiva, 0) AS saude_auditiva
FROM tb_fat_atividade_coletiva fac
JOIN tb_dim_inep inep ON inep.co_seq_dim_inep = fac.co_dim_inep
LEFT JOIN tb_fat_atvdd_coletiva_ext ext ON ext.co_fat_atividade_coletiva = fac.co_seq_fat_atividade_coletiva
LEFT JOIN tb_dim_tempo t ON t.co_seq_dim_tempo = fac.co_dim_tempo
LEFT JOIN tb_dim_equipe de ON de.co_seq_dim_equipe = fac.co_dim_equipe
LEFT JOIN tb_dim_profissional dprof ON dprof.co_seq_dim_profissional = fac.co_dim_profissional
LEFT JOIN tb_dim_cbo dcbo ON dcbo.co_seq_dim_cbo = fac.co_dim_cbo
WHERE 1=1
  {where_clauses}
ORDER BY fac.co_seq_fat_atividade_coletiva DESC
LIMIT %s;
"""


def listar_acoes_pse(
    ctx: Context,
    inep_escola: Optional[str] = None,
    ine_equipe: Optional[str] = None,
    acao_tematica: Optional[str] = None,
    limite: int = 50,
) -> List[AcaoPSEResult]:
    """
    Lista ações de saúde realizadas no ambiente escolar vinculadas ao código INEP (Programa Saúde na Escola - PSE).

    Permite auditar metas municipais de verificação vacinal, avaliação antropométrica,
    saúde bucal (escovação supervisionada e aplicação de flúor), saúde ocular e auditiva.
    """
    conn = get_db_conn(ctx)
    safe_limit = max(1, min(int(limite), _TETO_PSE))

    where_clauses: list[str] = []
    params: list = []

    if inep_escola and inep_escola.strip():
        clean_inep = re.sub(r"\D", "", inep_escola.strip())
        where_clauses.append("AND inep.nu_identificador LIKE %s")
        params.append(f"{clean_inep}%")

    if ine_equipe and ine_equipe.strip():
        clean_ine = re.sub(r"\D", "", ine_equipe.strip())
        where_clauses.append("AND de.nu_ine LIKE %s")
        params.append(f"{clean_ine}%")

    if acao_tematica and acao_tematica.strip():
        acao = acao_tematica.strip().lower()
        if acao in ("vacinacao", "vacinal", "vacina"):
            where_clauses.append("AND ext.st_prat_saude_situacao_vacinal = 1")
        elif acao in ("antropometria", "peso_altura", "nutricao"):
            where_clauses.append("AND ext.st_prat_saude_antropometria = 1")
        elif acao in ("saude_bucal", "bucal", "odonto"):
            where_clauses.append(
                "AND (ext.st_prat_saude_escov_supervisio = 1 OR ext.st_prat_saude_aplic_topi_fluor = 1)"
            )
        elif acao in ("ocular", "visao", "olhos"):
            where_clauses.append("AND ext.st_prat_saude_saude_ocular = 1")
        elif acao in ("auditiva", "audicao", "ouvido"):
            where_clauses.append("AND ext.st_prat_saude_saude_auditiva = 1")

    where_sql = "\n  ".join(where_clauses)
    sql = _SQL_ACOES_PSE.format(where_clauses=where_sql)
    params.append(safe_limit)

    rows = query_all(conn, sql, tuple(params))
    return [
        AcaoPSEResult(
            atividade_id=int(row.get("atividade_id") or 0),
            inep_escola=row.get("inep_escola"),
            nome_escola=row.get("nome_escola"),
            data_atividade=to_iso_date(row.get("data_atividade")),
            equipe_ine=_format_ine(row.get("equipe_ine")),
            equipe_nome=row.get("equipe_nome"),
            responsavel_nome=row.get("responsavel_nome"),
            cbo_codigo=row.get("cbo_codigo"),
            num_participantes=int(row.get("num_participantes") or 0),
            verificacao_vacinal=bool(row.get("verificacao_vacinal")),
            avaliacao_antropometrica=bool(row.get("avaliacao_antropometrica")),
            saude_bucal_escovacao=bool(row.get("saude_bucal_escovacao")),
            saude_bucal_fluor=bool(row.get("saude_bucal_fluor")),
            saude_ocular=bool(row.get("saude_ocular")),
            saude_auditiva=bool(row.get("saude_auditiva")),
        )
        for row in rows
    ]


__all__ = ["listar_acoes_pse"]
