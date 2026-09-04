'use strict';
module.exports = ({ userModel }) => ({
    async deletar(id) {
        await userModel.deletarEmCascata(id);
        // A mensagem antiga admitia o defeito: "as matrículas e pagamentos ficaram
        // sujos no banco". Agora não ficam.
        return { msg: 'Usuário deletado, junto com suas matrículas e pagamentos' };
    },
});
