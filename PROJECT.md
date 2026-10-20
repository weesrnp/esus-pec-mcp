# Project: e-SUS PEC FastMCP Refactor, Expansion & LGPD Hardening

## Architecture
- **FastMCP Server**: `src/pec_mcp/server.py` exposing clinical tools via `STANDALONE_TOOLS` tuple with read-only connection lifespan context.
- **Database Layer**: `src/pec_mcp/db.py` executing `query_all` and `query_one` with `psycopg2.extras.RealDictCursor`. Read-only session enforced (`readonly=True, autocommit=True`).
- **Data Models**: `src/pec_mcp/models.py` defining strict TypedDict schemas for all JSON outputs.
- **Clinical Tools Layer**: `src/pec_mcp/tools/` containing specialized modular tools with local `query_all`/`query_one` imports (enabling test harness mocking), safe pagination caps (`params[-1] = safe_limit`), and LGPD anonymization (`to_initials`, `compute_age_display`).
- **Test Harness**: `tests/` featuring:
  - T1: Runtime PII injection & regex sanitization (`test_no_pii_in_tool_outputs.py`).
  - T2: Static AST & lexical direct identifier audit (`test_projected_columns.py`).
  - Contracts & Limits: `test_tool_output_keys.py` and `test_limit_caps.py` driven by `casos_tools.py`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Purge analytics.py & Clear VIOLACOES_CONHECIDAS | Complete removal of vulnerable analytics module and zero-quarantine T2 AST audit | M1 | Survey / R5 |
| 2 | Refactor & Decouple Core Tools | Clean, decoupled rewrite of paciente, condicoes, atendimentos, medicoes, prescricoes, vacinas, procedimentos, sem_consulta preserving exact JSON keys | M2 | Survey / R1 |
| 3 | Oral Health: listar_atendimentos_odonto | Individual dental appointments query based on tb_fat_atendimento_odonto with CBO, consultation type, and conduct filters | M3 | Survey / R2 |
| 4 | Oral Health: listar_procedimentos_odonto | Chairside dental procedures query based on tb_fat_atend_odonto_proced for B3 (exodontias), B4 (preventives), and B6 (TRA/ART) | M3 | Survey / R2 |
| 5 | Oral Health: listar_problemas_odonto | Oral conditions/diagnostics query based on tb_fat_atend_odonto_problemas (CID-10/CIAP-2) | M3 | Survey / R2 |
| 6 | eMulti: listar_atividades_coletivas | Collective actions & team meetings tracking based on tb_fat_atividade_coletiva and tb_fat_atvdd_coletiva_int (PTS M2 filter) | M4 | Survey / R3 |
| 7 | eMulti: consultar_participacao_coletiva | Anonymized participant metrics based on tb_fat_atvdd_coletiva_part with strict LGPD masking (zero CPF/CNS projection) | M4 | Survey / R3 |
| 8 | eMulti: listar_profissionais_atividade_coletiva | Conducting healthcare professionals tracking based on tb_fat_atvdd_coletiva_propart for shared care auditing (M2) | M4 | Survey / R3 |
| 9 | PSE: listar_acoes_pse | School health program audit based on tb_fat_atividade_coletiva + tb_fat_atvdd_coletiva_ext joined with tb_dim_inep | M5 | Survey / R4 |
| 10 | E2E Security & Test Suite Hardening | 100% pytest pass with T1 (zero PII in all tools), T2 (zero forbidden columns), key contracts, and limit caps | M6 | Survey / Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: Purge analytics.py & LGPD Baseline | Remove analytics.py, clear VIOLACOES_CONHECIDAS in test_projected_columns.py, ensure clean T2 pass | none | DONE (analytics.py removed, VIOLACOES_CONHECIDAS cleared, pytest dev dep added) |
| 2 | M2: Refactor & Decouple Existing Tools | Idiomatic rewrite of paciente, condicoes, atendimentos, medicoes, prescricoes, vacinas, procedimentos, sem_consulta | M1 | DONE (All core tools refactored, decoupled, 311 tests passing) |
| 3 | M3: Oral Health Module (eSB / B1-B6) | saude_bucal.py (3 tools), models.py, server.py, casos_tools.py, test_tool_saude_bucal.py | M2 | DONE (3 tools implemented, registered, 361 tests passing) |
| 4 | M4: Collective Activities & eMulti (M1-M2) | atividades_coletivas.py (3 tools), models.py, server.py, casos_tools.py, test_tool_atividades_coletivas.py | M2 | DONE (3 tools implemented, registered, 422 tests passing) |
| 5 | M5: School Health Program (PSE) | pse.py (1 tool), models.py, server.py, casos_tools.py, test_tool_pse.py | M4 | DONE (1 tool implemented, registered, 422 tests passing) |
| 6 | M6: E2E Verification & Test Hardening | 100% pytest suite execution, T1/T2 verification across all 24 registered tools, limit caps, key contracts | M3, M4, M5 | DONE (422 passed, 14 skipped, 0 failures) |

## Interface Contracts
### Common Tool Signature & Context
All tools follow FastMCP signature:
```python
@server.tool()
def tool_name(ctx: Context, [args...], limite: int = 50) -> List[ResultType]:
    conn = get_db_conn(ctx)
    safe_limit = max(1, min(int(limite), TETO))
    # query_all(conn, sql, tuple(params + [safe_limit]))
```

### Prohibited Identifiers Invariant (LGPD)
- Prohibited strings: `nu_cpf`, `nu_cns`, `no_mae`, `nu_telefone`, `nu_celular`, `no_logradouro`, `nu_numero_logradouro`, `no_bairro`, `ds_email`, `nu_cep`.
- All patient names wrapped with `to_initials(name)`.
- All patient birthdates wrapped with `compute_age_display(dt)`.

### Limit Parameter Invariant
- The clamped `safe_limit` MUST be the final parameter passed in `params` to `query_all`: `params[-1] == safe_limit`.

## Code Layout
```
src/pec_mcp/
├── db.py                      # Database connection and query execution
├── models.py                  # TypedDict schemas for tool outputs
├── server.py                  # FastMCP instance and STANDALONE_TOOLS registry
└── tools/
    ├── __init__.py            # Context resolution and serialization helpers
    ├── paciente.py            # Patient search and identification (refactored)
    ├── condicoes.py           # Chronic/clinical conditions (refactored)
    ├── atendimentos.py        # SOAP clinical notes (refactored)
    ├── medicoes.py            # Anthropometry, BP, Blood glucose (refactored)
    ├── prescricoes.py         # Drug prescriptions (refactored)
    ├── vacinas.py             # Immunization DW records (refactored)
    ├── procedimentos.py       # Clinical procedures (refactored)
    ├── sem_consulta.py        # Active search for missing consultations (refactored)
    ├── saude_bucal.py         # NEW: Oral health appointments, procedures, problems (B1-B6)
    ├── atividades_coletivas.py # NEW: Collective actions, participants, conductors (M1-M2)
    └── pse.py                 # NEW: School Health Program (INEP) actions
tests/
    ├── conftest.py            # Global fixtures
    ├── casos_tools.py         # Test matrix and mock generator
    ├── test_no_pii_in_tool_outputs.py # T1 runtime PII audit
    ├── test_projected_columns.py     # T2 AST static projection audit
    ├── test_limit_caps.py     # Pagination limit caps verification
    ├── test_tool_output_keys.py # JSON output keys contract verification
    ├── test_tool_saude_bucal.py       # NEW: Unit tests for Oral Health
    ├── test_tool_atividades_coletivas.py # NEW: Unit tests for eMulti
    └── test_tool_pse.py               # NEW: Unit tests for PSE
```
