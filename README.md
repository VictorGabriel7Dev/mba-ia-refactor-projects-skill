# Skill de Auditoria e Refatoração Arquitetural

Entrega do desafio da fase 295 do MBA em Engenharia de Software com IA (Full Cycle).

Uma Skill que analisa uma codebase, audita anti-patterns com severidade e refatora o projeto para
o padrão MVC, funcionando nos três projetos legados deste repositório, em duas stacks diferentes.

> **Estado:** análise manual concluída (requisito 1). A skill e a execução nos três projetos são
> os passos seguintes. O enunciado original está preservado em `docs/ENUNCIADO.md`.

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

_A ser preenchido: decisões de design, quais anti-patterns entraram no catálogo e por quê, como a
skill se mantém agnóstica de tecnologia, e os desafios encontrados._

## Resultados

_A ser preenchido: resumo dos três relatórios de auditoria, comparação antes/depois, checklist de
validação e evidência das aplicações rodando após a refatoração._

## Como Executar

_A ser preenchido: pré-requisitos, comando por projeto e como validar a refatoração._
