'use strict';
/**
 * Mapeamento HTTP -> controller. Zero consulta, zero regra.
 *
 * Caminhos, métodos e códigos de status são os mesmos de antes. O CORPO das
 * respostas de erro mudou de string solta para JSON `{ "erro": ... }`, que é o que
 * o checklist "Error handling centralizado" do enunciado pede. Mudança declarada.
 */
const express = require('express');

module.exports = ({ checkoutController, reportController, userController }) => {
    const router = express.Router();

    router.post('/api/checkout', async (req, res, next) => {
        try {
            const b = req.body || {};
            res.status(200).json(await checkoutController.executar({
                nome: b.usr, email: b.eml, senha: b.pwd, cursoId: b.c_id, cartao: b.card,
            }));
        } catch (err) { next(err); }
    });

    router.get('/api/admin/financial-report', async (req, res, next) => {
        try {
            res.json(await reportController.financeiro());
        } catch (err) { next(err); }
    });

    router.delete('/api/users/:id', async (req, res, next) => {
        try {
            res.json(await userController.deletar(req.params.id));
        } catch (err) { next(err); }
    });

    return router;
};
