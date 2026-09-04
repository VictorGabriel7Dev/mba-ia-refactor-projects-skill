'use strict';
/**
 * Derivação e verificação de senha.
 *
 * Substitui `badCrypto()`, que concatenava 10.000 vezes o base64 do MESMO valor e
 * truncava em 10 caracteres: nenhuma entropia adicionada e espaço de saída pequeno
 * o bastante para colisão trivial.
 */
const crypto = require('crypto');

const TAM = 64;

function hashPassword(senha, salt = crypto.randomBytes(16)) {
    const derivada = crypto.scryptSync(String(senha), salt, TAM);
    return `scrypt$${salt.toString('hex')}$${derivada.toString('hex')}`;
}

function verifyPassword(senha, guardada) {
    if (typeof guardada !== 'string' || !guardada.startsWith('scrypt$')) return false;
    const [, saltHex, hashHex] = guardada.split('$');
    try {
        const derivada = crypto.scryptSync(String(senha), Buffer.from(saltHex, 'hex'), TAM);
        return crypto.timingSafeEqual(Buffer.from(hashHex, 'hex'), derivada);
    } catch {
        return false;
    }
}

/** Rastro de pagamento sem dado sensível: antes o log tinha o cartão INTEIRO. */
function mascararCartao(cc) {
    const texto = String(cc || '');
    return texto.length <= 4 ? '****' : `**** **** **** ${texto.slice(-4)}`;
}

module.exports = { hashPassword, verifyPassword, mascararCartao };
