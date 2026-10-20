"""
Camada fina de acesso a dados usando psycopg2.

Mantenha aqui apenas o essencial para evitar complexidade desnecessária
e facilitar testes (princípios KISS e YAGNI).
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection(dsn: str):
    """
    Abre conexão com o PostgreSQL usando RealDictCursor para devolver dicts.

    Quem chama gerencia o ciclo de vida (abrir/fechar), permitindo reuso
    de conexão no lifespan do servidor MCP.
    """

    if not dsn or not dsn.strip():
        raise ValueError("A DSN clínica da instalação é obrigatória.")
    return psycopg2.connect(dsn=dsn, cursor_factory=RealDictCursor)


class ConexaoSomenteLeitura:
    """
    Conexão de vida longa para o lifespan do servidor.

    Abre a sessão como somente leitura, com statement_timeout, e reabre sozinha
    se o banco derrubar a conexão (reinício do PEC, atualização, queda de rede).
    Sem isso, o servidor ficaria respondendo erro até ser reiniciado.
    Expõe só o que query_all/query_one usam: cursor() e close().
    """

    def __init__(self, dsn: str, statement_timeout_ms: int = 30_000):
        self._dsn = dsn
        self._timeout_ms = int(statement_timeout_ms)
        self._conn = None

    def abrir(self):
        if self._conn is None or self._conn.closed:
            conn = get_connection(self._dsn)
            conn.set_session(readonly=True, autocommit=True)
            with conn.cursor() as cur:
                # Reforço explícito: vale mesmo se o set_session mudar de comportamento.
                cur.execute("SET default_transaction_read_only = on")
                cur.execute("SET statement_timeout = %s", (self._timeout_ms,))
                cur.execute("SET application_name = 'pec-mcp'")
            self._conn = conn
        return self._conn

    def cursor(self, *args, **kwargs):
        return self.abrir().cursor(*args, **kwargs)

    @property
    def closed(self) -> bool:
        return self._conn is None or bool(self._conn.closed)

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
        self._conn = None


def query_all(conn, sql: str, params: Optional[Sequence] = None) -> list[dict]:
    """
    Executa consulta de leitura e retorna lista de dicionários.

    Mantemos helper simples para evitar repetição de boilerplate.
    """

    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        rows: Iterable[dict] = cur.fetchall()
    return list(rows)


def query_one(conn, sql: str, params: Optional[Sequence] = None) -> Optional[dict]:
    """
    Executa consulta de leitura e retorna um único registro ou None.
    """

    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        row = cur.fetchone()
    return row if row is not None else None


__all__ = ["ConexaoSomenteLeitura", "get_connection", "query_all", "query_one"]
