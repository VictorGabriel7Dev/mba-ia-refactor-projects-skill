'use strict';
/**
 * Tratamento de erro centralizado.
 *
 * Antes cada ramo devolvia uma string solta ("Erro DB", "Bad Request"), sem código,
 * sem formato e sem log. Agora o formato é único e o detalhe vai para o log.
 */
class AppError extends Error {
    constructor(mensagem, status = 400) {
        super(mensagem);
        this.status = status;
    }
}

function naoEncontrado(req, res) {
    res.status(404).json({ erro: 'Rota não encontrada' });
}

// A assinatura de 4 parâmetros é o que faz o Express reconhecer isto como handler
// de erro. Remover o `next` "que não é usado" quebra o middleware em silêncio.
function tratarErro(err, req, res, next) { // eslint-disable-line no-unused-vars
    const status = err.status || 500;
    if (status >= 500) console.error('[erro]', err);
    res.status(status).json({ erro: err.message || 'Erro interno' });
}

module.exports = { AppError, naoEncontrado, tratarErro };
