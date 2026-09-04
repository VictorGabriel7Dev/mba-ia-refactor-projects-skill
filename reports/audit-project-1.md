# Relatório de auditoria - Projeto 1

Saída da execução da skill `refactor-arch` em `code-smells-project/`.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3
Framework:     Flask 3.1.1 (versão exata em requirements.txt)
Dependencies:  flask-cors 5.0.1
Domain:        API de e-commerce (produtos, usuários, pedidos e relatório de vendas)
Architecture:  Monolítica sem camadas. Existem 4 arquivos e uma separação por NOME
               (app/controllers/models/database), mas não por responsabilidade:
               models.py concentra SQL, regra de negócio e formatação de 4 domínios,
               e app.py declara duas rotas administrativas no próprio entry point.
Source files:  4 files analyzed (~780 linhas)
DB tables:     produtos, usuarios, pedidos, itens_pedido
================================
```

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-09-04
```

## Summary

**CRITICAL: 6 | HIGH: 2 | MEDIUM: 3 | LOW: 3**

## Findings

### [CRITICAL] `sql-injection`
**File:** `models.py:110` (grave) · também em `models.py:28,68,92,140,155,174,188,192,220,224,280` e `models.py:291-297`
**Description:** as queries são montadas por concatenação de string. Em `login_usuario` o
`email` e a `senha` entram **crus** dentro das aspas do SQL:
`"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
Em `buscar_produtos` o termo de busca também é concatenado dentro de um `LIKE`.
**Impact:** confirmado por execução, não por leitura. `POST /login` com
`{"senha": "x' OR '1'='1"}` devolve **200 e o usuário autenticado**: uma aspa simples fecha a
string e o `OR` verdadeiro desliga a checagem de senha inteira. Os demais pontos interpolam um
id que passou por `str()`, o que reduz muito o alcance, mas é o mesmo defeito.
**Recommendation:** playbook 1 (query parametrizada), em todas as ocorrências.

### [CRITICAL] `arbitrary-code-execution`
**File:** `app.py:61-79`
**Description:** a rota `POST /admin/query` lê o campo `sql` do corpo e o entrega direto ao
`cursor.execute()`, sem autenticação nem lista de comandos permitidos.
**Impact:** o banco inteiro nas mãos de quem chamar a rota, incluindo `SELECT email, senha FROM
usuarios` e qualquer `DROP`. Não é um vazamento, é controle total.
**Recommendation:** playbook 3 (remoção). Não existe versão segura deste endpoint.

### [CRITICAL] `destructive-endpoint-without-auth`
**File:** `app.py:47-58`
**Description:** `POST /admin/reset-db` apaga as 4 tabelas sem verificar identidade.
**Impact:** qualquer requisição não autenticada zera a base de produção.
**Recommendation:** playbook 3 (remoção). Operação administrativa é tarefa de CLI autenticada.

### [CRITICAL] `hardcoded-credentials`
**File:** `app.py:7`
**Description:** `SECRET_KEY = "minha-chave-super-secreta-123"` literal na configuração.
**Impact:** a chave que assina sessão está no repositório; qualquer pessoa com acesso ao código
forja sessão.
**Recommendation:** playbook 2 (configuração por ambiente).

### [CRITICAL] `sensitive-data-in-response`
**File:** `controllers.py:289` e `models.py:83,99`
**Description:** duas exposições distintas. O `GET /health` devolve `"secret_key":
"minha-chave-super-secreta-123"` no corpo da resposta. E `get_todos_usuarios` e
`get_usuario_por_id` incluem o campo `senha` no dicionário, então `GET /usuarios` devolve a
senha de todos os usuários.
**Impact:** o vazamento deixa de exigir acesso ao repositório e passa a ser remoto e anônimo.
Confirmado na linha de base: as chaves da resposta de `/health` incluem `secret_key`.
**Recommendation:** playbook 5 (projeção explícita) e remoção do campo em `/health`.

### [CRITICAL] `broken-crypto`
**File:** `models.py:110,126-131` e `database.py:70-74`
**Description:** senha gravada em **texto plano** (`INSERT INTO usuarios ... VALUES ('admin123')`)
e conferida por comparação de igualdade dentro da própria query SQL.
**Impact:** vazamento do banco entrega todas as senhas em claro; e como a comparação é feita
pelo SQL, ela é o mesmo vetor da injeção do primeiro achado.
**Recommendation:** playbook 4 (função de derivação de senha com salt) somado ao playbook 1.

### [HIGH] `god-file`
**File:** `models.py:1-314`
**Description:** um único arquivo com acesso a dados, regra de negócio e formatação de resposta
para 4 domínios (produto, usuário, pedido, relatório). A regra de desconto por faixa de
faturamento (`models.py:256-262`) mora ao lado do SQL.
**Impact:** nada é testável em isolamento, e qualquer mudança em um domínio arrisca os outros.
**Recommendation:** playbook 6 (separar por camada) e playbook 7 (regra para controller).

### [HIGH] `global-mutable-state`
**File:** `database.py:4,9-11`
**Description:** `db_connection` é uma variável global de módulo, reatribuída na primeira
chamada, e a conexão é aberta com `check_same_thread=False`.
**Impact:** uma única conexão compartilhada por todas as requisições, sem controle de
concorrência. Sob carga, transações de requisições diferentes se misturam.
**Recommendation:** conexão por requisição, criada e fechada no ciclo de vida do pedido.

### [MEDIUM] `n-plus-1-query`
**File:** `models.py:187-199` e `models.py:219-231`
**Description:** `get_pedidos_usuario` e `get_todos_pedidos` iteram sobre os pedidos, abrem uma
consulta de itens por pedido e, dentro dessa, uma consulta de produto por item.
**Impact:** listar 50 pedidos com 3 itens cada dispara 1 + 50 + 150 consultas. O tempo de
resposta cresce com o volume de dados, não com o tamanho da página.
**Recommendation:** playbook 8 (consulta única com `JOIN`).

### [MEDIUM] `debug-mode-in-production`
**File:** `app.py:8,88` e `app.py:9`
**Description:** `DEBUG = True` na config e `app.run(host="0.0.0.0", debug=True)`. `CORS(app)`
sem restrição de origem.
**Impact:** o depurador do Werkzeug expõe um console interativo que executa Python no processo,
acessível de qualquer interface de rede. Vale por uma execução remota de código.
**Recommendation:** `debug` vindo do ambiente com default desligado; CORS com origem explícita.

### [MEDIUM] `missing-input-validation`
**File:** `controllers.py:118-121,43-46,87-90`
**Description:** `preco_min`/`preco_max` passam por `float()` sem `try`, e `preco`/`estoque` são
comparados com `< 0` sem checagem de tipo.
**Impact:** `?preco_min=abc` levanta `ValueError` e vira 500; um `preco` em string levanta
`TypeError` e também vira 500. Erro de cliente respondido como erro de servidor.
**Recommendation:** validar tipo e faixa antes de usar, devolvendo 400.

### [LOW] `inconsistent-error-handling`
**File:** `controllers.py:12,22,62,96,109,126,134,144,165,186,220,227,235,255,262,292`
**Description:** 16 blocos `except Exception as e` repetidos, todos devolvendo
`jsonify({"erro": str(e)}), 500`.
**Impact:** a mensagem interna da exceção vai para o cliente, e não há um formato único de erro.
**Recommendation:** playbook 11 (handler central de erro).

### [LOW] `magic-values-and-weak-typing`
**File:** `controllers.py:52,242` e `models.py:257-262`
**Description:** a lista de categorias válidas e a de status válidos estão escritas dentro dos
handlers, e as faixas de desconto (10000/5000/1000 e 0.1/0.05/0.02) são números soltos no meio
da função de relatório.
**Impact:** mudar uma regra exige caçar o literal, e nada impede que duas cópias divirjam.
**Recommendation:** playbook 12 (constantes nomeadas).

### [LOW] `dead-parameter`
**File:** `models.py:1-2`
**Description:** `import sqlite3` em `models.py` sem uso; `database.py` importa `os` sem uso.
**Impact:** ruído que sugere dependência que não existe.
**Recommendation:** remover.

```
================================
Total: 14 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
```

## Cobertura contra a análise manual

O enunciado exige que a Fase 2 encontre **no mínimo 5** dos problemas documentados
manualmente no README. Os 7 da análise manual deste projeto foram todos reencontrados:

| Análise manual | Achado correspondente |
|---|---|
| 1. SQL Injection no login | `sql-injection` (CRITICAL) |
| 2. Senha em texto plano comparada na query | `broken-crypto` (CRITICAL) |
| 3. `SECRET_KEY` hardcoded e devolvida por endpoint | `hardcoded-credentials` + `sensitive-data-in-response` |
| 4. God file de 314 linhas | `god-file` (HIGH) |
| 5. `debug=True` com bind em `0.0.0.0` | `debug-mode-in-production` (MEDIUM) |
| 6. CORS liberado | idem, mesmo achado |
| 7. Injeção por interpolação de inteiro nos CRUDs | `sql-injection`, gradação explicada |

**Três achados que a análise manual não tinha:** a rota `/admin/query` de execução arbitrária
de SQL, a rota `/admin/reset-db` sem autenticação, e o vazamento da **senha de todos os
usuários** em `GET /usuarios`. Os dois primeiros estão no `app.py`, que a leitura manual tratou
como arquivo de rotas e passou rápido; o terceiro está no `to_dict` implícito do model. É a
diferença entre ler procurando o que se espera achar e cruzar contra um catálogo.

---

## Fase 3 - refatoração

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
code-smells-project/
├── requirements.txt
└── src/
    ├── app.py                     (composition root: monta e conecta, sem regra)
    ├── database.py                (conexão POR REQUISIÇÃO, via `g` + teardown)
    ├── security.py                (scrypt com salt + comparação em tempo constante)
    ├── config/
    │   ├── settings.py            (tudo do ambiente; nenhum segredo literal)
    │   └── constants.py           (categorias, status, faixas de desconto)
    ├── models/
    │   ├── produto_model.py
    │   ├── usuario_model.py       (projeção PUBLICO: a senha não sai daqui)
    │   └── pedido_model.py        (listagem em 2 consultas, no lugar de 1+N+N*M)
    ├── controllers/
    │   ├── produto_controller.py
    │   ├── usuario_controller.py
    │   └── pedido_controller.py
    ├── views/routes.py            (só mapeamento HTTP -> controller)
    └── middlewares/error_handler.py

Validation
✓ Application boots without errors
✓ All endpoints respond correctly  (17/17 conferidos por execução)
✓ Zero anti-patterns remaining     (dos 14 achados, 14 tratados)
================================
```

### Prova de execução

`python tools/smoke_test.py --projeto code-smells-project` compara a resposta de cada
endpoint com a linha de base gravada **antes** de qualquer mudança
(`reports/_baseline-code-smells-project.json`):

```
✅ aplicação subiu e 17 endpoint(s) conferidos: 16 idênticos, 1 corrigidos de propósito

Mudanças deliberadas (correção, não regressão):
  login_injecao: 200 -> 401   SQL Injection corrigida: a aspa no campo senha
                              deixa de autenticar (era 200)
```

**A linha de base é a prova de que o defeito era real.** Antes da refatoração,
`POST /login` com `{"senha": "x' OR '1'='1"}` respondia **200 com o usuário autenticado**.
Depois, responde 401. Nenhum outro endpoint mudou de status.

### O que foi resolvido, achado a achado

| Achado | Transformação aplicada |
|---|---|
| `sql-injection` (12 locais) | playbook 1: toda query passou a placeholder, inclusive o filtro dinâmico da busca |
| `arbitrary-code-execution` | playbook 3: `/admin/query` **removida** |
| `destructive-endpoint-without-auth` | playbook 3: `/admin/reset-db` **removida** |
| `hardcoded-credentials` | playbook 2: `SECRET_KEY` vem de `os.environ` |
| `sensitive-data-in-response` | playbook 5: `/health` não devolve mais `secret_key`, `db_path` nem `debug`; `usuario_model` projeta campos públicos e a senha só sai em `credencial_por_email` |
| `broken-crypto` | playbook 4: scrypt com salt por usuário, verificação em tempo constante, e a comparação saiu de dentro do SQL |
| `god-file` | playbook 6: 314 linhas viraram 3 models, 3 controllers, 1 view e 1 middleware |
| `global-mutable-state` | conexão por requisição em `g`, fechada no `teardown_appcontext` |
| `n-plus-1-query` | playbook 8: listagem de pedidos em 2 consultas; relatório de vendas em 1 agregada, no lugar de 5 |
| `debug-mode-in-production` | `DEBUG` e `HOST` do ambiente, defaults seguros (`False`, `127.0.0.1`); CORS com origem explícita |
| `missing-input-validation` | tipo e faixa validados no controller, devolvendo 400 em vez de 500 |
| `inconsistent-error-handling` | playbook 11: 16 blocos `except` viraram 1 handler central |
| `magic-values-and-weak-typing` | playbook 12: `config/constants.py` |
| `dead-parameter` | imports sem uso removidos |

### Mudanças deliberadas de contrato

Três, todas declaradas:

1. **`POST /admin/query` removida.** Executava SQL arbitrário sem autenticação.
2. **`POST /admin/reset-db` removida.** Apagava as 4 tabelas sem autenticação.
3. **`GET /health` deixou de devolver `secret_key`, `db_path`, `debug` e `ambiente`.**
   O status e o restante do corpo continuam iguais.

O comando de inicialização passou de `python app.py` para `python src/app.py`, como pede a
estrutura do enunciado. Os caminhos HTTP não mudaram.

### Pendência declarada

**As senhas de exemplo mudam de formato no banco.** O seed agora grava
`scrypt$<salt>$<hash>`; um banco `loja.db` criado pela versão antiga tem senha em texto plano
e o login vai falhar contra ele. Apague o `loja.db` antigo, ou migre. Isso é consequência
inevitável de corrigir `broken-crypto`, e está aqui para ninguém descobrir por acidente.
