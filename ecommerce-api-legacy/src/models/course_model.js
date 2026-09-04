'use strict';
/** Acesso a dados de curso, matrícula, pagamento e auditoria. */
module.exports = (db) => ({
    ativoPorId: (id) => db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]),

    criarMatricula: (userId, courseId) =>
        db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [userId, courseId]),

    criarPagamento: (enrollmentId, valor, status) =>
        db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, valor, status]),

    registrarAuditoria: (acao) =>
        db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [acao]),

    /**
     * Relatório financeiro em UMA consulta.
     * Antes eram 1 + N + N*M: cursos, matrículas por curso, e usuário e pagamento
     * por matrícula, com callbacks aninhados em quatro níveis.
     */
    relatorioFinanceiro: () => db.all(`
        SELECT c.id            AS course_id,
               c.title         AS course,
               u.name          AS student,
               p.amount        AS paid,
               p.status        AS payment_status
          FROM courses c
          LEFT JOIN enrollments e ON e.course_id = c.id
          LEFT JOIN users       u ON u.id = e.user_id
          LEFT JOIN payments    p ON p.enrollment_id = e.id
         ORDER BY c.id`),
});
