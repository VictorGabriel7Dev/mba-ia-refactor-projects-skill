# Template do relatório de auditoria (Fase 2)

Formato fixo. O relatório é lido por gente que vai decidir se autoriza a Fase 3, então ele
precisa caber numa tela até a primeira decisão: cabeçalho, sumário por severidade, e só
depois o detalhe.

Salve em `reports/audit-<identificador>.md`. Neste repositório: `audit-project-1.md`
(`code-smells-project`), `audit-project-2.md` (`ecommerce-api-legacy`) e
`audit-project-3.md` (`task-manager-api`).

---

```markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <nome da pasta>
Stack:   <linguagem + framework>
Files:   <N> analyzed | ~<M> lines of code
Date:    <YYYY-MM-DD>

## Summary

CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [CRITICAL] <nome do anti-pattern do catálogo>
**File:** `<caminho>:<linha>`  (ou `<caminho>:<início>-<fim>`)
**Description:** o que está no código, em uma ou duas frases, citando o trecho.
**Impact:** o que acontece na prática se isso continuar. Consequência, não adjetivo.
**Recommendation:** a transformação a aplicar, nomeando o padrão do playbook.

### [HIGH] ...
### [MEDIUM] ...
### [LOW] ...

================================
Total: <n> findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```

---

## Regras de preenchimento

**Ordem.** CRITICAL → HIGH → MEDIUM → LOW. Dentro da mesma severidade, o de maior alcance
primeiro (afeta a aplicação inteira antes do que afeta uma rota).

**`File`.** Linha exata. Intervalo só quando o achado é o arquivo inteiro (god file). Se o
mesmo padrão aparece em vários lugares, liste todos na mesma linha:
`utils/helpers.py:38`, `routes/report_routes.py:35,42`.

**`Description`.** Diga o que **está lá**, com o identificador real. "Concatena `email` e
`senha` crus dentro das aspas do SQL" é descrição; "problemas de segurança" não é.

**`Impact`.** Consequência observável. Compare:

- ❌ "Isso é muito perigoso e vai causar problemas."
- ✅ "Uma aspa simples no campo de senha fecha a string e desvia a autenticação inteira."

**`Recommendation`.** Aponte o padrão do playbook pelo nome, para a Fase 3 saber o que
aplicar sem reinterpretar o achado.

**Números batem.** A soma do sumário tem de ser igual ao `Total`, e o `Total` igual ao número
de blocos de finding. Relatório cujo cabeçalho discorda do corpo perde a autoridade toda.

**A pergunta final é obrigatória e literal.** Ela é o único ponto em que o humano autoriza
escrita em disco. Nenhum arquivo é modificado antes da resposta.
