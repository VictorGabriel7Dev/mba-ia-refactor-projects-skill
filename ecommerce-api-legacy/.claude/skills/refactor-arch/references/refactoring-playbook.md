# Playbook de refatoração

12 transformações, uma por anti-pattern do catálogo. Cada uma tem **antes** e **depois** em
código. Os exemplos alternam Python e JavaScript de propósito: o padrão é o mesmo, a sintaxe
é detalhe.

Ordem de aplicação: CRITICAL primeiro. Uma transformação por vez, verificando que a aplicação
ainda sobe entre elas.

---

## 1. Query concatenada → query parametrizada
Resolve `sql-injection`. Aplique **antes** de qualquer reorganização de pastas: é o achado que
tem exploração imediata.

```python
# ANTES
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)

# DEPOIS
cursor.execute(
    "SELECT * FROM usuarios WHERE email = ? AND senha_hash = ?",
    (email, hash_senha(senha)),
)
```

Vale também para o caso que parece inofensivo:

```python
# ANTES                                        # DEPOIS
cursor.execute("... WHERE id = " + str(id))    cursor.execute("... WHERE id = ?", (id,))
```

Filtro montado condicionalmente também parametriza:

```python
# DEPOIS
sql, params = "SELECT * FROM produtos WHERE 1=1", []
if termo:
    sql += " AND (nome LIKE ? OR descricao LIKE ?)"
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    sql += " AND categoria = ?"
    params.append(categoria)
cursor.execute(sql, params)
```

## 2. Segredo literal → configuração por ambiente
Resolve `hardcoded-credentials`.

```javascript
// ANTES  (src/utils.js)
const config = {
    dbPass: "senha_super_secreta_prod_123",
    paymentGatewayKey: "pk_live_1234567890abcdef",
};

// DEPOIS  (src/config/settings.js)
const config = {
    dbPass: process.env.DB_PASS || "dev-only-password",
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || "pk_test_dev_only",
};
```

Duas regras que andam juntas:

- o default é **de desenvolvimento**, nunca a chave real que estava no repositório;
- chave `pk_live_` que já vazou continua vazada. Registre no relatório que ela precisa ser
  **rotacionada no provedor**: tirar do código não desfaz a exposição.

## 3. Endpoint de execução arbitrária → remoção
Resolve `arbitrary-code-execution` e `destructive-endpoint-without-auth`. Aqui não há
refatoração: não existe versão segura de "execute o SQL que eu mandar".

```python
# ANTES
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json().get("sql", ""))   # o banco inteiro

# DEPOIS
# removido. Operação administrativa é tarefa de CLI autenticada, não de rota HTTP.
```

Anote a remoção no relatório: é a única mudança deliberada de contrato de API.

## 4. Hash caseiro → função de derivação de senha
Resolve `broken-crypto`.

```javascript
// ANTES
function badCrypto(pwd) {
    let hash = "";
    for (let i = 0; i < 10000; i++) hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    return hash.substring(0, 10);          // 10 caracteres: colide fácil
}

// DEPOIS
const crypto = require('crypto');
function hashPassword(pwd, salt = crypto.randomBytes(16)) {
    const derived = crypto.scryptSync(pwd, salt, 64);
    return `${salt.toString('hex')}:${derived.toString('hex')}`;
}
function verifyPassword(pwd, stored) {
    const [saltHex, hashHex] = stored.split(':');
    const derived = crypto.scryptSync(pwd, Buffer.from(saltHex, 'hex'), 64);
    return crypto.timingSafeEqual(Buffer.from(hashHex, 'hex'), derived);
}
```

Em Python, o equivalente de biblioteca padrão:

```python
# ANTES                                  # DEPOIS
hashlib.md5(pwd.encode()).hexdigest()    hashlib.scrypt(pwd.encode(), salt=salt, n=2**14, r=8, p=1)
```

Três pontos que o exemplo ruim erra e o bom acerta: **salt** por usuário, função **lenta** de
propósito, e comparação em **tempo constante**.

## 5. Campo sensível na serialização → projeção explícita
Resolve `sensitive-data-in-response`.

```python
# ANTES
def to_dict(self):
    return {'id': self.id, 'email': self.email, 'password': self.password, ...}

# DEPOIS
def to_dict(self):
    """Representação PÚBLICA. Nunca inclua credencial: este método é usado por
    toda rota, e um campo a mais aqui vaza em todas de uma vez."""
    return {'id': self.id, 'email': self.email, 'role': self.role, ...}
```

## 6. God class → camadas por responsabilidade
Resolve `god-class` e `god-file`. Corte **por camada**, não por tamanho de arquivo.

```
# ANTES                          # DEPOIS
AppManager.js (141 linhas)       config/settings.js       ← configuração
  ├─ conexão com o banco         models/user_model.js     ← acesso a dados
  ├─ registro de rotas           models/course_model.js
  ├─ regra de checkout           controllers/checkout_controller.js  ← regra
  ├─ montagem de relatório       controllers/report_controller.js
  └─ exclusão de usuário         routes/index.js          ← só o mapeamento
                                 middlewares/error_handler.js
```

Procedimento: liste as responsabilidades da unidade, dê um destino a cada uma, mova uma por
vez, rode a aplicação entre os movimentos.

## 7. Regra de negócio na rota → controller
Resolve `business-logic-in-route`. É a transformação central do padrão.

```python
# ANTES  (routes/report_routes.py, 90 linhas num handler)
@report_bp.route('/reports/summary')
def summary_report():
    users = User.query.all()
    stats = []
    for u in users:                                   # consulta dentro de laço
        tasks = Task.query.filter_by(user_id=u.id).all()
        done = len([t for t in tasks if t.status == 'done'])
        stats.append({'user_id': u.id, 'completion_rate': round(done/len(tasks)*100, 2)})
    return jsonify({'user_productivity': stats}), 200

# DEPOIS
# routes/report_routes.py
@report_bp.route('/reports/summary')
def summary_report():
    return jsonify(ReportController.summary()), 200

# controllers/report_controller.py
class ReportController:
    @staticmethod
    def summary():
        return {'user_productivity': TaskModel.completion_by_user()}

# models/task_model.py
@staticmethod
def completion_by_user():
    rows = (db.session.query(User.id, User.name,
                             func.count(Task.id),
                             func.sum(case((Task.status == 'done', 1), else_=0)))
            .outerjoin(Task, Task.user_id == User.id)
            .group_by(User.id).all())          # uma consulta, não N+1
    return [...]
```

A rota volta a caber em uma linha, a regra fica testável sem HTTP, e o N+1 morre junto.

## 8. N+1 → consulta única
Resolve `n-plus-1-query`.

```javascript
// ANTES: 1 + N + N*M consultas
db.all("SELECT * FROM courses", [], (err, courses) => {
    courses.forEach(c => {
        db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrs) => {
            enrs.forEach(e => db.get("SELECT ... FROM users WHERE id = ?", [e.user_id], ...));
        });
    });
});

// DEPOIS: 1 consulta
const sql = `
  SELECT c.id, c.title, u.name AS student, p.amount, p.status
    FROM courses c
    LEFT JOIN enrollments e ON e.course_id = c.id
    LEFT JOIN users       u ON u.id = e.user_id
    LEFT JOIN payments    p ON p.enrollment_id = e.id`;
const rows = await all(sql);
```

Quando o `JOIN` não serve, a segunda melhor forma é uma consulta com `IN` sobre os ids
coletados. O que não vale é consultar dentro do laço.

## 9. Contador manual → async/await
Resolve `manual-async-control-flow`.

```javascript
// ANTES
let pending = items.length;
items.forEach(i => doAsync(i, () => { pending--; if (pending === 0) res.json(out); }));
// erro em qualquer ramo => contador trava => requisição pendura até o timeout

// DEPOIS
const util = require('util');
const all = util.promisify(db.all.bind(db));
try {
    const out = await Promise.all(items.map(i => doAsync(i)));
    res.json(out);
} catch (err) {
    next(err);            // vai para o handler central de erro
}
```

## 10. API deprecada → substituto atual
Resolve `deprecated-api`. Troque **todas** as ocorrências: deixar uma é manter o defeito.

```python
# ANTES                                    # DEPOIS
from datetime import datetime              from datetime import datetime, timezone
created_at = datetime.utcnow()             created_at = datetime.now(timezone.utc)
```

⚠️ **Cuidado com a mistura.** `utcnow()` devolve datetime **ingênuo**; `now(timezone.utc)`
devolve **consciente**. Comparar um com o outro levanta
`TypeError: can't compare offset-naive and offset-aware datetimes`. Ou troca tudo, ou não
troca nada. Se o banco guarda ingênuo, converta na leitura ou normalize a coluna: metade
convertida é pior que nenhuma.

```javascript
// ANTES                       // DEPOIS
new Buffer(data)               Buffer.from(data)
url.parse(str)                 new URL(str)
util.isArray(x)                Array.isArray(x)
```

## 11. Erro solto → handler central
Resolve `inconsistent-error-handling`.

```python
# ANTES: repetido em cada handler
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500     # vaza detalhe interno

# DEPOIS  (middlewares/error_handler.py)
class AppError(Exception):
    def __init__(self, mensagem, status=400):
        self.mensagem, self.status = mensagem, status

def registrar(app):
    @app.errorhandler(AppError)
    def _app_error(e):
        return jsonify({"erro": e.mensagem, "sucesso": False}), e.status

    @app.errorhandler(Exception)
    def _inesperado(e):
        app.logger.exception(e)               # detalhe vai para o log
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500
```

Some o `except` nu, a resposta fica uniforme, e a exceção real aparece no log em vez de na
resposta.

## 12. Valor mágico e comparação de tipo → constante e `isinstance`
Resolve `magic-values-and-weak-typing`.

```python
# ANTES  (a mesma lista repetida em 3 arquivos)
if status not in ['pending', 'in_progress', 'done', 'cancelled']:
if type(tags) == list:
if faturamento > 10000: desconto = faturamento * 0.1

# DEPOIS  (config/constants.py)
STATUS_VALIDOS = ('pending', 'in_progress', 'done', 'cancelled')
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))

if status not in STATUS_VALIDOS:
if isinstance(tags, list):
desconto = next((v * taxa for limite, taxa in FAIXAS_DESCONTO if v > limite), 0)
```

---

## Ao terminar

1. **Suba a aplicação.** Se não subir, não terminou.
2. **Chame cada endpoint do inventário da Fase 3, passo 1**, e compare com o comportamento
   registrado antes.
3. **Releia o relatório da Fase 2** e marque item a item o que foi resolvido.
4. **Diga o que ficou de fora e por quê.** Pendência declarada é informação; pendência
   escondida atrás de um checklist verde é armadilha para o próximo.
