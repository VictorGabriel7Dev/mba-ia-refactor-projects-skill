# Relatório de auditoria - Projeto 3

Saída da execução da skill `refactor-arch` em `task-manager-api/`. Mesma skill dos projetos
1 e 2, copiada sem alteração.

**Este é o projeto que testa se a skill audita de verdade.** Ele já tem `models/`, `routes/`,
`services/` e `utils/`. Uma auditoria que classifique arquitetura pela árvore de diretórios
declara este projeto saudável e devolve zero achado.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3
Framework:     Flask 3.0.0 + Flask-SQLAlchemy 3.1.1
Dependencies:  flask-cors 4.0.0, marshmallow 3.20.1, requests 2.31.0, python-dotenv 1.0.0
Domain:        API de gestão de tarefas (tarefas, usuários, categorias e relatórios)
Architecture:  **MVC APARENTE, sem camada de controller.** As pastas existem e os nomes
               estão certos, mas a regra de negócio mora dentro dos handlers de rota:
               task_routes.py tem 299 linhas, report_routes.py 223 e user_routes.py 211.
               `models/` são só declarações de tabela; `services/` tem um único serviço
               que nenhuma rota chama.
Source files:  11 files analyzed (~1.100 linhas)
DB tables:     tasks, users, categories
================================
```

> O sinal objetivo que a Fase 1 manda medir: **arquivo de rota acima de ~150 linhas**. Os três
> passam. E `marshmallow` está declarado no `requirements.txt` e não é importado em lugar
> nenhum: a validação que ele faria está escrita à mão dentro dos handlers.

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0 + SQLAlchemy
Files:   11 analyzed | ~1.100 lines of code
Date:    2026-09-04
```

## Summary

**CRITICAL: 3 | HIGH: 2 | MEDIUM: 4 | LOW: 3**

## Findings

### [CRITICAL] `hardcoded-credentials`
**File:** `services/notification_service.py:10` e `app.py:13`
**Description:** senha do servidor de e-mail (`self.email_password = 'senha123'`) como atributo
de classe, e `SECRET_KEY = 'super-secret-key-123'` na configuração da aplicação.
**Impact:** duas credenciais no repositório. Um anti-pattern, dois locais, conforme a regra 1
do catálogo.
**Recommendation:** playbook 2, com as credenciais **injetadas** no serviço.

### [CRITICAL] `sensitive-data-in-response`
**File:** `models/user.py:21`
**Description:** `User.to_dict()` inclui `'password': self.password`.
**Impact:** este método é usado por `GET /users/<id>` **e** pela resposta do `POST /login`.
Um campo a mais no serializador vaza em todas as rotas de uma vez. Confirmado na linha de
base: as chaves de `GET /users/1` incluem `password`.
**Recommendation:** playbook 5 (projeção pública explícita).

### [CRITICAL] `broken-crypto`
**File:** `models/user.py:29,32`
**Description:** `hashlib.md5(pwd.encode()).hexdigest()`, sem salt, para gravar e conferir
senha.
**Impact:** MD5 é quebrado para senha, e sem salt duas contas com a mesma senha têm o mesmo
digest: uma tabela arco-íris entrega o grupo inteiro de uma vez.
**Recommendation:** playbook 4 (scrypt com salt e comparação em tempo constante).

### [HIGH] `business-logic-in-route`
**File:** `routes/task_routes.py:11-63,240-299`, `routes/report_routes.py:12-101`,
`routes/user_routes.py:10-25,153-183`
**Description:** o achado central deste projeto. `summary_report` tem **90 linhas** de
agregação dentro do handler; `get_tasks` monta o dicionário campo a campo e busca usuário e
categoria de cada tarefa; `task_stats` faz cinco contagens e depois um laço em memória.
**Impact:** nada disso é testável sem subir HTTP, e a mesma regra aparece copiada. O cálculo de
`overdue` está escrito **seis vezes**, em quatro arquivos, cada cópia livre para divergir.
**Recommendation:** playbook 7 (extrair para controller) e mover a regra de `overdue` para o
modelo.

### [HIGH] `no-dependency-injection`
**File:** `services/notification_service.py:5-10,15`
**Description:** o construtor define host, porta, usuário e senha internamente, e `send_email`
instancia `smtplib.SMTP` direto.
**Impact:** não há como testar notificação sem servidor de e-mail real, nem apontar para outro
servidor sem editar código.
**Recommendation:** receber configuração e transporte por parâmetro.

### [MEDIUM] `n-plus-1-query`
**File:** `routes/report_routes.py:56,163`, `routes/task_routes.py:42,51`,
`routes/user_routes.py:21`
**Description:** quatro ocorrências. Consulta de tarefas **por usuário** dentro do laço de
usuários; contagem de tarefas **por categoria**; busca de usuário e de categoria **por tarefa**
na listagem; e `len(u.tasks)` por usuário, que dispara consulta pelo lazy loading.
**Impact:** `GET /tasks` com 200 tarefas dispara 401 consultas. `GET /reports/summary` cresce
com o número de usuários.
**Recommendation:** playbook 8 (`JOIN` com agregação).

### [MEDIUM] `deprecated-api`
**File:** `utils/helpers.py:38`, `models/user.py:14`, `models/task.py:15,16,52`,
`models/category.py:11`, `routes/report_routes.py:35,42,45,71`, `routes/user_routes.py:172`,
`routes/task_routes.py:31,72,215,285`, `seed.py:66,67,69,70,74`
**Description:** `datetime.utcnow()`, deprecada desde o Python 3.12, em **19 locais**.
**Impact:** devolve datetime **ingênuo**. No dia em que qualquer parte do sistema passar a usar
data com fuso, toda comparação com `due_date` levanta
`TypeError: can't compare offset-naive and offset-aware datetimes`. É defeito latente com data
para explodir, não questão de estilo.
**Recommendation:** playbook 10, **trocando todas as ocorrências de uma vez**. Ver a nota sobre
a armadilha na seção da Fase 3.

### [MEDIUM] `debug-mode-in-production`
**File:** `app.py:34` e `app.py:15`
**Description:** `app.run(debug=True, host='0.0.0.0')` e `CORS(app)` sem restrição de origem.
**Impact:** console interativo do Werkzeug acessível pela rede.
**Recommendation:** ambiente com default seguro.

### [MEDIUM] `missing-input-validation`
**File:** `routes/task_routes.py:113,182,261,264`
**Description:** `priority < 1 or priority > 5` sem checar tipo, e `int(priority)` /
`int(user_id)` na busca sem `try`.
**Impact:** `{"priority": "alta"}` levanta `TypeError` e vira 500; `?priority=abc` levanta
`ValueError` e vira 500. Erro de cliente respondido como erro de servidor.
**Recommendation:** validar tipo antes de comparar, devolvendo 400.

### [LOW] `inconsistent-error-handling`
**File:** `routes/task_routes.py:62,236`, `routes/report_routes.py:186,207,221`
**Description:** cinco blocos `except:` **nus**, que capturam qualquer exceção, inclusive
`KeyboardInterrupt`, e devolvem `'Erro interno'` sem registrar nada.
**Impact:** a causa real desaparece. Um erro de programação vira 500 silencioso e ninguém
descobre por que.
**Recommendation:** playbook 11 (handler central).

### [LOW] `magic-values-and-weak-typing`
**File:** `routes/task_routes.py:110,141,177,210`, `utils/helpers.py:75,103,114`,
`models/task.py:39`
**Description:** a lista de status válidos escrita **cinco vezes**; `type(tags) == list` em vez
de `isinstance`; `MIN_PASSWORD_LENGTH = 4`.
**Impact:** cinco cópias da mesma lista divergem no dia em que alguém acrescentar um status.
`type(x) == list` quebra com subclasse de `list`. E quatro caracteres não é política de senha.
**Recommendation:** playbook 12.

### [LOW] `dead-code` *(fora do catálogo)*
**File:** `utils/helpers.py:1-7,31-34,57`, `requirements.txt:4`
**Description:** `os`, `json`, `sys`, `math` e `hashlib` importados sem uso; `generate_id()` e
`process_task_data()` nunca chamados; `marshmallow` declarado e não usado.
**Impact:** sugere dependência e capacidade que não existem, e infla a superfície de
manutenção.
**Recommendation:** remover o que não é usado; manter o que for API pública, documentado.

```
================================
Total: 11 findings
================================

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
> y
```

## Cobertura contra a análise manual

Os 8 achados manuais foram reencontrados; a skill somou 3.

| Análise manual | Achado |
|---|---|
| 1. Senha de e-mail hardcoded | `hardcoded-credentials` |
| 2. `SECRET_KEY` hardcoded | idem, mesmo achado, segundo local |
| 3. Regra de negócio dentro das rotas | `business-logic-in-route` |
| 4. N+1 no relatório | `n-plus-1-query` |
| 5. `datetime.utcnow()` deprecada | `deprecated-api` |
| 6. `debug=True` com bind em `0.0.0.0` | `debug-mode-in-production` |
| 7. Política de senha de 4 caracteres | `magic-values-and-weak-typing` |
| 8. `type(x) == list` | idem, mesmo achado |

**Novos:** o `to_dict()` que devolve o hash da senha em toda rota que serializa usuário; o MD5
sem salt; e a ausência de injeção de dependência no serviço de notificação.

E a contagem da análise manual ficou curta em dois pontos: o `utcnow()` aparece em **19**
locais, não em 4, e o cálculo de `overdue` está copiado **seis** vezes.

---

## Fase 3 - refatoração

```
================================
PHASE 3: REFACTORING COMPLETE
================================
New Project Structure:
task-manager-api/
├── app.py                     (composition root: monta, injeta e conecta)
├── database.py
├── security.py                (scrypt com salt, comparação em tempo constante)
├── config/
│   ├── settings.py            (ambiente; nenhum segredo literal)
│   └── constants.py           (status, faixas, mínimos)
├── models/                    (declaração + regra do próprio dado)
│   ├── task.py                (`is_overdue()` mora aqui, uma vez só)
│   ├── user.py                (`to_dict` público, sem o hash de senha)
│   └── category.py
├── controllers/               (NOVO: a camada que faltava)
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── report_controller.py
│   └── category_controller.py
├── routes/                    (só mapeamento HTTP -> controller)
├── services/notification_service.py   (config e transporte injetados)
├── middlewares/error_handler.py
└── utils/
    ├── tempo.py               (NOVO: UTC sem a API deprecada)
    └── helpers.py

Validation
✓ Application boots without errors
✓ All endpoints respond correctly  (16/16 conferidos por execução)
✓ Zero anti-patterns remaining     (dos 11 achados, 11 tratados)
================================
```

### Prova de execução

```
✅ aplicação subiu e 16 endpoint(s) conferidos: 16 idênticos, 0 corrigidos de propósito
```

**Nenhum status mudou.** Ao contrário dos projetos 1 e 2, aqui não houve mudança deliberada de
contrato: os defeitos deste projeto eram de organização e de dado exposto, não de rota
perigosa.

### A armadilha do `utcnow()`, que quase quebrou a aplicação

A troca óbvia, `datetime.utcnow()` → `datetime.now(timezone.utc)`, **quebra este projeto**.

As colunas `db.DateTime` do SQLite guardam datetime **ingênuo**. Se os valores novos passarem a
ser **conscientes**, toda comparação com um valor lido do banco levanta
`TypeError: can't compare offset-naive and offset-aware datetimes`, e o campo `overdue`, que
compara `due_date` com agora, para de funcionar em quatro rotas.

A solução foi `utils/tempo.agora_utc()`, que devolve
`datetime.now(timezone.utc).replace(tzinfo=None)`: sai a chamada deprecada, entra a
recomendada, e o formato de armazenamento continua idêntico. É exatamente o aviso do playbook
10: **ou troca tudo, ou não troca nada; metade convertida é pior que nenhuma.**

Migrar as colunas para `DateTime(timezone=True)` é o passo seguinte, e está declarado como
pendência em vez de feito pela metade.

### O que foi resolvido, achado a achado

| Achado | Transformação aplicada |
|---|---|
| `hardcoded-credentials` | playbook 2: `config/settings.py`; o serviço de e-mail **recebe** as credenciais |
| `sensitive-data-in-response` | playbook 5: `to_dict()` público, sem `password`. `GET /users/1` e `POST /login` param de vazar o hash |
| `broken-crypto` | playbook 4: MD5 sem salt virou scrypt com salt e `hmac.compare_digest` |
| `business-logic-in-route` | playbook 7: 733 linhas de rota viraram **131**, e nasceu `controllers/` com 4 unidades. `overdue`, que estava copiado 6 vezes, virou `Task.is_overdue()` |
| `no-dependency-injection` | `NotificationService` recebe host, porta, usuário, senha e transporte |
| `n-plus-1-query` | playbook 8: `GET /tasks` em 1 consulta com JOIN; produtividade por usuário, contagem por categoria e `task_count` em consultas agregadas |
| `deprecated-api` | playbook 10: 19 ocorrências de `utcnow()` trocadas de uma vez, com a ressalva acima |
| `debug-mode-in-production` | `DEBUG` e `HOST` do ambiente; CORS com origem explícita |
| `missing-input-validation` | tipo checado antes da comparação; `int()` com tratamento, devolvendo 400 |
| `inconsistent-error-handling` | playbook 11: 5 `except:` nus viraram 1 handler central |
| `magic-values-and-weak-typing` | playbook 12: `config/constants.py`; `isinstance`; mínimo de senha de 4 para 8 |
| `dead-code` | imports e `requirements` sem uso removidos |

### Pendências declaradas

1. **As colunas de data continuam ingênuas.** `agora_utc()` normaliza, o que remove a API
   deprecada sem quebrar nada, mas a migração para `DateTime(timezone=True)` fica em aberto.
2. **O `seed.py` cria usuários com senha de 4 caracteres** (`'1234'`, `'abcd'`, `'pass'`),
   abaixo do novo mínimo de 8. Funciona porque o seed chama `set_password` direto, sem passar
   pelo controller. É fixture de desenvolvimento e ficou como estava de propósito, para não
   invalidar as credenciais que qualquer pessoa usa ao testar o projeto. Em produção o caminho
   é a rota, e a rota valida.
3. **`marshmallow` continua no `requirements.txt`.** A validação foi para os controllers, em
   Python puro; adotar marshmallow seria uma decisão de projeto, não uma correção de defeito.
