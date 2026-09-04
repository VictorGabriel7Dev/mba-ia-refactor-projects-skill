'use strict';
/** Composition root: cria as dependências, conecta as camadas, sobe o servidor. */
const express = require('express');

const { config } = require('./config/settings');
const { criarConexao, promisificar, inicializar } = require('./database');
const { hashPassword } = require('./security');
const { naoEncontrado, tratarErro } = require('./middlewares/error_handler');
const criarUserModel = require('./models/user_model');
const criarCourseModel = require('./models/course_model');
const criarCheckoutController = require('./controllers/checkout_controller');
const criarReportController = require('./controllers/report_controller');
const criarUserController = require('./controllers/user_controller');
const criarRotas = require('./views/routes');

async function montar() {
    const db = promisificar(criarConexao(config.dbFile));
    await inicializar(db, { hashPassword });

    const userModel = criarUserModel(db);
    const courseModel = criarCourseModel(db);

    const app = express();
    app.use(express.json());
    app.use(criarRotas({
        checkoutController: criarCheckoutController({ userModel, courseModel }),
        reportController: criarReportController({ courseModel }),
        userController: criarUserController({ userModel }),
    }));
    app.use(naoEncontrado);
    app.use(tratarErro);
    return app;
}

if (require.main === module) {
    montar()
        .then((app) => app.listen(config.port, () => {
            console.log(`LMS rodando na porta ${config.port}...`);
        }))
        .catch((err) => { console.error('falha ao subir:', err); process.exit(1); });
}

module.exports = { montar };
