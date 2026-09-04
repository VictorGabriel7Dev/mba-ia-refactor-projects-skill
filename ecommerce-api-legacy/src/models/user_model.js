'use strict';
/** Acesso a dados de usuário. Só SQL parametrizado, sem regra de negócio. */
module.exports = (db) => ({
    porEmail: (email) => db.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]),
    criar: (nome, email, senhaHash) =>
        db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [nome, email, senhaHash]),
    /**
     * Exclusão em cascata, dentro de uma transação.
     * Antes o DELETE apagava só o usuário e deixava matrículas e pagamentos órfãos,
     * o que fazia o relatório financeiro somar receita de matrícula sem dono.
     */
    async deletarEmCascata(id) {
        await db.exec('BEGIN');
        try {
            await db.run(
                'DELETE FROM payments WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)',
                [id]);
            await db.run('DELETE FROM enrollments WHERE user_id = ?', [id]);
            const r = await db.run('DELETE FROM users WHERE id = ?', [id]);
            await db.exec('COMMIT');
            return r;
        } catch (err) {
            await db.exec('ROLLBACK');
            throw err;
        }
    },
});
