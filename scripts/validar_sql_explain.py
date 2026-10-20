"""
Confere todas as SQLs das tools contra um banco e-SUS PEC real, só com EXPLAIN.

EXPLAIN pede ao PostgreSQL o plano da consulta: ele resolve cada tabela, coluna,
tipo e função, mas não executa a consulta nem devolve linha nenhuma. Serve para
validar o schema de uma versão nova do PEC sem ler dado de paciente.

Uso (na raiz do repositório):
    PEC_DB_DSN="postgresql://usuario_leitura:senha@host:5432/esus" \
        uv run python scripts/validar_sql_explain.py

Sai com código 1 se alguma SQL falhar.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "tests")]

import casos_tools as ct  # noqa: E402
from pec_mcp.config import get_db_dsn  # noqa: E402
from pec_mcp.db import ConexaoSomenteLeitura  # noqa: E402

# Variações de argumentos para exercitar os filtros opcionais de cada tool.
VARIACOES = {
    "capturar_paciente": [dict(sex="F", unidade_saude_id=1, equipe_id=1, micro_area="01", age_min=1)],
    "contar_pacientes": [dict(cid_codes=["E11", "I10"], cid_logic="AND", ciap_code="T90", condition_text="x", unidade_saude_id=1)],
    "listar_condicoes_pacientes": [dict(cid_code="E11", ciap_code="T90", condition_text="x", equipe_id=1, micro_area="01")],
    "listar_registros_hgt": [dict(paciente_id=1, momento="jejum", data_inicio="2024-01-01", data_fim="2024-12-31")],
    "listar_registros_pa": [dict(paciente_id=1, data_inicio="2024-01-01", data_fim="2024-12-31")],
    "listar_registros_antropometria": [dict(paciente_id=1, data_inicio="2024-01-01", data_fim="2024-12-31")],
    "listar_resultados_hba1c": [dict(paciente_id=1, data_inicio="2024-01-01", data_fim="2024-12-31")],
    "listar_prescricoes_medicamentos": [dict(paciente_id=1, estado="ativo", medicamento="x")],
    "listar_gestantes": [dict(trimestre="2", unidade_saude_id=1, equipe_id=1, micro_area="01")],
    "listar_visitas_acs": [
        dict(nome_profissional="x", acompanhamento="gestante", motivo="periodica", unidade_saude_id=1, com_pa=True, ultimos_dias=30),
        dict(apenas_contagem=True, data_inicio="2024-01-01", data_fim="2024-12-31"),
    ],
    "contar_pacientes_sem_consulta": [dict(tipo="gestante", unidade_saude_id=1, equipe_id=1, micro_area="01")],
    "listar_pacientes_sem_consulta": [dict(tipo="diabetes", unidade_saude_id=1)],
    "listar_vacinas_paciente": [dict(paciente_id=1, imunobiologico="x")],
    "listar_procedimentos_clinicos": [dict(paciente_id=1, codigo_sigtap="0301", termo_busca="x")],
    "listar_atendimentos_odonto": [dict(paciente_id=1, cbo_codigo="2232", apenas_primeira_consulta=True, apenas_tratamento_concluido=True, apenas_gestantes=True)],
    "listar_procedimentos_odonto": [dict(paciente_id=1, grupo="exodontia")],
    "listar_problemas_odonto": [dict(paciente_id=1, cid_codigo="K02", ciap_codigo="D82")],
    "listar_atividades_coletivas": [dict(ine_equipe="1", cbo_codigo="2", apenas_emulti=True, apenas_pts=True, tipo_atividade=1)],
    "consultar_participacao_coletiva": [dict(paciente_id=1)],
    "listar_acoes_pse": [dict(inep_escola="1", ine_equipe="1", acao_tematica="vacinacao")],
    "obter_codigos_condicao_saude": [dict(condicao="asma bronquica")],
}


def main() -> int:
    conexao = ConexaoSomenteLeitura(get_db_dsn())
    falhas: list[str] = []
    total = 0
    atual = {"tool": ""}

    def explicar(conn, sql, params=None):
        nonlocal total
        total += 1
        with conexao.cursor() as cur:
            try:
                cur.execute("EXPLAIN " + sql, params or ())
            except Exception as exc:  # noqa: BLE001
                primeira = str(exc).strip().splitlines()[0]
                falhas.append(f"{atual['tool']}: {primeira}")
        return []

    def explicar_um(conn, sql, params=None):
        explicar(conn, sql, params)
        return {"total": 0, "count": 0}

    for modulo in {c.modulo for c in ct.CASOS.values()}:
        mod = importlib.import_module(f"pec_mcp.tools.{modulo}")
        if hasattr(mod, "query_all"):
            mod.query_all = explicar
        if hasattr(mod, "query_one"):
            mod.query_one = explicar_um

    for nome, caso in ct.CASOS.items():
        for args in [caso.argumentos, *VARIACOES.get(nome, [])]:
            atual["tool"] = nome
            caso.tool(ct.ContextoFalso(), **args)

    conexao.close()
    print(f"{total} consultas verificadas com EXPLAIN, {len(falhas)} com erro.")
    for falha in falhas:
        print(f"  ERRO {falha}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
