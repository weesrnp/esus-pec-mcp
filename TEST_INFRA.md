# E2E Test Infra: e-SUS PEC FastMCP

## Test Philosophy
- Opaque-box & AST static verification derived strictly from requirements and regulations (Portarias GM/MS 3.493/2024, SAPS 161/2024, LGPD Lei 13.709/2018).
- Zero tolerance for PII leaks (T1 test) and forbidden direct identifier columns (T2 AST audit).
- Strict pagination limit enforcement across all list tools.

## Feature Inventory & Test Mapping
| # | Feature | Source (Requirement) | Tier 1 (Feature) | Tier 2 (Boundary & Limits) | Tier 3 (Cross-Feature) | Tier 4 (Real-World) |
|---|---------|----------------------|:----------------:|:--------------------------:|:----------------------:|:--------------------:|
| 1 | Purge analytics.py & Zero VIOLACOES_CONHECIDAS | R5 | ✓ | ✓ | ✓ | ✓ |
| 2 | Refactored Existing Tools | R1 | ✓ | ✓ | ✓ | ✓ |
| 3 | Oral Health Appointments (`listar_atendimentos_odonto`) | R2 | ✓ | ✓ | ✓ | ✓ |
| 4 | Oral Health Procedures (`listar_procedimentos_odonto`) | R2 | ✓ | ✓ | ✓ | ✓ |
| 5 | Oral Health Conditions (`listar_problemas_odonto`) | R2 | ✓ | ✓ | ✓ | ✓ |
| 6 | eMulti Collective Activities (`listar_atividades_coletivas`) | R3 | ✓ | ✓ | ✓ | ✓ |
| 7 | eMulti Participant Privacy (`consultar_participacao_coletiva`) | R3 | ✓ | ✓ | ✓ | ✓ |
| 8 | eMulti Conductors / Shared Care (`listar_profissionais_atividade_coletiva`) | R3 | ✓ | ✓ | ✓ | ✓ |
| 9 | PSE School Actions Audit (`listar_acoes_pse`) | R4 | ✓ | ✓ | ✓ | ✓ |
| 10 | Security Harness (T1 PII & T2 AST) | R5 | ✓ | ✓ | ✓ | ✓ |

## Test Architecture
- **Runner**: `uv run --with pytest pytest` (and `uv run pytest` once pytest dependency is wired).
- **Security T1**: `tests/test_no_pii_in_tool_outputs.py` sweeps all 11 PII regexes and strict capital initials against mock injections.
- **Security T2**: `tests/test_projected_columns.py` verifies AST AST-level compliance, banning `COLUNAS_PROIBIDAS` and enforcing `VIOLACOES_CONHECIDAS = set()`.
- **Contracts**: `tests/test_tool_output_keys.py` checks strict sets of `chaves_permitidas`.
- **Limits**: `tests/test_limit_caps.py` checks that `safe_limit` is properly capped and bound as `params[-1]`.
- **Domain Unit Tests**:
  - `tests/test_tool_saude_bucal.py` (CBOs 2232xx/3224xx, exodontias B3, preventivos B4, TRA/ART B6).
  - `tests/test_tool_atividades_coletivas.py` (eMulti 28 CBOs, PTS M2 flag, zero participant PII).
  - `tests/test_tool_pse.py` (INEP school code, 14 thematic health actions).

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Oral Health B1-B6 Indicator Auditing for eSB funding | F3, F4, F5 | High |
| 2 | eMulti Indicator M1 & M2 Co-financing calculation | F6, F7, F8 | High |
| 3 | PSE Annual Municipal Agreement Verification | F9, F6 | Medium |
| 4 | Active search for vulnerable citizens without consultation | F2, F3, F7 | High |
| 5 | Full LGPD Adversarial Penetration Test across all tools | F1-F10 | High |
