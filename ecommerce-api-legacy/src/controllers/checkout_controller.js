'use strict';
/** Regra de checkout. Não conhece `req` nem `res`. */
const { constants } = require('../config/settings');
const { AppError } = require('../middlewares/error_handler');
const { hashPassword, mascararCartao } = require('../security');

module.exports = ({ userModel, courseModel, logger = console }) => ({
    async executar({ nome, email, senha, cursoId, cartao }) {
        if (!nome || !email || !cursoId || !cartao) {
            throw new AppError('Bad Request', 400);
        }
        if (typeof cartao !== 'string') {
            throw new AppError('Cartão inválido', 400);
        }

        const curso = await courseModel.ativoPorId(cursoId);
        if (!curso) throw new AppError('Curso não encontrado', 404);

        let usuario = await userModel.porEmail(email);
        if (!usuario) {
            // A senha só é exigida no ramo que CRIA usuário, que é onde ela era
            // usada antes. Validar cedo demais mudaria o 404 de curso inexistente
            // para 400, quebrando o contrato: foi o que a linha de base pegou.
            if (!senha || String(senha).length < constants.SENHA_MIN) {
                // Antes caía em `badCrypto(p || "123456")`: usuário criado com senha
                // padrão conhecida, sem ninguém saber.
                throw new AppError(
                    `Senha deve ter ao menos ${constants.SENHA_MIN} caracteres`, 400);
            }
            const { lastID } = await userModel.criar(nome, email, hashPassword(senha));
            usuario = { id: lastID };
        }

        // O log nunca vê o número do cartão nem a chave do gateway.
        logger.log(`Processando pagamento do curso ${cursoId} (${mascararCartao(cartao)})`);
        const status = cartao.startsWith(constants.PREFIXO_CARTAO_APROVADO)
            ? constants.STATUS_PAGO : constants.STATUS_NEGADO;
        if (status === constants.STATUS_NEGADO) {
            throw new AppError('Pagamento recusado', 400);
        }

        const { lastID: matriculaId } = await courseModel.criarMatricula(usuario.id, cursoId);
        await courseModel.criarPagamento(matriculaId, curso.price, status);
        await courseModel.registrarAuditoria(`Checkout curso ${cursoId} por ${usuario.id}`);

        return { msg: 'Sucesso', enrollment_id: matriculaId };
    },
});
