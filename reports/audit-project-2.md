# Relatório de auditoria - Projeto 2

Saída da execução da skill `refactor-arch` em `ecommerce-api-legacy/`. **A skill é a mesma,
copiada sem uma linha de diferença** do projeto 1: `diff -r` entre as três cópias é vazio.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js 20)
Framework:     Express 4.18.2 (versão do package-lock.json)
Dependencies:  sqlite3 5.1.6
Domain:        LMS com fluxo de checkout (cursos, matrículas, pagamentos e auditoria).
               O nome da pasta diz "ecommerce", as TABELAS dizem outra coisa.
Architecture:  God Class. `AppManager` acumula conexão de banco, criação de esquema,
               registro de rotas, regra de checkout, montagem de relatório e exclusão
               de usuário. `app.js` tem 14 linhas e só instancia o AppManager.
Source files:  3 files analyzed (~180 linhas)
DB tables:     users, courses, enrollments, payments, audit_logs (SQLite em :memory:)
================================
```

> A observação sobre o domínio veio da regra da Fase 1 de não tirar domínio do nome do
> repositório. As tabelas são `courses`, `enrollments` e `payments`: é um LMS, não um
> e-commerce de produtos.

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js + Express 4.18.2
Files:   3 analyzed | ~180 lines of code
Date:    2026-09-04
```

## Summary

**CRITICAL: 3 | HIGH: 4 | MEDIUM: 3 | LOW: 2**

## Findings

### [CRITICAL] `hardcoded-credentials`
**File:** `src/utils.js:2-4`
**Description:** senha de banco (`dbPass: "senha_super_secreta_prod_123"`) e **chave live** do
gateway de pagamento (`paymentGatewayKey: "pk_live_1234567890abcdef"`) literais no objeto de
configuração. O prefixo `pk_live_` é o sinal forte do catálogo: é chave de produção, não de
teste.
**Impact:** quem clonar o repositório tem a credencial de pagamento de produção.
**Recommendation:** playbook 2. E **rotacionar a chave no provedor**: tirar do código não
desfaz a exposição de quem já leu.

### [CRITICAL] `broken-crypto`
**File:** `src/utils.js:17-23`
**Description:** `badCrypto()` concatena, 10.000 vezes, os 2 primeiros caracteres do base64 do
**mesmo** valor, e devolve `substring(0, 10)`.
**Impact:** o laço não adiciona entropia nenhuma, porque repete a codificação de um valor
constante; o `substring(0,10)` reduz a saída a 10 caracteres de um alfabeto pequeno. O espaço
de saída fica pequeno o bastante para colisão trivial, e a transformação é reversível.
**Recommendation:** playbook 4 (scrypt com salt e comparação em tempo constante).

### [CRITICAL] `sensitive-data-in-response`
**File:** `src/AppManager.js:45`
**Description:** `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)`
grava o **número completo do cartão** e a chave live do gateway no log, a cada checkout.
**Impact:** log de aplicação costuma ir para arquivo, agregador e ferramenta de terceiro. Dado
de cartão em claro nesse caminho é incidente por si só, independente de invasão.
**Recommendation:** não registrar o dado. Se precisar de rastro, os 4 últimos dígitos.

### [HIGH] `god-class`
**File:** `src/AppManager.js:4-141`
**Description:** uma classe com conexão de banco (linha 7), DDL e seed (10-23), registro de
rotas (25-138), regra de checkout (28-78), relatório financeiro (80-129) e exclusão de usuário
(131-137).
**Impact:** nada é testável sem subir o Express inteiro, e qualquer mudança em uma rota mexe no
arquivo que também cria o esquema.
**Recommendation:** playbook 6, cortando por camada.

### [HIGH] `global-mutable-state`
**File:** `src/utils.js:9-10`
**Description:** `globalCache` e `totalRevenue` são variáveis de módulo compartilhadas entre
requisições. `logAndCache` escreve no cache global a cada checkout.
**Impact:** estado vaza entre requisições e o cache cresce sem limite nem expiração.
**Observação medida:** `totalRevenue` é exportado por valor (`module.exports = { totalRevenue }`),
então quem importa recebe uma **cópia congelada em 0**. O acumulador nunca funcionou. É um
segundo defeito escondido dentro do primeiro.
**Recommendation:** estado por requisição, ou um store explícito com ciclo de vida.

### [HIGH] `no-dependency-injection`
**File:** `src/AppManager.js:5-8`
**Description:** o construtor instancia o próprio banco (`new sqlite3.Database(':memory:')`).
**Impact:** não há como testar a regra de checkout sem um banco real, nem apontar para outro
banco sem editar código.
**Recommendation:** receber a conexão pronta por parâmetro.

### [HIGH] `data-integrity-on-delete` *(fora do catálogo)*
**File:** `src/AppManager.js:131-137`
**Description:** `DELETE /api/users/:id` apaga o usuário e deixa matrículas e pagamentos
órfãos. O próprio código admite: a resposta é *"Usuário deletado, mas as matrículas e
pagamentos ficaram sujos no banco."*
**Impact:** o relatório financeiro passa a listar `student: 'Unknown'` e continua somando a
receita de matrículas sem dono. O dado fica errado em silêncio.
**Recommendation:** transação apagando as dependências, ou exclusão lógica. Registrado como
achado fora do catálogo, conforme a regra 4 de `anti-patterns.md`.

### [MEDIUM] `n-plus-1-query`
**File:** `src/AppManager.js:83-128`
**Description:** o relatório busca todos os cursos, depois as matrículas **por curso**, depois
usuário e pagamento **por matrícula**.
**Impact:** com 20 cursos e 50 matrículas cada, são 1 + 20 + 2000 consultas para montar uma
página.
**Recommendation:** playbook 8 (uma consulta com `LEFT JOIN`).

### [MEDIUM] `manual-async-control-flow`
**File:** `src/AppManager.js:86-122`
**Description:** dois contadores (`coursesPending`, `enrPending`) decrementados dentro de
callbacks aninhados em 4 níveis para decidir quando responder.
**Impact:** os callbacks internos **ignoram o parâmetro `err`** (linhas 104 e 106). Um erro em
qualquer consulta deixa o contador travado e a requisição pendura até o timeout do cliente, sem
nada no log.
**Recommendation:** playbook 9 (`async/await` com `Promise.all`).

### [MEDIUM] `missing-input-validation`
**File:** `src/AppManager.js:29-35,46,68`
**Description:** `p` (senha) não é validado e cai num default literal
(`badCrypto(p || "123456")`); `cc` não tem formato conferido, e a aprovação do pagamento é
`cc.startsWith("4")`; nenhum campo tem tipo verificado.
**Impact:** usuário criado com senha padrão conhecida. E `cc` não string derruba a rota com
`TypeError`, virando 500.
**Recommendation:** validar presença, tipo e formato antes de usar; nunca cair em senha
default.

### [LOW] `inconsistent-error-handling`
**File:** `src/AppManager.js:35,38,41,51,55,84`
**Description:** erros devolvidos como string solta: `"Bad Request"`, `"Erro DB"`,
`"Erro Matrícula"`, `"Erro Pagamento"`. Sem código, sem formato, sem log.
**Impact:** o cliente não distingue os casos programaticamente e o erro real não fica em lugar
nenhum.
**Recommendation:** playbook 11 (handler central).

### [LOW] `magic-values-and-weak-typing`
**File:** `src/utils.js:5`, `src/AppManager.js:46,68`
**Description:** porta `3000` fixa na configuração, prefixo `"4"` de cartão aprovado e senha
default `"123456"` como literais no meio da regra.
**Recommendation:** playbook 12 (constantes nomeadas e configuração por ambiente).

```
================================
Total: 12 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
```

## Cobertura contra a análise manual

Os 7 achados manuais deste projeto foram reencontrados, e a skill somou 5.

| Análise manual | Achado |
|---|---|
| 1. Credenciais de produção hardcoded | `hardcoded-credentials` |
| 2. `badCrypto()` reversível e colidível | `broken-crypto` |
| 3. God class `AppManager` | `god-class` |
| 4. Estado global mutável | `global-mutable-state` |
| 5. N+1 em cascata no relatório | `n-plus-1-query` |
| 6. Controle assíncrono por contador manual | `manual-async-control-flow` |
| 7. Erros como string solta | `inconsistent-error-handling` |

**Novos:** cartão e chave live gravados em log; ausência de injeção de dependência; integridade
referencial quebrada no `DELETE`; falta de validação com senha default; e valores mágicos.

**A checagem que NÃO virou achado, e é o ponto do exercício:** este projeto **não tem SQL
Injection**. As seis queries usam placeholder `?` com array de parâmetros
(`AppManager.js:37,40,50,54,57,92,104,106,133`). A regra do catálogo é explícita: presença de
SQLite não é sinal, só concatenação é. Uma skill que marcasse "usa banco, logo injeção" daria
falso positivo aqui, no projeto que **acerta** justamente no acesso a dados enquanto erra feio
em criptografia.

---

## Fase 3 - refatoração

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
ecommerce-api-legacy/
├── package.json
└── src/
    ├── app.js                       (composition root: cria as deps e injeta)
    ├── database.js                  (conexão INJETADA + helpers com Promise)
    ├── security.js                  (scrypt, timingSafeEqual, máscara de cartão)
    ├── config/settings.js           (ambiente + constantes de domínio)
    ├── models/
    │   ├── user_model.js            (exclusão em cascata, em transação)
    │   └── course_model.js          (relatório em 1 consulta com LEFT JOIN)
    ├── controllers/
    │   ├── checkout_controller.js
    │   ├── report_controller.js
    │   └── user_controller.js
    ├── views/routes.js
    └── middlewares/error_handler.js

Validation
✓ Application boots without errors
✓ All endpoints respond correctly  (6/6 conferidos por execução)
✓ Zero anti-patterns remaining     (dos 12 achados, 12 tratados)
================================
```

### Prova de execução

```
endpoint                    antes    depois
  checkout_ok                 200       200
  checkout_negado             400       400
  checkout_faltando           400       400
  checkout_curso_404          404       404
  relatorio                   200       200
  deletar_usuario             200       200

✅ aplicação subiu e 6 endpoint(s) conferidos: 6 idênticos
```

### A regressão que o harness pegou, e que a leitura não pegaria

A primeira versão do controller validava a senha **antes** de buscar o curso. Resultado:
`checkout` com curso inexistente passou a responder **400 em vez de 404**, porque a validação
nova disparava primeiro. O código estava "mais correto" e o contrato, quebrado.

```
  checkout_curso_404          404       400   <-- REGRESSÃO
```

Corrigido movendo a exigência de senha para dentro do ramo que **cria** usuário, que é
exatamente onde ela era usada antes. Fica registrado porque é o argumento a favor do harness:
uma revisão de código teria aprovado a versão errada sem hesitar.

### O que foi resolvido, achado a achado

| Achado | Transformação aplicada |
|---|---|
| `hardcoded-credentials` | playbook 2: `config/settings.js` lê do ambiente. ⚠️ A `pk_live_` **não** virou default: precisa ser rotacionada no provedor |
| `broken-crypto` | playbook 4: `badCrypto` substituído por scrypt com salt e `timingSafeEqual` |
| `sensitive-data-in-response` | o log deixou de imprimir o cartão e a chave; agora sai `**** **** **** 1111` |
| `god-class` | playbook 6: `AppManager` (141 linhas, 6 responsabilidades) virou 2 models, 3 controllers, 1 view, 1 middleware e 1 módulo de banco |
| `global-mutable-state` | `globalCache` e `totalRevenue` eliminados |
| `no-dependency-injection` | a conexão é criada no composition root e **injetada** nos models |
| `data-integrity-on-delete` | `deletarEmCascata` apaga pagamentos, matrículas e usuário numa transação |
| `n-plus-1-query` | playbook 8: relatório em **1** consulta com `LEFT JOIN`, agrupada em memória |
| `manual-async-control-flow` | playbook 9: contadores viraram `async/await`; o erro que era engolido agora sobe para o handler |
| `missing-input-validation` | presença, tipo e tamanho validados; a senha default `"123456"` foi eliminada |
| `inconsistent-error-handling` | playbook 11: handler central, formato único |
| `magic-values-and-weak-typing` | playbook 12: porta, prefixo de cartão e mínimo de senha viraram constantes |

### Mudanças deliberadas de contrato

**Os corpos de erro deixaram de ser string solta e passaram a ser JSON `{"erro": ...}`.** Os
caminhos, métodos e **códigos de status** continuam idênticos, mas o corpo mudou de
`"Erro DB"` para `{"erro": "..."}`. Isso é exigência do próprio checklist do enunciado
("Error handling centralizado"), e não dava para atender mantendo a string solta.

**`DELETE /api/users/:id` mudou de mensagem.** Era *"Usuário deletado, mas as matrículas e
pagamentos ficaram sujos no banco"*. Agora os dados dependentes vão junto, e a mensagem diz
isso. Status continua 200.

### Pendência declarada

**A chave `pk_live_1234567890abcdef` continua exposta.** Ela saiu do código, mas está no
histórico do repositório e já foi lida por qualquer pessoa com acesso. **Só a rotação no
provedor resolve.** Está aqui, e não num comentário no código, porque é ação fora do
repositório e não pode depender de alguém abrir o arquivo certo.
