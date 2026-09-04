# Catálogo de anti-patterns

17 anti-patterns, cada um com **sinal de detecção acionável** e severidade fixa. Sinal
acionável quer dizer que dá para procurar no código: "query montada por concatenação de
entrada do usuário" serve; "código mal escrito" não.

Escala (a do enunciado):

- **CRITICAL** - falha grave de arquitetura ou segurança: expõe dado sensível, permite
  execução arbitrária, ou viola completamente a separação de responsabilidades.
- **HIGH** - violação forte de MVC ou SOLID que trava manutenção e teste.
- **MEDIUM** - padronização, duplicação, performance moderada, validação ausente.
- **LOW** - legibilidade, nomenclatura, magic numbers.

> ⚠️ **Severidade é do anti-pattern, não do seu gosto.** O que varia por caso é a
> justificativa, não a classe. Subir tudo para CRITICAL destrói a utilidade do relatório.

---

## CRITICAL

### `sql-injection`
**Sinal:** query montada por concatenação ou interpolação de valor vindo do usuário:
`"... WHERE x = '" + valor + "'"`, f-string com `{valor}` dentro de SQL, template literal
com `${valor}`.
**Não é sinal:** usar SQLite, ORM, ou ter `SELECT` no código. Placeholder (`?`, `%s`,
`:nome`) com array de parâmetros é o jeito **certo** e não deve ser reportado.
**Gradação:** concatenar **texto livre** (email, senha, termo de busca) é o caso grave, porque
uma aspa simples reescreve a query. Interpolar um inteiro que passou por conversão numérica é
o mesmo defeito com alcance muito menor: reporte, mas explique a diferença.

### `hardcoded-credentials`
**Sinal:** literal atribuído a nome que contenha `password`, `passwd`, `pass`, `secret`,
`token`, `api_key`, `apikey`, `secret_key`, `private_key`, `dsn`, `connection_string`.
Prefixos de chave real são sinal forte: `pk_live_`, `sk_live_`, `AKIA`, `ghp_`, `xoxb-`.
**Onde procura:** config de framework, objeto/dicionário de configuração, atributo de classe
de serviço, e o `__init__`/construtor. As três formas aparecem em stacks diferentes.
**Agrava:** se o mesmo valor for **devolvido por um endpoint**, o vazamento deixa de exigir
acesso ao repositório e passa a ser remoto. Reporte como achado separado.

### `arbitrary-code-execution`
**Sinal:** endpoint que recebe conteúdo do corpo/query e o entrega a um interpretador:
`cursor.execute(request...)`, `eval(`, `exec(`, `child_process.exec(` com string montada,
`Function(`. O caso clássico é uma rota `/admin/query` que executa o SQL que chegou.
**Por que CRITICAL sem discussão:** não é um bug que expõe dado, é o banco inteiro nas mãos
de quem chamar a rota.

### `destructive-endpoint-without-auth`
**Sinal:** rota que apaga ou reseta dados (`DELETE FROM` sem `WHERE`, `drop`, `reset`,
`truncate`) sem nenhuma verificação de identidade no caminho.

### `broken-crypto`
**Sinal:** senha gravada em texto plano; comparação de senha direto na query
(`WHERE senha = '...'`); hash com algoritmo quebrado para senha (`md5`, `sha1`) sem salt;
função "de hash" caseira que concatena, codifica em base64 ou trunca o resultado.
**Por que truncar é fatal:** cortar o digest em 10 caracteres reduz o espaço de saída a ponto
de tornar colisão trivial, por mais iterações que o laço tenha. Repetir a codificação do
**mesmo** valor não adiciona entropia nenhuma.

### `sensitive-data-in-response`
**Sinal:** serialização que devolve campo de senha, hash, token ou chave. Procure `password`,
`senha`, `hash`, `secret` dentro de `to_dict`, `toJSON`, `serialize` ou do payload de uma
resposta. Um `to_dict()` que inclui a senha contamina **toda** rota que o usa.

## HIGH

### `god-class` / `god-file`
**Sinal:** uma unidade que acumula responsabilidades de camadas diferentes: conexão com
banco **e** registro de rotas **e** regra de negócio **e** formatação.
**Limiar relativo, nunca absoluto:** um arquivo Python de 300 linhas com 4 domínios e uma
classe JS de 140 linhas com 3 responsabilidades são o mesmo defeito. Conte
**responsabilidades cruzando camadas**, e use o tamanho só como pista.

### `business-logic-in-route`
**Sinal:** handler de rota que consulta o banco, agrega/calcula e formata a saída no próprio
corpo. Pistas: laço sobre resultado de consulta dentro do handler, cálculo de percentual ou
soma, montagem de dicionário aninhado grande.
**Este é o achado que exige ler o conteúdo.** Um projeto com `routes/`, `models/` e
`services/` pode não ter camada de controller nenhuma. Arquivo de rota acima de ~150 linhas é
sinal quase certo.

### `global-mutable-state`
**Sinal:** variável de módulo reatribuída em tempo de execução e compartilhada entre
requisições: cache global, acumulador de total, conexão única em variável global.
**Por que HIGH:** o estado vaza entre requisições, os testes passam a depender de ordem, e
sob concorrência o resultado deixa de ser determinístico.

### `no-dependency-injection`
**Sinal:** classe ou função que instancia a própria dependência (`new Database()`,
`SmtpClient(...)` dentro do construtor) em vez de recebê-la.
**Consequência prática:** não dá para testar sem banco nem sem servidor de e-mail reais.

## MEDIUM

### `n-plus-1-query`
**Sinal estrutural, independente de linguagem:** chamada de I/O **dentro** de laço que itera
sobre o resultado de outra chamada de I/O. Em callbacks aninhados o padrão é o mesmo, só
mais difícil de enxergar: `forEach` externo, consulta por item dentro.
**Correção esperada:** uma consulta com `JOIN`/agregação, ou uma segunda consulta com `IN`.

### `deprecated-api`
**Sinal:** uso de API marcada como obsoleta pelo fornecedor da linguagem ou do framework.
Casos correntes:

| API | Situação | Substituto |
|---|---|---|
| `datetime.utcnow()` (Python) | deprecada desde 3.12; devolve objeto **ingênuo** de fuso | `datetime.now(timezone.utc)` |
| `datetime.utcfromtimestamp()` (Python) | idem | `datetime.fromtimestamp(x, timezone.utc)` |
| `Query.get()` do SQLAlchemy | legado desde 2.0 | `db.session.get(Model, id)` |
| `new Buffer(...)` (Node) | deprecada desde o Node 6 | `Buffer.from(...)` |
| `url.parse()` (Node) | legado | `new URL(...)` |
| `crypto.createCipher` (Node) | deprecada | `createCipheriv` |
| `util.isArray` (Node) | deprecada | `Array.isArray` |

**Por que MEDIUM e não LOW:** `utcnow()` não é só estilo. Ele devolve um datetime sem fuso, e
comparar ingênuo com consciente levanta `TypeError` no momento em que **qualquer** parte do
sistema passar a usar data com fuso. É um defeito latente com data para explodir.
**Procure por padrão, não por ocorrência:** se aparece em 4 arquivos, é um achado com 4
locais, e não 4 achados.

### `manual-async-control-flow`
**Sinal:** contador decrementado à mão para saber quando um lote de operações assíncronas
terminou (`pending--; if (pending === 0) responde()`), callbacks aninhados em três ou mais
níveis.
**Por que importa:** um erro em qualquer ramo deixa o contador travado e a requisição pendura
até o timeout. `Promise.all` ou `async/await` fazem a mesma coisa sem o vazamento.

### `missing-input-validation`
**Sinal:** valor vindo do usuário usado sem checagem de tipo, faixa ou formato; conversão
numérica sem `try`; ausência de validação de tamanho em campo de texto livre.

### `debug-mode-in-production`
**Sinal:** `debug=True`, `DEBUG=True`, `app.set('env','development')` combinados com bind em
`0.0.0.0`.
**Por que não é cosmético no Flask:** o depurador do Werkzeug expõe um **console interativo**
que executa Python no processo. Ligado e acessível pela rede, vale por uma execução remota.
**Relacionado:** CORS liberado para qualquer origem (`CORS(app)` sem restrição,
`Access-Control-Allow-Origin: *`) em API que aceita credencial.

## LOW

### `inconsistent-error-handling`
**Sinal:** erro devolvido como string solta (`res.send("Erro DB")`), `except:` nu que engole
qualquer exceção, mistura de formatos de erro na mesma API, ausência de handler central.
**Consequência:** o cliente não tem como distinguir programaticamente os casos, e a exceção
real desaparece do log.

### `magic-values-and-weak-typing`
**Sinal:** literal repetido sem constante (lista de status válidos escrita em três arquivos),
número solto em regra de negócio (faixas de desconto, limites), `type(x) == list` em vez de
`isinstance(x, list)`, comparação de tipo por igualdade.
**Sobre `type(x) == list`:** quebra silenciosamente com subclasse de `list`. É LOW porque o
impacto é raro, mas é defeito, não estilo.

---

## Como usar este catálogo

1. Um anti-pattern por achado. Se o mesmo padrão aparece em 5 linhas do mesmo arquivo, é
   **um** achado com 5 locais.
2. Se o sinal não estiver no código, o anti-pattern não vai ao relatório. Ausência de achado
   é um resultado legítimo.
3. Achado sem arquivo e linha não é achado.
4. A lista não é exaustiva. Encontrou algo grave que não está aqui? Reporte com a severidade
   da escala e diga que é fora do catálogo, para o catálogo poder crescer.
