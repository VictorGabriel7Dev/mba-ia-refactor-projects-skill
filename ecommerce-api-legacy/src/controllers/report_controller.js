'use strict';
/**
 * Relatório financeiro.
 *
 * A consulta agora é uma só; o agrupamento por curso acontece aqui, em memória, e o
 * formato de saída é idêntico ao anterior: [{ course, revenue, students: [...] }].
 */
const { constants } = require('../config/settings');

module.exports = ({ courseModel }) => ({
    async financeiro() {
        const linhas = await courseModel.relatorioFinanceiro();
        const porCurso = new Map();
        for (const l of linhas) {
            if (!porCurso.has(l.course_id)) {
                porCurso.set(l.course_id, { course: l.course, revenue: 0, students: [] });
            }
            const item = porCurso.get(l.course_id);
            if (l.student === null && l.paid === null) continue;  // curso sem matrícula
            if (l.payment_status === constants.STATUS_PAGO) item.revenue += l.paid;
            item.students.push({ student: l.student || 'Unknown', paid: l.paid || 0 });
        }
        return [...porCurso.values()];
    },
});
