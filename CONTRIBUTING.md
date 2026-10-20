# Como contribuir

O servidor expõe dados clínicos em modo somente leitura. A regra que orienta tudo é a minimização: cada tool devolve o mínimo necessário para responder à pergunta clínica.

## Privacidade

Nunca exponha o nome completo de paciente em resultado de tool, exemplo, log, mensagem de erro, documentação ou teste. Se a SQL precisar ler `tb_cidadao.no_cidadao` para filtrar ou gerar iniciais, o valor não pode sair do processo.

Não podem aparecer na saída:

- nome completo do paciente;
- CPF, CNS, telefone, e-mail, endereço, nome da mãe, prontuário local, documento ou cartão;
- texto livre com identificação direta (os campos de texto livre passam por `mascarar_texto_livre`, que remove CPF, CNS, telefone e e-mail, mas não nomes);
- combinação de atributos que facilite reidentificar alguém sem necessidade para a tool.

Para pacientes, use `paciente_initials` no lugar do nome e `paciente_id` (`co_seq_cidadao`) só quando a navegação entre tools exigir. Datas vão em ISO. Todo campo exposto precisa de justificativa funcional.

## Checklist para criar ou alterar uma tool

1. Confira tabelas e colunas no schema da versão do PEC em uso e anote as hipóteses sobre regra de negócio.
2. Rode `scripts/validar_sql_explain.py` contra um banco de homologação, ou contra a produção com usuário somente leitura. O script só faz `EXPLAIN` e não lê linhas.
3. Não copie linhas, valores clínicos ou identificadores do banco para issues, PRs, testes ou documentação. Use dados sintéticos.
4. Se uma regra ainda não foi conferida com dados reais, diga isso na documentação da tool.
5. Revise se a SQL seleciona alguma coluna sensível sem necessidade e se o `TypedDict` tem algum campo de PII.
6. Atualize a documentação da tool (tabelas e colunas lidas, campos devolvidos, proteções aplicadas).
7. Acrescente teste de regressão: ausência de PII na saída e, com SQL dinâmica, ausência de coluna sensível na projeção.

## Regras de implementação

- Projete as colunas do `SELECT` explicitamente; nada de `SELECT *` sobre tabela.
- Nunca devolva `no_cidadao`. Para iniciais, converta no servidor com `to_initials` e descarte o valor bruto.
- Evite join com tabela de identificação direta quando o caso de uso não pede.
- Toda tool de lista tem limite padrão e teto (`safe_limit`), e o limite é o último parâmetro da consulta.
- Somente leitura: nada de `INSERT`, `UPDATE`, `DELETE`, `ALTER`, `CREATE` ou `DROP`.
- Ignore `tb_atend_prof` com `st_cancelado = 1` em tools de atendimento válido.
- Mantenha compatibilidade com PostgreSQL 9.6: dê tipo explícito a literais dentro de CTE com `UNION` (`'x'::text`).

## Testes

```bash
uv run pytest
```

- Toda tool com dado de paciente precisa de teste garantindo que a saída não traz `nome_paciente`, `no_cidadao` ou equivalente.
- Ao corrigir um vazamento, inclua o teste de regressão no mesmo commit.

## Na dúvida

Entre utilidade e privacidade, escolha privacidade. Se uma necessidade parecer exigir PII direta, redesenhe a tool para anonimizar ou reduzir o escopo.
