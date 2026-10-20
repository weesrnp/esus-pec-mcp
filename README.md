# e-SUS PEC MCP Server

```
===================================================================================
███████╗      ███████╗██╗   ██╗███████╗    ██████╗ ███████╗ ██████╗    ███╗   ███╗ ██████╗██████╗ 
██╔════╝      ██╔════╝██║   ██║██╔════╝    ██╔══██╗██╔════╝██╔════╝    ████╗ ████║██╔════╝██╔══██╗
█████╗  █████╗███████╗██║   ██║███████╗    ██████╔╝█████╗  ██║         ██╔████╔██║██║     ██████╔╝
██╔══╝  ╚════╝╚════██║██║   ██║╚════██║    ██╔═══╝ ██╔══╝  ██║         ██║╚██╔╝██║██║     ██╔═══╝ 
███████╗      ███████║╚██████╔╝███████║    ██║     ███████╗╚██████╗    ██║ ╚═╝ ██║╚██████╗██║     
╚══════╝      ╚══════╝ ╚═════╝ ╚══════╝    ╚═╝     ╚══════╝ ╚═════╝    ╚═╝     ╚═╝ ╚═════╝╚═╝     
===================================================================================
```

> **Servidor Model Context Protocol (MCP) de alta performance, auditoria clínica e inteligência em saúde pública para o Data Warehouse do e-SUS APS / PEC (PostgreSQL).**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![MCP Specification](https://img.shields.io/badge/MCP-2024--11--05-orange.svg)](https://modelcontextprotocol.io/)
[![Database PostgreSQL](https://img.shields.io/badge/PostgreSQL-9.6%20a%2016-336791.svg)](https://www.postgresql.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Security LGPD Compliant](https://img.shields.io/badge/LGPD-Blindagem%20Estrita-success.svg)](#seguran%C3%A7a-e-blindagem-lgpd)
[![Tests Passing](https://img.shields.io/badge/tests-454%20passed-brightgreen.svg)](#testes-e-garantia-de-qualidade)

---

## Sumário

- [Visão Geral](#visão-geral)
- [Stack Tecnológica](#stack-tecnológica)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Segurança e Blindagem LGPD](#segurança-e-blindagem-lgpd)
- [Catálogo de Ferramentas (24 Tools)](#catálogo-de-ferramentas-24-tools)
  - [1. Identificação e Demografia](#1-identificação-e-demografia)
  - [2. Condições Crônicas e Diagnósticos](#2-condições-crônicas-e-diagnósticos)
  - [3. Atendimentos Clínicos e Prescrições](#3-atendimentos-clínicos-e-prescrições)
  - [4. Medições e Sinais Vitais](#4-medições-e-sinais-vitais)
  - [5. Imunização e Procedimentos SIGTAP](#5-imunização-e-procedimentos-sigtap)
  - [6. Ciclos de Vida e Busca Ativa](#6-ciclos-de-vida-e-busca-ativa)
  - [7. Saúde Bucal (eSB / Indicadores B1–B6)](#7-saúde-bucal-esb--indicadores-b1b6)
  - [8. Atividades Coletivas e eMulti (Indicadores M1–M2)](#8-atividades-coletivas-e-emulti-indicadores-m1m2)
  - [9. Programa Saúde na Escola (PSE)](#9-programa-saúde-na-escola-pse)
- [Instalação e Pré-requisitos](#instalação-e-pré-requisitos)
- [Configuração de Ambiente](#configuração-de-ambiente)
- [Execução do Servidor](#execução-do-servidor)
- [Integração com Clientes MCP](#integração-com-clientes-mcp)
- [Testes e Garantia de Qualidade](#testes-e-garantia-de-qualidade)
- [Licença](#licença)

---

## Visão Geral

O **e-SUS PEC MCP Server** é uma infraestrutura de integração padronizada baseada na especificação do **Model Context Protocol (MCP)**, desenvolvida para conectar sistemas e ferramentas analíticas diretamente à base de dados relacional e ao Data Warehouse do **Prontuário Eletrônico do Cidadão (PEC)** do Ministério da Saúde.

O projeto permite extração clínica, rastreamento de linhas de cuidado, auditoria de cofinanciamento da Atenção Primária à Saúde (APS) e monitoramento nominal de indicadores com garantia de **leitura estrita (`READ ONLY`)** e **blindagem total de dados pessoais sensíveis (LGPD)**.

---

## Stack Tecnológica

| Componente | Tecnologia | Detalhes |
|---|---|---|
| **Linguagem** | Python 3.10+ | Compatível com runtimes 3.10, 3.11, 3.12 e 3.13 |
| **Framework MCP** | FastMCP (`mcp[cli]<2`) | Suporte a transportes `stdio` e `streamable-http` (SSE) |
| **Banco de Dados** | PostgreSQL 9.6 a 16 (validado no 9.6 e no 16 com o PEC 5.5.28) | Sessão somente leitura, `statement_timeout` de 30 s e reconexão automática |
| **Driver Relacional** | `psycopg2-binary >= 2.9` | Cursors otimizados com `RealDictCursor` e queries parametrizadas |
| **Data Warehouse** | Star Schema e-SUS APS | Tabelas fato (`tb_fat_*`), dimensões (`tb_dim_*`) e cadastro (`tb_cidadao`) |
| **Gerenciador de Pacotes** | `uv` / `pip` | Builds determinísticos e resolução ágil de dependências |
| **Qualidade & Auditoria** | `pytest` + AST + Regex | Varreduras sintéticas de PII em runtime e checagem léxica no SQL |

---

## Arquitetura do Sistema

```mermaid
flowchart TD
    subgraph CLIENTS["Clientes MCP & Camada Analítica"]
        CLI["CLI / Desktop MCP Client"]
        DASH["Dashboards & Serviços Analíticos"]
    end

    subgraph SERVER["Servidor FastMCP (pec-mcp-server)"]
        TRANSPORT["Transport Layer (stdio / HTTP Streamable)"]
        SECURITY["Filtros de Segurança & LGPD"]
        TOOLS["24 Ferramentas Especializadas"]
        MODELS["Contratos Tipados (TypedDict)"]
    end

    subgraph DW["PostgreSQL — e-SUS PEC (Read-Only)"]
        TRANSACTION["Sessão Segura: readonly=on, timeout=30s"]
        FAT["Tabelas Fato (tb_fat_*)"]
        DIM["Tabelas Dimensão (tb_dim_*)"]
        CORE["Tabelas Clínicas (tb_cidadao, tb_prontuario)"]
    end

    CLI --> TRANSPORT
    DASH --> TRANSPORT
    TRANSPORT --> SECURITY
    SECURITY --> TOOLS
    TOOLS --> MODELS
    TOOLS --> TRANSACTION
    TRANSACTION --> FAT
    TRANSACTION --> DIM
    TRANSACTION --> CORE
```

---

## Segurança e Blindagem LGPD

O servidor opera sob o princípio da **minimização absoluta de dados** (Lei Geral de Proteção de Dados - Lei nº 13.709/2018):

1. **Ausência Total de Colunas Proibidas no SQL**:
   A suíte de testes estática (AST) impede que qualquer consulta utilize ou selecione colunas de identificação civil direta:
   - `nu_cpf`, `nu_cns`, `no_mae`, `nu_telefone`, `nu_celular`, `no_logradouro`, `nu_numero_logradouro`, `no_bairro`, `ds_email`, `nu_cep`.
2. **Anonimização de Nomes em Tempo Real**:
   Nenhum nome completo de paciente é retornado. A função `to_initials()` converte nomes em iniciais tratadas (ex.: *"Maria da Silva Santos"* $\rightarrow$ *"MSS"*), descartando preposições e preservando a confidencialidade.
3. **Cálculo de Idade sem Exposição de Nascimento**:
   A data exata de nascimento nunca é exposta na saída pública. A função `compute_age_display()` deriva representações textuais amigáveis (ex.: *"41 anos"*, *"6 meses"*, *"15 dias"*), calculadas no servidor.
4. **Mascaramento de Códigos Identificadores**:
   - Procedimentos SIGTAP: Mascarados no padrão oficial `XX.XX.XX.XXX-X` para prevenir falso-positivo com números de contato.
   - Equipes INE: Formatadas com delimitador `XXXXXXX-XXX`.
5. **Tetos Rígidos de Paginação**:
   Todas as consultas de lista têm teto de paginação forçado (200, ou 500 em prescrições e visitas), inclusive quando o `limite` não é informado.
6. **Máscara em Texto Livre**:
   CPF, CNS, telefone e e-mail digitados em campos de texto livre (SOAP, observações de problemas, recomendações e posologia de receitas) saem substituídos por `[CPF removido]`, `[telefone removido]` etc. Nomes próprios no texto livre **não** têm padrão detectável e continuam aparecendo: trate esses campos como dado sensível.
7. **Sessão Somente Leitura com Timeout**:
   A conexão abre com `default_transaction_read_only = on` e `statement_timeout` (30 s por padrão, `PEC_DB_STATEMENT_TIMEOUT_MS`). Mesmo assim, use um usuário do PostgreSQL que só tenha `SELECT`.

---

## Catálogo de Ferramentas (24 Tools)

### 1. Identificação e Demografia

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `capturar_paciente` | Busca paciente de forma segura por identificador, iniciais, sexo ou faixa etária. | `paciente_id`, `name_starts_with`, `sex`, `age_min`, `age_max`, `unidade_saude_id` | `paciente_id`, `name` (iniciais), `age`, `sex` |
| `contar_pacientes` | Retorna o quantitativo agregado de pacientes segundo filtros clínicos e demográficos. | Filtros demográficos e/ou códigos CID/CIAP | `count` (inteiro) |
| `listar_unidades_saude` | Lista as unidades para parametrizar filtros. Por padrão, só as ativas da APS (tipos CNES 01, 02, 32, 40, 71, 72 e 74). | `apenas_atencao_primaria`, `incluir_inativas` | `unidade_id`, `cnes`, `name`, `is_active`, `tipo_cnes`, `tipo_unidade` |

### 2. Condições Crônicas e Diagnósticos

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `listar_condicoes_pacientes` | Consulta condições ativas e diagnósticos (CID-10 e CIAP-2) registrados nos prontuários. | `paciente_id`, `cid_code`, `ciap_code`, `condition_text`, `limite` | Lista de `ConditionResult` (códigos, descrições, status, início/fim) |
| `obter_codigos_condicao_saude` | Mapeia tabelas de referência de termos clínicos para códigos padronizados CID-10 e CIAP-2. | `condicao` (ex.: *"hipertensao"*, *"diabetes"*, *"asma"*) | Lista de códigos e descrições oficiais |

### 3. Atendimentos Clínicos e Prescrições

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `listar_ultimos_atendimentos_soap` | Histórico clínico com notas SOAP (Subjetivo, Objetivo, Avaliação e Plano), CBO e profissional. | `paciente_id` (obrigatório), `limite` | Notas SOAP estruturadas, data/hora e profissional |
| `listar_prescricoes_medicamentos` | Histórico farmacológico com posologia, concentração, via, duração, uso contínuo e status. | `paciente_id` (obrigatório), `estado`, `medicamento`, `limite` | Doses, vigência, status de renovação ou interrupção |

### 4. Medições e Sinais Vitais

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `listar_registros_antropometria` | Série temporal de peso, altura e IMC calculados, unificando PEC e visitas domiciliares. | `paciente_id` (obrigatório), `limite` | `peso_kg`, `altura_cm`, `imc`, `data_medicao`, `origem` |
| `listar_registros_pa` | Histórico de pressão arterial decomposta em sistólica (PAS) e diastólica (PAD). | `paciente_id` (obrigatório), `limite` | `pas`, `pad`, `pressao_raw`, `data_medicao`, `origem` |
| `listar_registros_hgt` | Histórico de glicemia capilar (HGT em mg/dL) com momento da aferição (jejum, pós-prandial). | `paciente_id` (obrigatório), `tipo_glicemia`, `limite` | `valor_mg_dl`, `momento_afericao`, `data_medicao` |
| `listar_resultados_hba1c` | Resultados laboratoriais históricos de hemoglobina glicada para monitoramento de diabetes. | `paciente_id` (obrigatório), `data_inicio`, `data_fim`, `limite` | `valor_percentual`, `data_realizacao`, `data_resultado` |

### 5. Imunização e Procedimentos SIGTAP

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `listar_vacinas_paciente` | Histórico vacinal do Data Warehouse (`tb_fat_vacinacao_vacina`), doses, lotes e validade. | `paciente_id` (obrigatório), `limite` | `imunobiologico`, `sigla`, `dose`, `data_aplicacao`, `lote` |
| `listar_procedimentos_clinicos` | Procedimentos individuais e ambulatoriais unificados com formatação SIGTAP oficial. | `paciente_id` (obrigatório), `codigo_sigtap`, `termo_busca`, `limite` | Código SIGTAP formatado, quantidade, profissional e contexto |

### 6. Ciclos de Vida e Busca Ativa

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `listar_gestantes` | Monitoramento de gestações ativas, idade gestacional em semanas/dias, DPP e estratificação de risco. | `unidade_id`, `equipe_id`, `microarea`, `trimestre`, `alto_risco` | Iniciais, DPP, semanas gestacionais, tipo e risco |
| `listar_visitas_acs` | Registro de visitas domiciliares dos Agentes Comunitários de Saúde (motivo, desfecho e ações). | `profissional_id`, `paciente_id`, `data_inicio`, `data_fim`, `limite` | Desfecho da visita, acompanhamentos e aferições |
| `contar_pacientes_sem_consulta` | Contagem de busca ativa para hipertensos, diabéticos ou gestantes sem consulta recente. | `tipo` (`hipertensao`, `diabetes`, `gestante`), `dias_sem_consulta` | Quantitativo total de pacientes elegíveis |
| `listar_pacientes_sem_consulta` | Lista nominal anonimizada de pacientes elegíveis para busca ativa e agendamento preventivo. | `tipo`, `dias_sem_consulta`, `unidade_saude_id`, `limite` | Iniciais, idade textual, sexo, data da última consulta |

### 7. Saúde Bucal (eSB / Indicadores B1–B6)

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `listar_atendimentos_odonto` | Consultas odontológicas individuais, condutas de tratamento concluído (B2) e primeira consulta (B1). | `paciente_id`, `cbo_codigo`, `apenas_primeira_consulta`, `apenas_tratamento_concluido`, `limite` | Dados do atendimento, fornecimento de insumos e vigilância |
| `listar_procedimentos_odonto` | Procedimentos em cadeira odontológica: exodontias (B3), preventivos (B4) e restaurações TRA/ART (B6). | `paciente_id` (obrigatório), `codigo_sigtap`, `grupo` (`exodontia`, `preventivo`, `tra_art`), `limite` | Quantidade, flags de classificação e dados profissionais |
| `listar_problemas_odonto` | Condições e diagnósticos bucais (CID-10 e CIAP-2) avaliados nos atendimentos de saúde bucal. | `paciente_id` (obrigatório), `cid_codigo`, `ciap_codigo`, `limite` | CID, CIAP, situação clínica e profissional responsável |

### 8. Atividades Coletivas e eMulti (Indicadores M1–M2)

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `listar_atividades_coletivas` | Ações coletivas, reuniões de equipe e grupos com filtro de Discussão de Caso / PTS (M2). | `ine_equipe`, `cbo_codigo`, `apenas_emulti`, `apenas_pts`, `tipo_atividade`, `limite` | Temas de reunião, saúde, práticas coletivas e participantes |
| `consultar_participacao_coletiva` | Participações individuais anônimas em grupos de saúde, tabagismo e avaliação nutricional. | `atividade_id` ou `paciente_id` (obrigatório ao menos um), `limite` | Métricas antropométricas e evolução no grupo |
| `listar_profissionais_atividade_coletiva` | Condutores da atividade para validação de ações conjuntas e matriciamento (28 CBOs eMulti). | `atividade_id` (obrigatório) | Profissional, CBO, flag `is_emulti` e INE da equipe |

### 9. Programa Saúde na Escola (PSE)

| Ferramenta | Descrição | Principais Parâmetros | Saída |
|---|---|---|---|
| `listar_acoes_pse` | Ações de saúde escolar cruzadas com escolas cadastradas (código INEP) e temas prioritários. | `inep_escola`, `ine_equipe`, `acao_tematica` (`vacinacao`, `antropometria`, `saude_bucal`, etc.), `limite` | Escola INEP, equipe, participantes e flags temáticas |

---

## Instalação e Pré-requisitos

### Pré-requisitos
- **Python**: versão 3.10 ou superior.
- **Banco de Dados**: instância acessível do PostgreSQL contendo o schema do e-SUS PEC (produção, réplica de leitura ou staging de testes).

### Instalação via `uv` (Recomendado)

```bash
# Criar o ambiente virtual isolado
uv venv .venv

# Ativar o ambiente virtual
# No Linux/macOS:
source .venv/bin/activate
# No Windows:
.venv\Scripts\activate

# Instalar em modo editável com dependências
uv pip install -e .
```

### Instalação via `pip` tradicional

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

---

## Configuração de Ambiente

Crie um arquivo `.env` na raiz do projeto a partir do modelo fornecido:

```bash
cp .env.example .env
```

Configure uma string de conexão unificada em `PEC_DB_DSN` **ou** as variáveis individuais:

```ini
# Configuração Unificada de DSN (Prioritária)
PEC_DB_DSN=postgresql://usuario_leitura:senha_segura@127.0.0.1:5432/esus_db?sslmode=prefer

# Ou Parâmetros Individuais:
PEC_DB_HOST=127.0.0.1
PEC_DB_PORT=5432
PEC_DB_NAME=esus_db
PEC_DB_USER=usuario_leitura
PEC_DB_PASSWORD=senha_segura
PEC_DB_SSLMODE=prefer

# Timeout por consulta, em milissegundos (padrão 30000)
PEC_DB_STATEMENT_TIMEOUT_MS=30000

# Configuração do Transporte MCP (padrão: stdio)
MCP_TRANSPORT=stdio
MCP_HTTP_HOST=127.0.0.1
MCP_HTTP_PORT=5174
```

---

## Execução do Servidor

### 1. Modo Padrão via Stdio (Para Clientes MCP Locais e IDEs)

```bash
# Executando via entrypoint instalado
pec-mcp

# Ou via módulo Python
python -m pec_mcp.server
```

### 2. Modo HTTP Streamable (Para Serviços Remotos e Redes Locais)

Defina `MCP_TRANSPORT=streamable-http` no arquivo `.env` ou via linha de comando:

```bash
# Executando servidor HTTP MCP
MCP_TRANSPORT=streamable-http pec-mcp
```
O endpoint estará disponível em `http://127.0.0.1:5174/mcp`.

> **Atenção:** o modo HTTP não tem autenticação. Mantenha `MCP_HTTP_HOST=127.0.0.1`. Expor em `0.0.0.0` deixa qualquer máquina da rede consultar dados clínicos; se precisar de acesso remoto, coloque um proxy com autenticação e TLS na frente.

---

## Integração com Clientes MCP

Para integrar com qualquer cliente compatível com MCP, adicione a configuração no arquivo de configuração do seu cliente:

```json
{
  "mcpServers": {
    "esus-pec": {
      "command": "uv",
      "args": [
        "--directory",
        "D:\\caminho\\para\\esus-pec-mcp",
        "run",
        "python",
        "-m",
        "pec_mcp.server"
      ],
      "env": {
        "PEC_DB_DSN": "postgresql://usuario_leitura:senha_segura@127.0.0.1:5432/esus_db",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

---

## Testes e Garantia de Qualidade

O projeto possui uma infraestrutura de testes automatizados com cobertura rigorosa:

```bash
# Executar suíte completa de testes
uv run pytest
```

### Validar as SQLs contra o seu banco

Os testes unitários não abrem banco. Para conferir que todas as consultas batem com o schema da sua versão do PEC, rode:

```bash
PEC_DB_DSN="postgresql://usuario_leitura:senha@127.0.0.1:5432/esus" uv run python scripts/validar_sql_explain.py
```

O script roda só `EXPLAIN`: o PostgreSQL confere tabelas, colunas e tipos, mas não executa a consulta nem devolve linhas. Rode de novo a cada atualização do PEC.

### Mecanismos de Proteção Testados
1. **Teste T1 (`test_no_pii_in_tool_outputs.py`)**:
   Injeta em memória linhas sintéticas carregadas propositalmente com CPFs, CNSs, telefones, endereços e nomes civis em todas as ferramentas registradas. O teste valida que nenhum dado sensível sobrevive à serialização final.
2. **Teste T2 (`test_projected_columns.py`)**:
   Audita a árvore sintática abstrata (AST) do código-fonte em tempo de compilação, assegurando que nenhuma consulta SQL faça referência a colunas de dados civis protegidos.
3. **Contratos e Limites (`test_tool_output_keys.py` e `test_limit_caps.py`)**:
   Assegura previsibilidade das chaves retornadas e conformidade dos tetos máximos de paginação.

---

## Limitações conhecidas

As tools de condições, medições do PEC, gestantes e busca ativa leem as tabelas do prontuário (`tb_problema`, `tl_medicao`, `tb_pre_natal`). Em municípios que registram o atendimento clínico em outro sistema e enviam só fichas CDS ao PEC, essas tabelas ficam vazias e as tools devolvem zero. As tools baseadas no Data Warehouse (`tb_fat_*`: vacinas, visitas, saúde bucal, atividades coletivas, PSE, procedimentos) funcionam nos dois cenários.

---

## Contribuindo

Regras de privacidade e checklist para novas tools em [CONTRIBUTING.md](CONTRIBUTING.md). Histórico de versões em [CHANGELOG.md](CHANGELOG.md).

---

## Licença

Distribuído sob a Licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
