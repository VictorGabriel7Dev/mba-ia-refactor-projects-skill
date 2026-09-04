'use strict';
/**
 * Configuração vinda do ambiente. Nenhum valor sensível literal.
 *
 * Os defaults são de DESENVOLVIMENTO. A `pk_live_...` que estava aqui NÃO foi
 * mantida como default: além de vazar, ela é de produção. Quem tinha acesso ao
 * repositório já a leu, então ela precisa ser ROTACIONADA no provedor -- tirar do
 * código não desfaz a exposição.
 */
const config = {
    dbUser: process.env.DB_USER || 'dev_user',
    dbPass: process.env.DB_PASS || 'dev-only-password',
    dbFile: process.env.DB_FILE || ':memory:',
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || 'pk_test_dev_only',
    smtpUser: process.env.SMTP_USER || 'no-reply@example.invalid',
    port: Number(process.env.PORT || 3000),
};

// Valores de domínio que eram literais no meio da regra de negócio.
const constants = {
    PREFIXO_CARTAO_APROVADO: '4',
    STATUS_PAGO: 'PAID',
    STATUS_NEGADO: 'DENIED',
    SENHA_MIN: 6,
};

module.exports = { config, constants };
