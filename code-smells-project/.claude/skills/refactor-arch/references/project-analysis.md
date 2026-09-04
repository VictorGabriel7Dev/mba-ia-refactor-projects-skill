# Fase 1 - heurísticas de análise de projeto

Objetivo: descobrir **o que o projeto é** e **como ele está organizado de verdade**, sem
depender de convenção de nome de pasta.

## 1. Linguagem e gerenciador de pacotes

Procure o manifesto, nesta ordem. O primeiro que existir decide.

| Arquivo | Linguagem | Onde está a versão do framework |
|---|---|---|
| `package.json` | JavaScript / TypeScript | `dependencies`, e a versão exata em `package-lock.json` |
| `requirements.txt` | Python | a própria linha (`Flask==3.1.1`) |
| `pyproject.toml` | Python | `[project.dependencies]` ou `[tool.poetry.dependencies]` |
| `go.mod` | Go | `require` |
| `composer.json` | PHP | `require` |
| `Gemfile` | Ruby | `Gemfile.lock` |
| `pom.xml` / `build.gradle` | Java / Kotlin | `<dependencies>` / `dependencies` |

Sem manifesto, decida pela extensão dominante dos arquivos de código.

> ⚠️ **A versão do lock vale mais que a do manifesto.** `"express": "^4.18.2"` é uma faixa;
> o lock diz o que está instalado. Reporte o que o lock diz, e diga que veio do lock.

## 2. Framework

Não basta ver a dependência: confirme o uso.

| Sinal no código | Framework |
|---|---|
| `Flask(__name__)`, `@app.route`, `Blueprint(` | Flask |
| `express()`, `app.use(`, `app.listen(` | Express |
| `FastAPI()`, `@router.get` | FastAPI |
| `NestFactory.create`, `@Controller()` | NestJS |
| `Django`, `urls.py`, `settings.py` | Django |
| `Rails::Application` | Rails |

Dependência declarada e não usada não é o framework do projeto. Dependência usada e não
declarada é um achado (ver `implicit-dependency` no catálogo).

## 3. Banco de dados e tabelas

Duas fontes, nesta ordem:

1. **DDL literal**: `CREATE TABLE` em qualquer arquivo. Dá o nome e as colunas.
2. **Modelos de ORM**: `class X(db.Model)` com `__tablename__`, `sequelize.define`,
   `@Entity()`. O nome da tabela vem do `__tablename__`, e não do nome da classe.

Registre também **onde o banco vive**: arquivo em disco, `:memory:`, servidor externo.
`:memory:` significa que o estado morre com o processo, o que muda como validar na Fase 3.

## 4. Domínio

Saia das rotas e das tabelas, nunca do nome do repositório. Um repositório chamado
`ecommerce-api-legacy` pode ser, na verdade, um LMS com fluxo de checkout: as tabelas
(`courses`, `enrollments`, `payments`) contam a história certa, o nome não.

Uma linha, concreta: *"API de e-commerce (produtos, pedidos, usuários)"*.

## 5. Arquitetura REAL

Este é o passo que se erra com mais frequência. **Classifique pelo conteúdo, não pela árvore.**

Procedimento:

1. Liste os handlers de rota (`@app.route`, `@bp.route`, `app.get(`, `@Get()`).
2. Para **cada** handler, responda: ele faz consulta a banco? cálculo de regra de negócio?
   formatação de resposta? As três?
3. Some quantos handlers fazem as três coisas. Essa proporção é a arquitetura.

| Achado | Classificação |
|---|---|
| Todo o código em 1 a 4 arquivos, sem camadas | Monolítica sem separação |
| Uma classe concentrando banco, rotas e regra | God Class |
| Pastas `models/`, `routes/`, `services/` **mas** regra de negócio dentro dos handlers | **MVC aparente, sem camada de controller** |
| Models, Views/Routes e Controllers com responsabilidade separada de fato | MVC |

> ⚠️ **"MVC aparente" é o caso mais perigoso.** As pastas existem, os nomes estão certos, e
> uma auditoria que olhe só a estrutura declara o projeto saudável e devolve zero achado.
> O sinal objetivo é: **arquivo de rota com mais de ~150 linhas**, ou handler que abre
> consulta ao banco e faz agregação no mesmo corpo. Meça, não confie no nome.

## 6. Contagem de arquivos

`Source files` = arquivos de código-fonte da aplicação que você leu.

Não conta: `node_modules/`, `venv/`, `__pycache__/`, arquivos gerados, lockfiles, migrações
automáticas, `seed`/fixtures que não fazem parte do runtime, e os arquivos da própria skill.

Se você contar 4 e ler 3, o relatório inteiro perde credibilidade no primeiro item.
