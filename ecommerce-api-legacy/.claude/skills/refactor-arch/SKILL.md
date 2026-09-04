---
name: refactor-arch
description: Audita uma codebase e a refatora para o padrão MVC. Detecta stack e arquitetura, cruza o código contra um catálogo de anti-patterns com severidade, emite um relatório com arquivo e linha exatos, pede confirmação e só então reestrutura, validando que a aplicação continua de pé. Agnóstica de linguagem e framework. Use quando o pedido for auditar arquitetura, achar code smells, ou migrar um projeto legado para MVC.
---

# refactor-arch

Três fases sequenciais. **A Fase 3 nunca começa sem um "sim" explícito do humano.**

O conhecimento de domínio está nos arquivos de referência. Leia cada um no momento em que
a fase correspondente começa, não antes: carregar tudo de uma vez enche o contexto com
detalhe que só importa depois.

| Fase | O que faz | Referência a ler |
|---|---|---|
| 1. Análise | detecta stack, mapeia arquitetura real, imprime resumo | `references/project-analysis.md` |
| 2. Auditoria | cruza código contra o catálogo, emite relatório, **pede confirmação** | `references/anti-patterns.md` e `references/report-template.md` |
| 3. Refatoração | reestrutura para MVC e valida | `references/mvc-guidelines.md` e `references/refactoring-playbook.md` |

---

## Fase 1 - Análise

Leia `references/project-analysis.md` e siga as heurísticas de lá.

Produza exatamente este bloco:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão, se declarada>
Framework:     <framework + versão da trava de dependências>
Dependencies:  <as relevantes para arquitetura>
Domain:        <o que a aplicação faz, em uma linha, tirado das rotas e das tabelas>
Architecture:  <como o código está organizado HOJE, e não como as pastas sugerem>
Source files:  <N> files analyzed
DB tables:     <tabelas encontradas>
================================
```

**Regras que não podem ser quebradas nesta fase:**

- **Nunca infira arquitetura pela árvore de diretórios.** Uma pasta `models/` não prova que
  existe camada de modelo. Abra os handlers de rota e veja onde a regra de negócio mora.
  Um projeto com `models/`, `routes/` e `services/` pode não ter camada nenhuma de
  controller, e é justamente esse o caso mais fácil de auditar errado.
- **`Source files` conta arquivos de código-fonte da aplicação**, não dependências, não
  arquivos gerados, não migrações. Diga o número que você realmente leu.
- **`DB tables` sai do DDL ou dos modelos**, não de um palpite pelo nome do domínio.

## Fase 2 - Auditoria

Leia `references/anti-patterns.md` (o catálogo) e `references/report-template.md` (o formato).

1. Percorra **todo** arquivo de código-fonte contado na Fase 1.
2. Para cada anti-pattern do catálogo, procure os sinais de detecção descritos.
3. Registre cada achado com **arquivo e linha exatos**. Intervalo (`models.py:1-314`) só
   quando o problema é o arquivo inteiro; caso contrário, a linha específica.
4. Ordene por severidade: CRITICAL → HIGH → MEDIUM → LOW.
5. Emita o relatório no formato do template e **salve em `reports/audit-<identificador>.md`**.
   Neste repositório os identificadores são `project-1`, `project-2` e `project-3`, na
   ordem em que o enunciado lista os projetos.

**Regras que não podem ser quebradas nesta fase:**

- **Um achado sem arquivo e linha não entra no relatório.** "O projeto tem acoplamento
  alto" não é acionável e não é finding.
- **Não reporte anti-pattern que você não confirmou lendo a linha.** Presença de SQLite não
  é sinal de SQL Injection: só concatenação de entrada do usuário na query é. Um projeto
  pode errar feio em criptografia e acertar no acesso a dados.
- **Se um anti-pattern do catálogo não aparecer, ele simplesmente não vai ao relatório.**
  Não invente ocorrência para encher a lista, e não force severidade para cima.
- **Ao final, PARE e pergunte**, literalmente:
  `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`
  Não modifique nenhum arquivo antes da resposta. Qualquer coisa diferente de um sim
  explícito encerra a execução aqui, com o relatório já salvo.

## Fase 3 - Refatoração

Só depois do "sim". Leia `references/mvc-guidelines.md` (o alvo) e
`references/refactoring-playbook.md` (as transformações).

1. **Registre o comportamento atual antes de mexer.** Liste método, caminho e forma da
   resposta de cada endpoint. Esse inventário é o critério de aceite do final.
2. Crie a estrutura MVC descrita em `mvc-guidelines.md`.
3. Aplique as transformações do playbook, **uma por vez**, começando pelas CRITICAL.
4. Valide, e só então declare pronto.

**Regras que não podem ser quebradas nesta fase:**

- **Contrato de API é intocável.** Mesmos caminhos, mesmos métodos, mesmo formato de
  resposta, mesmos códigos de status. Refatoração que muda a resposta não é refatoração.
- **Segredo sai do código para variável de ambiente, com o mesmo valor como default de
  desenvolvimento** quando ele já estava público no repositório. Trocar o valor quebra a
  aplicação de quem clona; deixá-lo no código deixa o problema.
- **Endpoint que só existe para facilitar o legado inseguro (executar SQL arbitrário,
  resetar o banco sem autenticação, devolver a `SECRET_KEY`) é removido, não movido.**
  Registre a remoção no relatório: isso muda a superfície da API de propósito, e é a única
  exceção à regra do contrato intocável.
- **Validar é executar.** Suba a aplicação e chame os endpoints. "O código parece certo"
  não é validação. Se não subir, conserte antes de reportar.

Ao final, produza:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
<árvore resultante>

Validation
✓ Application boots without errors
✓ All endpoints respond correctly  (<N>/<N> conferidos)
✓ Zero anti-patterns remaining     (ou: <lista do que ficou e por quê>)
================================
```

Se algum anti-pattern sobreviver de propósito, **diga qual e por quê**. Um checklist com
tudo marcado e uma pendência escondida é pior que a pendência.
