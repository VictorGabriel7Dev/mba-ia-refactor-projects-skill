'use strict';
/**
 * Conexão, esquema e helpers com Promise.
 *
 * A conexão deixa de ser criada dentro da classe de aplicação e passa a ser
 * injetada: quem monta a aplicação decide qual banco usar. Os helpers `run`, `get`
 * e `all` devolvem Promise, o que elimina o aninhamento de callbacks e o controle
 * de fluxo por contador manual.
 */
const sqlite3 = require('sqlite3').verbose();

function criarConexao(arquivo) {
    return new sqlite3.Database(arquivo);
}

const promisificar = (db) => ({
    run(sql, params = []) {
        return new Promise((ok, falha) => {
            db.run(sql, params, function (err) {
                if (err) return falha(err);
                ok({ lastID: this.lastID, changes: this.changes });
            });
        });
    },
    get(sql, params = []) {
        return new Promise((ok, falha) =>
            db.get(sql, params, (err, row) => (err ? falha(err) : ok(row))));
    },
    all(sql, params = []) {
        return new Promise((ok, falha) =>
            db.all(sql, params, (err, rows) => (err ? falha(err) : ok(rows || []))));
    },
    exec(sql) {
        return new Promise((ok, falha) => db.exec(sql, (err) => (err ? falha(err) : ok())));
    },
});

const ESQUEMA = `
    CREATE TABLE IF NOT EXISTS users       (id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT);
    CREATE TABLE IF NOT EXISTS courses     (id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER);
    CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY, user_id INTEGER, course_id INTEGER);
    CREATE TABLE IF NOT EXISTS payments    (id INTEGER PRIMARY KEY, enrollment_id INTEGER, amount REAL, status TEXT);
    CREATE TABLE IF NOT EXISTS audit_logs  (id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME);
`;

async function inicializar(dbp, { hashPassword }) {
    await dbp.exec(ESQUEMA);
    const { total } = await dbp.get('SELECT COUNT(*) AS total FROM users');
    if (total > 0) return;
    // A senha de exemplo entra JÁ DERIVADA. Antes ia como '123' em texto plano.
    await dbp.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
        ['Leonan', 'leonan@fullcycle.com.br', hashPassword('123')]);
    await dbp.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1), (?, ?, 1)',
        ['Clean Architecture', 997.0, 'Docker', 497.0]);
    await dbp.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
    await dbp.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.0, ?)',
        ['PAID']);
}

module.exports = { criarConexao, promisificar, inicializar, ESQUEMA };
