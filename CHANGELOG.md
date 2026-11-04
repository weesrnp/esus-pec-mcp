# Changelog

## 1.2.0 - 2026-11-03

### Otimizado

- **Pilar 4 de Otimizacao:** Implementada camada de cache em memoria com TTL (pec_mcp.cache.cached_dimension) para consultas de dimensoes estaticas e imutaveis.
- As tools listar_unidades_saude e obter_codigos_condicao_saude agora reutilizam resultados cacheados por 1 hora, eliminando round-trips repetitivos ao PostgreSQL em fluxos conversacionais densos.
- Adicionado utilitario clear_dimension_cache() e suporte a isolamento por fixture em testes unitarios.

### Testes

- 2 novos testes unitarios adicionados para cobertura de armazenamento, reuso e expiracao do cache com TTL.
- Suite de testes completa com 457 testes passando sem regressoes.
## 1.1.1 — 2026-10-20

### Corrigido

- `listar_registros_antropometria`, `listar_registros_pa` e `listar_registros_hgt` liam `tl_medicao`, que no PEC é a tabela de log (Hibernate Envers) de `tb_medicao`: uma linha por revisão do registro. Uma medição editada aparecia repetida e uma excluída continuava aparecendo. As três tools agora leem `tb_medicao`.
- Novo teste de regressão roda todas as tools e falha se alguma SQL citar uma tabela `tl_`.

## 1.1.0 — 2026-10-20

Validado contra o schema oficial do PEC 5.5.28 no PostgreSQL 16 e numa instalação em produção no PostgreSQL 9.6.

### Corrigido

- Cinco tools falhavam com "column does not exist": `listar_vacinas_paciente`, `listar_procedimentos_clinicos`, `listar_atendimentos_odonto`, `listar_procedimentos_odonto` e `listar_problemas_odonto`.
- `listar_procedimentos_clinicos` falhava no PostgreSQL 9.6 (literal sem tipo em CTE com `UNION`).
- `listar_visitas_acs` devolvia o id do Data Warehouse como `paciente_id`; agora devolve o `co_seq_cidadao`, como as demais tools. O filtro `unidade_saude_id` passou a usar o mesmo id de `listar_unidades_saude`.
- `listar_gestantes` ligava a ecografia à gestação por ids sem relação; a DPP agora vem da USG mais recente do mesmo prontuário.
- Códigos CID com ponto (`I11.0`, `E11.9`) nunca casavam com `tb_cid10`, que grava sem ponto. As expressões regulares de `obter_codigos_condicao_saude` também não reconheciam o ponto nem colapsavam espaços.
- Nome do profissional vinha nulo quando não havia nome social.
- Peso ou altura em texto não numérico em `tl_medicao` derrubavam a consulta.
- `data_fim` cortava o próprio dia em medições e HbA1c.
- Saúde bucal: ABPO010, ABPO015 e ABPO016 eram classificados como exodontia; o B3 passou a contar só exodontia de dente permanente.
- `listar_atividades_coletivas` duplicava atividades com várias pautas.
- Busca ativa e lista de gestantes incluíam pessoas falecidas.
- `name_starts_with` aceitava `%` e listava o cadastro inteiro.

### Alterado

- Transporte padrão passou a ser `stdio` (era `streamable-http`).
- `listar_ultimos_atendimentos_soap` tem limite padrão 50 e teto 200 (antes, sem limite).
- `listar_unidades_saude` lista por padrão só as unidades ativas da APS e devolve `tipo_cnes` e `tipo_unidade`.
- CPF, CNS, telefone e e-mail digitados em texto livre saem mascarados.
- A conexão usa `statement_timeout` (30 s, `PEC_DB_STATEMENT_TIMEOUT_MS`), reforça o modo somente leitura e se reconecta sozinha.

### Novo

- `scripts/validar_sql_explain.py`: confere todas as SQLs contra o banco com `EXPLAIN`, sem ler linhas.

## 1.0.0

Versão inicial com 24 tools.
