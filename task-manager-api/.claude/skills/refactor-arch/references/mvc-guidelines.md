# Arquitetura alvo - MVC

O destino da Fase 3. Vale para qualquer linguagem: o que muda é a extensão do arquivo, não a
regra de quem pode chamar quem.

## Estrutura

```
src/
├── config/           configuração lida do ambiente. Nenhum segredo literal.
├── models/           acesso a dados. Uma unidade por entidade.
├── controllers/      regra de negócio e orquestração. Uma por área do domínio.
├── views/  (routes/) só o mapeamento HTTP -> controller.
├── middlewares/      transversais: erro, autenticação, log.
└── app.<ext>         composition root: monta e conecta. Nada de regra aqui.
```

Nome de pasta é convenção; **a regra que importa é a direção das dependências**.

## Responsabilidade de cada camada

### `models/`
Conversa com o banco e devolve dados. **Só isso.**

- Uma unidade por entidade (`produto`, `usuario`, `pedido`), não uma por aplicação.
- Query **sempre** parametrizada. Sem exceção, nem para inteiro.
- Não formata resposta de API, não decide status HTTP, não valida entrada de usuário.
- Não conhece o framework web. Se o model importa `request`, a camada está errada.

### `controllers/`
Onde a regra de negócio mora.

- Recebe dados já extraídos, chama os models, decide, devolve resultado.
- Faz a validação de domínio (faixa de preço, transição de status válida).
- **Não** monta resposta HTTP diretamente; devolve dados e deixa a view/rota traduzir. Em
  frameworks onde isso é custoso, é aceitável devolver `(dados, status)`, desde que o
  controller não conheça o objeto `request`.

### `views/` ou `routes/`
Mapeia caminho e método para o controller. Deve caber numa tela.

- Extrai parâmetros e corpo, chama o controller, serializa.
- **Zero** consulta a banco. **Zero** cálculo. Se tem laço agregando resultado aqui, o código
  está na camada errada, e este é exatamente o defeito `business-logic-in-route`.

### `config/`
Toda configuração vem do ambiente.

- Segredo: `os.environ.get("SECRET_KEY", <default de desenvolvimento>)`.
- Quando o valor já estava público no repositório, **mantenha-o como default**: trocar
  quebra quem clonar; o ganho vem de o valor passar a ser sobrescrevível sem editar código.
- `debug` também vem do ambiente, com default seguro (desligado).

### `middlewares/`
Erro tratado num lugar só. Um handler central converte exceção em resposta padronizada, com
o mesmo formato para toda a API. Some o `except` nu espalhado pelos handlers.

## Direção das dependências

```
routes ──► controllers ──► models ──► banco
   │            │
   └────────────┴──► config
```

**Nunca ao contrário.** Model não importa controller; controller não importa rota. Se
precisar, a abstração está no lugar errado.

## Contrato de API

**Não muda.** Mesmos caminhos, métodos, formato de resposta e códigos de status. A prova da
refatoração é a aplicação responder igual depois.

**Única exceção, e ela é explícita:** endpoint que existe apenas para expor o problema
(executar SQL arbitrário, resetar o banco sem autenticação, devolver a chave secreta) é
**removido**. Isso reduz a superfície de propósito e precisa constar do relatório final.

## Critério de pronto

1. Nenhum segredo literal no código.
2. Nenhuma query montada por concatenação.
3. Nenhum handler de rota consultando banco ou calculando.
4. Erro tratado por handler central.
5. Entry point que só monta a aplicação.
6. **A aplicação sobe e os endpoints originais respondem.** Verificado por execução, não por
   leitura.
