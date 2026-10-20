"""Servidor FastMCP para execução standalone das tools clínicas."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import ServerSettings, get_db_dsn, get_server_settings, get_statement_timeout_ms
from .db import ConexaoSomenteLeitura
from .tools.atendimentos import listar_ultimos_atendimentos_soap
from .tools.atividades_coletivas import (
    consultar_participacao_coletiva,
    listar_atividades_coletivas,
    listar_profissionais_atividade_coletiva,
)
from .tools.condicoes import listar_condicoes_pacientes
from .tools.contar_pacientes import contar_pacientes
from .tools.medicoes import (
    listar_registros_antropometria,
    listar_registros_hgt,
    listar_registros_pa,
)
from .tools.exames import listar_resultados_hba1c
from .tools.gestantes import listar_gestantes
from .tools.obter_codigos_condicao_saude import obter_codigos_condicao_saude
from .tools.paciente import capturar_paciente
from .tools.prescricoes import listar_prescricoes_medicamentos
from .tools.procedimentos import listar_procedimentos_clinicos
from .tools.pse import listar_acoes_pse
from .tools.saude_bucal import (
    listar_atendimentos_odonto,
    listar_problemas_odonto,
    listar_procedimentos_odonto,
)
from .tools.sem_consulta import (
    contar_pacientes_sem_consulta,
    listar_pacientes_sem_consulta,
)
from .tools.unidades import listar_unidades_saude
from .tools.vacinas import listar_vacinas_paciente
from .tools.visitas_acs import listar_visitas_acs


STANDALONE_TOOLS = (
    capturar_paciente,
    obter_codigos_condicao_saude,
    listar_condicoes_pacientes,
    contar_pacientes,
    listar_unidades_saude,
    listar_ultimos_atendimentos_soap,
    listar_registros_antropometria,
    listar_registros_pa,
    listar_registros_hgt,
    listar_resultados_hba1c,
    listar_prescricoes_medicamentos,
    listar_visitas_acs,
    listar_gestantes,
    contar_pacientes_sem_consulta,
    listar_pacientes_sem_consulta,
    listar_vacinas_paciente,
    listar_procedimentos_clinicos,
    listar_atendimentos_odonto,
    listar_procedimentos_odonto,
    listar_problemas_odonto,
    listar_atividades_coletivas,
    consultar_participacao_coletiva,
    listar_profissionais_atividade_coletiva,
    listar_acoes_pse,
)


def _build_lifespan(dsn: str | None):
    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncIterator[dict[str, Any]]:
        connection = ConexaoSomenteLeitura(
            dsn or get_db_dsn(), statement_timeout_ms=get_statement_timeout_ms()
        )
        # Abre já na subida: credencial errada aparece logo, não na 1ª pergunta.
        connection.abrir()
        try:
            yield {"db_conn": connection}
        finally:
            connection.close()

    return lifespan


def create_server(
    *,
    settings: ServerSettings | None = None,
    dsn: str | None = None,
) -> FastMCP:
    """Cria o servidor standalone; a conexão só é aberta no lifespan."""

    resolved_settings = settings or get_server_settings()

    server = FastMCP(
        "pec-mcp",
        host=resolved_settings.host,
        port=resolved_settings.port,
        lifespan=_build_lifespan(dsn),
    )
    for tool in STANDALONE_TOOLS:
        server.tool()(tool)
    return server


# Mantém um objeto importável para ASGI/composição e para clientes MCP.
mcp = create_server()


def main() -> None:
    """Inicia o processo standalone usando a configuração do ambiente."""

    settings = get_server_settings()
    server = create_server(settings=settings)
    server.run(transport=settings.transport)


if __name__ == "__main__":  # pragma: no cover - exercitado como processo
    main()


__all__ = ["STANDALONE_TOOLS", "create_server", "main", "mcp"]
