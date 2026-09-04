# Skill de Auditoria e Refatoração Arquitetural

Entrega do desafio da fase 295 do MBA em Engenharia de Software com IA (Full Cycle).

Uma Skill que analisa uma codebase, audita anti-patterns com severidade e refatora o projeto para
o padrão MVC, funcionando nos três projetos legados deste repositório, em duas stacks diferentes.

> **Estado:** completo. Análise manual, skill, execução nos três projetos, refatoração e
> relatórios. O enunciado original está preservado em `docs/ENUNCIADO.md`.
>
> | | code-smells-project | ecommerce-api-legacy | task-manager-api |
> |---|---|---|---|
> | Stack detectada | Python + Flask 3.1.1 | Node + Express 4.18.2 | Python + Flask 3.0.0 |
> | Achados | **14** | **12** | **11** |
> | CRITICAL ou HIGH | 8 | 7 | 5 |
> | Endpoints validados | 17/17 | 6/6 | 16/16 |
> | Aplicação sobe | ✅ | ✅ | ✅ |
>
> **37 achados** no total, e a aplicação dos três continua respondendo, verificado por
> execução (`tools/smoke_test.py`), não por leitura.

## Análise Manual

Leitura dos três projetos antes de escrever qualquer linha da skill. O objetivo aqui não é achar
tudo, e sim entender que classes de problema a skill precisa detectar - e confirmar que elas
aparecem de formas diferentes em cada stack, que é o que torna a skill agnóstica não trivial.

Severidades conforme a escala do enunciado: CRITICAL (falha de arquitetura ou segurança, dado
exposto, separação de responsabilidades completamente violada), HIGH (violação forte de MVC ou
SOLID que trava manutenção e teste), MEDIUM (padronização, duplicação, performance moderada),
LOW (legibilidade, nomenclatura, magic numbers).

---

### Projeto 1 - `code-smells-project` (Python + Flask, API de E-commerce)

4 arquivos, ~780 linhas. Monolito sem camadas: `models.py` concentra SQL e regra de negócio de
quatro domínios.

| # | Severidade | Problema | Local |
|---|---|---|---|
| 1 | **CRITICAL** | SQL Injection no login, por concatenação de string com credenciais do usuário | `models.py:110` |
| 2 | **CRITICAL** | Senha comparada em texto plano dentro da própria query, sem hash | `models.py:110` |
| 3 | **CRITICAL** | `SECRET_KEY` hardcoded, e o mesmo valor devolvido por um endpoint da API | `app.py:7`, `controllers.py:289` |
| 4 | **HIGH** | God file: 314 linhas misturando acesso a dados, regra de negócio e formatação de 4 domínios | `models.py:1-314` |
| 5 | **MEDIUM** | `debug=True` com bind em `0.0.0.0` - console interativo do Werkzeug exposto na rede | `app.py:88` |
| 6 | **MEDIUM** | CORS liberado sem restrição de origem | `app.py:9` |
| 7 | **LOW** | SQL Injection também nos CRUDs, mas por interpolação de inteiro - impacto menor que o do login | `models.py:28,68,92,140,155` |

**Por que o item 1 é o mais grave:** os demais pontos de injeção interpolam um id que passa por
`str()`, o que limita muito o que dá para injetar. O do login concatena **email e senha crus**
dentro das aspas do SQL, então basta um apóstrofo no campo de senha para desviar a autenticação
inteira. É a diferença entre um bug de arquitetura e uma porta destrancada.

**Por que o item 3 pesa duas vezes:** ter a chave no código já é ruim; devolvê-la em um endpoint
transforma um vazamento de repositório em um vazamento remoto, sem acesso ao código.

---

### Projeto 2 - `ecommerce-api-legacy` (Node.js + Express, LMS com checkout)

3 arquivos, ~180 linhas. Pequeno em tamanho e o mais grave em segurança.

| # | Severidade | Problema | Local |
|---|---|---|---|
| 1 | **CRITICAL** | Credenciais de **produção** hardcoded: senha do banco e chave live do gateway de pagamento (`pk_live_...`) | `utils.js:2-4` |
| 2 | **CRITICAL** | `badCrypto()` não é hash: concatena base64 do texto puro em laço e trunca em 10 caracteres. É reversível e colide com facilidade | `utils.js:17-23` |
| 3 | **HIGH** | God class: `AppManager` acumula conexão de banco, registro de rotas, checkout, relatório e exclusão de usuário | `AppManager.js:4-141` |
| 4 | **HIGH** | Estado global mutável compartilhado entre requisições (`globalCache`, `totalRevenue`) | `utils.js:9-10` |
| 5 | **MEDIUM** | N+1 em cascata no relatório: por curso, busca matrículas; por matrícula, busca usuário e pagamento | `AppManager.js:92-108` |
| 6 | **MEDIUM** | Controle de fluxo assíncrono por contador manual (`coursesPending`, `enrPending`), sem Promise | `AppManager.js:87-98` |
| 7 | **LOW** | Erros devolvidos como string solta, sem código nem formato (`"Erro DB"`, `"Bad Request"`) | `AppManager.js:35,41,51,55` |

**Achado que corrige uma suposição minha:** eu esperava SQL Injection aqui também, por analogia com
o projeto 1. **Não há.** Todas as queries usam placeholders `?` com array de parâmetros
(`AppManager.js:37,40,92,104,106,133`). O projeto erra feio em criptografia e em arquitetura, e
acerta no acesso a dados. Isso importa para a skill: ela não pode marcar "usa SQLite" como sinal de
injeção, precisa olhar a forma da query.

**Sobre o item 2:** o nome da função entrega a intenção do exercício, mas o problema real é
específico. Um laço de 10.000 iterações concatenando base64 **do mesmo valor** não adiciona
entropia nenhuma; o `substring(0,10)` final joga fora quase tudo. O espaço de saída fica pequeno o
bastante para colisão trivial.

---

### Projeto 3 - `task-manager-api` (Python + Flask, API de Task Manager)

11 arquivos com `models/`, `routes/`, `services/` e `utils/`. **Parcialmente organizado** - e é
justamente o caso mais difícil para a skill, porque a estrutura de pastas sugere MVC sem entregar
a separação.

| # | Severidade | Problema | Local |
|---|---|---|---|
| 1 | **CRITICAL** | Senha de e-mail hardcoded no serviço de notificação | `services/notification_service.py:10` |
| 2 | **HIGH** | `SECRET_KEY` hardcoded na aplicação | `app.py:13` |
| 3 | **HIGH** | Regra de negócio dentro das rotas: `task_routes.py` com 299 linhas e `report_routes.py` com 223 fazem consulta, cálculo e formatação no próprio handler. Não há camada de controller | `routes/task_routes.py`, `routes/report_routes.py` |
| 4 | **MEDIUM** | N+1: consulta de tarefas dentro do laço de usuários no relatório | `routes/report_routes.py:56` |
| 5 | **MEDIUM** | API deprecada: `datetime.utcnow()`, removida do caminho recomendado desde Python 3.12, devolve objeto ingênuo de fuso | `utils/helpers.py:38`, `routes/report_routes.py:35,42`, `routes/user_routes.py:172`, `models/category.py:11` |
| 6 | **MEDIUM** | `debug=True` com bind em `0.0.0.0` | `app.py:34` |
| 7 | **LOW** | Política de senha frouxa: mínimo de 4 caracteres | `utils/helpers.py:114` |
| 8 | **LOW** | `type(x) == list` em vez de `isinstance`, que quebra com subclasses | `utils/helpers.py:103` |

**Por que este projeto é o teste real da skill:** ele já tem `models/`, `routes/` e `services/`.
Uma skill que audite pela árvore de diretórios vai declarar este projeto saudável e não achar nada.
Só encontra o item 3 quem olhar o **conteúdo** dos handlers e medir onde a regra de negócio mora.
É a diferença entre detectar MVC pela pasta e detectar pela responsabilidade.

**Sobre o item 5:** é o único achado de API deprecada dos três projetos, e o enunciado exige que o
catálogo cubra essa categoria. Ele aparece em 4 arquivos, o que o torna bom caso de teste para
detecção por padrão em vez de por ocorrência isolada.

---

### O que a análise implica para a skill

| Observação | Consequência no desenho |
|---|---|
| Injeção de SQL aparece por concatenação no projeto 1 e **não** aparece no projeto 2, que usa placeholders | A detecção precisa avaliar a **forma da query**, não a presença de banco |
| Credenciais hardcoded aparecem nos 3, em 3 formas (config Flask, objeto JS, atributo de classe) | Detecção por padrão de nome + literal, não por arquivo conhecido |
| O projeto 3 tem pastas MVC sem separação real | A Fase 1 não pode inferir arquitetura só da árvore de diretórios |
| God class aparece como arquivo de 314 linhas (py) e como classe de 141 (js) | O limiar precisa ser relativo à linguagem, não um número absoluto |
| N+1 aparece nos projetos 2 e 3, com sintaxes completamente diferentes | O sinal é estrutural: chamada de I/O dentro de laço |
| Erros sem padrão no projeto 2, política de senha frouxa no 3 | LOW e MEDIUM precisam de regras próprias, senão o relatório só tem CRITICAL |

## Construção da Skill

A skill vive em `.claude/skills/refactor-arch/`, **dentro dos três projetos**, e as três
cópias são idênticas byte a byte (`diff -r` vazio). Isso não é detalhe de organização: é a
prova do agnosticismo. Se ela precisasse de um ajuste por projeto, não seria agnóstica.

```
refactor-arch/
├── SKILL.md                          as 3 fases e as regras invioláveis de cada uma
└── references/
    ├── project-analysis.md           heurísticas de detecção de stack e arquitetura
    ├── anti-patterns.md              17 anti-patterns com sinal e severidade
    ├── report-template.md            formato do relatório da Fase 2
    ├── mvc-guidelines.md             a arquitetura alvo e a direção das dependências
    └── refactoring-playbook.md       12 transformações com código antes/depois
```

Mínimos do enunciado e o que foi entregue:

| Exigência | Mínimo | Entregue |
|---|---|---|
| Anti-patterns no catálogo | 8 | **17** |
| Severidades cobertas | 4 | 4 (6 CRITICAL, 4 HIGH, 5 MEDIUM, 2 LOW) |
| Detecção de APIs deprecated | obrigatória | 7 casos, cada um com o substituto |
| Transformações no playbook | 8 | **12**, todas com antes/depois |
| Fase 2 pausa e pede confirmação | obrigatória | sim, com a pergunta literal |
| Fase 3 valida boot + endpoints | obrigatória | sim, por execução real |

### Por que o SKILL.md é curto e as referências são longas

O `SKILL.md` é o **prompt**: diz o que fazer, em que ordem, e o que nunca pode ser quebrado.
O conhecimento de domínio fica nas referências, que são lidas **no início da fase que precisa
delas**. Carregar as cinco de uma vez enche o contexto com detalhe de refatoração enquanto o
agente ainda está tentando descobrir qual é o framework.

### Os anti-patterns que entraram, e por quê

O catálogo não saiu de uma lista genérica de code smells. Cada entrada existe porque **apareceu
nestes três projetos**, e a redação do sinal de detecção veio de um caso concreto:

| Anti-pattern | O caso que o originou |
|---|---|
| `sql-injection` | login do projeto 1 concatenando email e senha crus |
| `hardcoded-credentials` | `pk_live_` no projeto 2, `SECRET_KEY` no 1 e no 3, senha de SMTP no 3 |
| `arbitrary-code-execution` | `/admin/query` do projeto 1, que executa o SQL do corpo |
| `destructive-endpoint-without-auth` | `/admin/reset-db` do projeto 1 |
| `broken-crypto` | `badCrypto()` no 2, MD5 sem salt no 3, texto plano no 1 |
| `sensitive-data-in-response` | `to_dict()` com a senha no 3, `secret_key` no `/health` do 1 |
| `god-class` / `god-file` | `models.py` com 314 linhas, `AppManager` com 141 |
| `business-logic-in-route` | as rotas de 299, 223 e 211 linhas do projeto 3 |
| `global-mutable-state` | `globalCache`/`totalRevenue` no 2, conexão global no 1 |
| `no-dependency-injection` | banco no construtor do `AppManager`, SMTP no serviço do 3 |
| `n-plus-1-query` | relatório do 2 (1+N+N*M) e quatro pontos no 3 |
| `deprecated-api` | 19 usos de `datetime.utcnow()` no projeto 3 |
| `manual-async-control-flow` | os contadores `coursesPending`/`enrPending` do projeto 2 |
| `missing-input-validation` | `float()` sem `try` no 1, senha default `"123456"` no 2 |
| `debug-mode-in-production` | `debug=True` com `0.0.0.0` no 1 e no 3 |
| `inconsistent-error-handling` | 16 `except` iguais no 1, strings soltas no 2, `except:` nu no 3 |
| `magic-values-and-weak-typing` | lista de status escrita 5 vezes no projeto 3 |

### Como a skill se mantém agnóstica

Três decisões de desenho, todas nascidas de um erro que a análise manual corrigiu:

**1. O sinal é a forma do código, nunca a tecnologia.** A regra de injeção diz explicitamente
que *"presença de SQLite não é sinal; concatenação de entrada do usuário é"*. Isso importa
porque o `ecommerce-api-legacy` **usa banco e não tem injeção**: as queries são parametrizadas.
Uma skill que marcasse "usa banco, logo injeção" daria falso positivo justamente no projeto que
acerta no acesso a dados enquanto erra feio em criptografia. Foi a suposição por analogia que a
análise manual desmentiu.

**2. Limiar relativo, nunca absoluto.** God class aparece como arquivo Python de 314 linhas e
como classe JavaScript de 141. Se o catálogo dissesse "acima de 300 linhas", perderia o caso
JS inteiro. O que se conta é **responsabilidade cruzando camadas**; o tamanho é pista.

**3. A Fase 1 não pode inferir arquitetura pela árvore de diretórios.** O `task-manager-api`
tem `models/`, `routes/` e `services/` e mesmo assim não tem camada de controller. O
procedimento é abrir os handlers e medir onde a regra mora; o sinal objetivo é arquivo de rota
acima de ~150 linhas.

O mesmo vale para N+1, que é descrito como padrão estrutural (I/O dentro de laço sobre
resultado de I/O) e por isso foi encontrado tanto em `for` de Python quanto em callbacks
aninhados de JavaScript.

### Desafios encontrados

**O catálogo puxa a severidade para cima sozinho.** A primeira versão classificava quase tudo
como CRITICAL, e um relatório em que todo item é crítico não ajuda a priorizar nada. A solução
foi fixar a severidade **no anti-pattern**, não no caso: o que varia por ocorrência é a
justificativa. Está escrito no topo do catálogo como regra.

**Distinguir correção de regressão.** Consertar a SQL Injection do projeto 1 **muda** a resposta
de um endpoint: `POST /login` com aspa no campo senha deixa de devolver 200. Sem declarar isso,
a validação acusaria quebra de contrato exatamente onde o trabalho deu certo. O harness ganhou
um campo `mudanca_esperada` por projeto para separar as duas coisas.

**A troca ingênua de API deprecada quebra a aplicação.** No projeto 3, trocar
`datetime.utcnow()` por `datetime.now(timezone.utc)` faz toda comparação com data do banco
levantar `TypeError`, porque as colunas do SQLite guardam datetime ingênuo. O playbook ganhou o
aviso explícito: **ou troca tudo, ou não troca nada**. Detalhes em `reports/audit-project-3.md`.

**Validar de verdade pega o que revisão de código aprova.** No projeto 2, mover a validação de
senha para antes da busca do curso fez o `404` de curso inexistente virar `400`. O código
estava mais correto e o contrato, quebrado. Só o harness pegou.

## Resultados

### Resumo dos três relatórios

| | Projeto 1 | Projeto 2 | Projeto 3 |
|---|---|---|---|
| CRITICAL | 6 | 3 | 3 |
| HIGH | 2 | 4 | 2 |
| MEDIUM | 3 | 3 | 4 |
| LOW | 3 | 2 | 2 |
| **Total** | **14** | **12** | **11** |
| Achados da análise manual reencontrados | 7/7 | 7/7 | 8/8 |
| Achados novos, que a leitura manual não tinha | 3 | 5 | 3 |

Relatórios completos em `reports/audit-project-1.md`, `-2` e `-3`.

**Os oito achados que a skill viu e a leitura manual não:**

- `POST /admin/query` executando SQL arbitrário do corpo, sem autenticação (projeto 1)
- `POST /admin/reset-db` apagando as 4 tabelas, sem autenticação (projeto 1)
- `GET /usuarios` devolvendo a **senha de todos os usuários** (projeto 1)
- número do cartão e chave live do gateway gravados em log a cada checkout (projeto 2)
- `totalRevenue` exportado por valor: o acumulador **nunca funcionou** (projeto 2)
- callbacks do relatório ignorando `err`, deixando a requisição pendurada (projeto 2)
- `DELETE /api/users/:id` deixando matrículas e pagamentos órfãos (projeto 2)
- `to_dict()` do usuário devolvendo o **hash da senha** em toda rota que serializa (projeto 3)

### Antes e depois

| | Antes | Depois |
|---|---|---|
| **Projeto 1** | 4 arquivos, 780 linhas, sem camadas | `config/ models/ controllers/ views/ middlewares/`, entry point que só monta |
| | SQL por concatenação em 12 pontos | 100% parametrizado |
| | senha em texto plano, conferida no SQL | scrypt com salt, verificada em Python |
| | listagem de pedidos: 1+N+N*M consultas | 2 consultas |
| | relatório de vendas: 5 consultas | 1 agregada |
| | 16 blocos `except` idênticos | 1 handler central |
| **Projeto 2** | `AppManager` com 6 responsabilidades | 2 models, 3 controllers, 1 view, 1 middleware |
| | relatório: 1+N+N*M consultas, 4 níveis de callback | 1 consulta com `LEFT JOIN`, `async/await` |
| | `badCrypto()` reversível e colidível | scrypt com `timingSafeEqual` |
| | `DELETE` deixava órfãos | exclusão em cascata, em transação |
| **Projeto 3** | rotas com 733 linhas somadas | **131 linhas**, e nasceu `controllers/` |
| | `overdue` copiado 6 vezes | `Task.is_overdue()`, uma vez |
| | 4 pontos de N+1 | consultas agregadas |
| | `to_dict()` vazando o hash da senha | projeção pública explícita |
| | MD5 sem salt | scrypt com salt |
| | 19 usos de `datetime.utcnow()` | `utils/tempo.agora_utc()` |

### Checklist de validação do enunciado

**Fase 1 - Análise**

| Item | P1 | P2 | P3 |
|---|---|---|---|
| Linguagem detectada corretamente | ✅ | ✅ | ✅ |
| Framework detectado corretamente | ✅ | ✅ | ✅ |
| Domínio descrito corretamente | ✅ | ✅ (LMS, não e-commerce) | ✅ |
| Número de arquivos condiz com a realidade | ✅ 4 | ✅ 3 | ✅ 11 |

**Fase 2 - Auditoria**

| Item | P1 | P2 | P3 |
|---|---|---|---|
| Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Ordenados por severidade | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 14 | ✅ 12 | ✅ 11 |
| Detecção de APIs deprecated incluída | não aplicável | não aplicável | ✅ 19 locais |
| Pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |

**Fase 3 - Refatoração**

| Item | P1 | P2 | P3 |
|---|---|---|---|
| Estrutura segue MVC | ✅ | ✅ | ✅ |
| Configuração extraída, sem hardcoded | ✅ | ✅ | ✅ |
| Models abstraem os dados | ✅ | ✅ | ✅ |
| Views/Routes só roteiam | ✅ | ✅ | ✅ |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ | ✅ | ✅ |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ 17/17 | ✅ 6/6 | ✅ 16/16 |

**Critérios de aceite (os quatro obrigatórios, nos 3 projetos)**

| Critério | P1 | P2 | P3 |
|---|---|---|---|
| Fase 1 detecta stack | ✅ | ✅ | ✅ |
| Fase 2 encontra ≥ 5 findings | ✅ 14 | ✅ 12 | ✅ 11 |
| Fase 2 tem ao menos 1 CRITICAL ou HIGH | ✅ 8 | ✅ 7 | ✅ 5 |
| Fase 3 aplicação funciona após refatoração | ✅ | ✅ | ✅ |

### Log das aplicações rodando após a refatoração

```
$ python tools/smoke_test.py --projeto code-smells-project
endpoint                    antes    depois
  index                       200       200
  health                      200       200
  produtos_listar             200       200
  produto_404                 404       404
  login_ok                    200       200
  login_errado                401       401
  login_injecao               200       401   <-- mudou de propósito
  pedido_criar                201       201
  relatorio_vendas            200       200
  [...]
✅ aplicação subiu e 17 endpoint(s) conferidos: 16 idênticos, 1 corrigidos de propósito

$ python tools/smoke_test.py --projeto ecommerce-api-legacy
✅ aplicação subiu e 6 endpoint(s) conferidos: 6 idênticos, 0 corrigidos de propósito

$ python tools/smoke_test.py --projeto task-manager-api
✅ aplicação subiu e 16 endpoint(s) conferidos: 16 idênticos, 0 corrigidos de propósito
```

A linha `login_injecao: 200 -> 401` é a evidência mais direta deste trabalho: **antes** da
refatoração, `POST /login` com `{"senha": "x' OR '1'='1"}` respondia 200 e autenticava. A
vulnerabilidade não era teórica, e a correção também não.

### Mudanças deliberadas de contrato

Cinco, todas declaradas nos relatórios, nenhuma acidental:

1. `POST /admin/query` **removida** (projeto 1) - executava SQL arbitrário.
2. `POST /admin/reset-db` **removida** (projeto 1) - apagava as tabelas sem autenticação.
3. `GET /health` deixou de devolver `secret_key`, `db_path` e `debug` (projeto 1).
4. Corpos de erro passaram de string solta para JSON `{"erro": ...}` (projeto 2), que é o que
   o item "Error handling centralizado" do enunciado exige.
5. `to_dict()` do usuário parou de devolver o hash da senha (projeto 3), o que muda o corpo de
   `GET /users/<id>` e do `POST /login`.

## Como Executar

### Pré-requisitos

- Python 3.10+ e Node.js 18+
- Claude Code (a skill usa o formato `.claude/skills/`)

### Executar a skill

```bash
cd code-smells-project    && claude "/refactor-arch"
cd ../ecommerce-api-legacy && claude "/refactor-arch"
cd ../task-manager-api     && claude "/refactor-arch"
```

A skill roda as três fases em sequência e **para na Fase 2**, esperando um `y` antes de tocar
em qualquer arquivo. O relatório já fica salvo em `reports/` mesmo se você responder `n`.

### Rodar cada projeto

```bash
# Projeto 1 - Python/Flask, porta 5000
cd code-smells-project
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python src/app.py

# Projeto 2 - Node/Express, porta 3000
cd ecommerce-api-legacy && npm install && npm start

# Projeto 3 - Python/Flask, porta 5000
cd task-manager-api
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python seed.py && python app.py
```

Configuração por ambiente, com defaults de desenvolvimento em todos:
`SECRET_KEY`, `DEBUG`, `HOST`, `PORT`, `CORS_ORIGENS`, `DATABASE_URL`,
`EMAIL_USER`/`EMAIL_PASSWORD` (projeto 3), `PAYMENT_GATEWAY_KEY`/`DB_PASS` (projeto 2).

### Validar que a refatoração funciona

```bash
python tools/smoke_test.py --projeto code-smells-project
python tools/smoke_test.py --projeto ecommerce-api-legacy
python tools/smoke_test.py --projeto task-manager-api
```

O harness sobe o servidor de verdade, chama cada endpoint e **compara com a linha de base
gravada antes da refatoração** (`reports/_baseline-*.json`). Ele sai com código 1 se algum
endpoint regredir, e distingue regressão de correção deliberada.

Para regravar uma linha de base (só faz sentido a partir do código original):

```bash
python tools/smoke_test.py --projeto <nome> --salvar reports/_baseline-<nome>.json
```

> ⚠️ O projeto 1 precisa de um venv em `code-smells-project/.venv-check` e o projeto 3 em
> `task-manager-api/.venv-check`, que é o interpretador que o harness invoca. Ambos estão no
> `.gitignore`.
