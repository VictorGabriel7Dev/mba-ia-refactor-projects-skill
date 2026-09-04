#!/usr/bin/env python3
"""
smoke_test.py
=============

Prova, por execução, que um dos projetos continua respondendo depois da refatoração.

Por que existe: a Fase 3 da skill exige validar "boot da aplicação + endpoints
funcionando", e ler o código não é validar. Este script sobe o servidor, bate em
cada endpoint e compara com o comportamento registrado ANTES da refatoração.

Uso:
    python tools/smoke_test.py --projeto code-smells-project
    python tools/smoke_test.py --projeto ecommerce-api-legacy
    python tools/smoke_test.py --projeto task-manager-api
    python tools/smoke_test.py --projeto <x> --salvar reports/_baseline-<x>.json

`--salvar` grava o resultado como linha de base. Sem ele, o script compara com a
linha de base já gravada e falha se algum endpoint mudou de status.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# (nome, método, caminho, corpo). O nome é a chave da comparação, então não mude.
SUITES: dict[str, dict] = {
    "code-smells-project": {
        "porta": 5000,
        "comando": [".venv-check/bin/python", "src/app.py"],
        "limpar": ["loja.db"],
        "endpoints": [
            ("index",            "GET",  "/", None),
            ("health",           "GET",  "/health", None),
            ("produtos_listar",  "GET",  "/produtos", None),
            ("produto_1",        "GET",  "/produtos/1", None),
            ("produto_404",      "GET",  "/produtos/99999", None),
            ("produtos_busca",   "GET",  "/produtos/busca?q=Mouse", None),
            ("produto_criar",    "POST", "/produtos",
             {"nome": "Item de teste", "preco": 10.5, "estoque": 3, "categoria": "geral"}),
            ("usuarios_listar",  "GET",  "/usuarios", None),
            ("usuario_1",        "GET",  "/usuarios/1", None),
            ("usuario_criar",    "POST", "/usuarios",
             {"nome": "Teste", "email": "teste@ex.com", "senha": "segredo123"}),
            ("login_ok",         "POST", "/login",
             {"email": "admin@loja.com", "senha": "admin123"}),
            ("login_errado",     "POST", "/login",
             {"email": "admin@loja.com", "senha": "errada"}),
            # O caso que prova a injeção: uma aspa no campo de senha.
            ("login_injecao",    "POST", "/login",
             {"email": "admin@loja.com", "senha": "x' OR '1'='1"}),
            ("pedido_criar",     "POST", "/pedidos",
             {"usuario_id": 2, "itens": [{"produto_id": 1, "quantidade": 1}]}),
            ("pedidos_listar",   "GET",  "/pedidos", None),
            ("pedidos_usuario",  "GET",  "/pedidos/usuario/2", None),
            ("relatorio_vendas", "GET",  "/relatorios/vendas", None),
        ],
        # Mudanças DELIBERADAS: são a correção, não regressão. Declaradas aqui para
        # o relatório distinguir "consertamos" de "quebramos".
        "mudanca_esperada": {
            "login_injecao": (401, "SQL Injection corrigida: a aspa no campo senha "
                                   "deixa de autenticar (era 200)"),
        },
    },
    "ecommerce-api-legacy": {
        "porta": 3000,
        "comando": ["node", "src/app.js"],
        "limpar": [],
        "endpoints": [
            ("checkout_ok",      "POST", "/api/checkout",
             {"usr": "Ana", "eml": "ana@ex.com", "pwd": "segredo123", "c_id": 1, "card": "4111111111111111"}),
            ("checkout_negado",  "POST", "/api/checkout",
             {"usr": "Bruno", "eml": "bruno@ex.com", "pwd": "segredo123", "c_id": 1, "card": "5111111111111111"}),
            ("checkout_faltando","POST", "/api/checkout", {"usr": "Ana"}),
            ("checkout_curso_404","POST","/api/checkout",
             {"usr": "Ana", "eml": "ana@ex.com", "pwd": "x", "c_id": 999, "card": "4111111111111111"}),
            ("relatorio",        "GET",  "/api/admin/financial-report", None),
            ("deletar_usuario",  "DELETE", "/api/users/1", None),
        ],
    },
    "task-manager-api": {
        "porta": 5000,
        "comando": [".venv-check/bin/python", "app.py"],
        "limpar": ["instance/tasks.db", "tasks.db"],
        "semear": [".venv-check/bin/python", "seed.py"],
        "endpoints": [
            ("index",            "GET",  "/", None),
            ("health",           "GET",  "/health", None),
            ("tasks_listar",     "GET",  "/tasks", None),
            ("task_1",           "GET",  "/tasks/1", None),
            ("task_404",         "GET",  "/tasks/99999", None),
            ("task_criar",       "POST", "/tasks",
             {"title": "Task de teste", "priority": 2, "status": "pending"}),
            ("task_titulo_curto","POST", "/tasks", {"title": "ab"}),
            ("tasks_busca",      "GET",  "/tasks/search?q=a", None),
            ("tasks_stats",      "GET",  "/tasks/stats", None),
            ("users_listar",     "GET",  "/users", None),
            ("user_1",           "GET",  "/users/1", None),
            ("login_ok",         "POST", "/login",
             {"email": "joao@email.com", "password": "1234"}),
            ("login_errado",     "POST", "/login",
             {"email": "joao@email.com", "password": "errada"}),
            ("relatorio_resumo", "GET",  "/reports/summary", None),
            ("relatorio_user",   "GET",  "/reports/user/1", None),
            ("categorias",       "GET",  "/categories", None),
        ],
    },
}


def chamar(base: str, metodo: str, caminho: str, corpo) -> dict:
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(base + caminho, data=dados, method=metodo)
    if dados:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            texto = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        texto, status = e.read().decode("utf-8", "replace"), e.code
    except Exception as e:
        return {"status": 0, "erro": type(e).__name__ + ": " + str(e)}

    saida = {"status": status}
    try:
        payload = json.loads(texto)
    except ValueError:
        saida["forma"] = "texto"
        return saida
    # Compara a FORMA da resposta, não o conteúdo: id gerado e timestamp mudam a
    # cada execução e fariam a comparação falhar sempre.
    if isinstance(payload, list):
        saida["forma"] = f"lista[{len(payload)}]"
        if payload and isinstance(payload[0], dict):
            saida["chaves"] = sorted(payload[0].keys())
    elif isinstance(payload, dict):
        saida["forma"] = "objeto"
        saida["chaves"] = sorted(payload.keys())
    else:
        saida["forma"] = type(payload).__name__
    return saida


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--projeto", required=True, choices=sorted(SUITES))
    ap.add_argument("--salvar", type=Path, help="grava o resultado como linha de base")
    ap.add_argument("--espera", type=float, default=5.0, help="segundos até o servidor subir")
    args = ap.parse_args()

    suite = SUITES[args.projeto]
    cwd = RAIZ / args.projeto
    base = f"http://127.0.0.1:{suite['porta']}"

    for alvo in suite["limpar"]:
        p = cwd / alvo
        if p.exists():
            p.unlink()
    if suite.get("semear"):
        subprocess.run(suite["semear"], cwd=cwd, capture_output=True, text=True, timeout=120)

    env = dict(os.environ, PORT=str(suite["porta"]), FLASK_RUN_PORT=str(suite["porta"]))
    proc = subprocess.Popen(suite["comando"], cwd=cwd, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    time.sleep(args.espera)
    subiu = proc.poll() is None
    resultado = {"_boot": {"subiu": subiu}}
    if not subiu:
        resultado["_boot"]["saida"] = (proc.stdout.read() or "")[-2000:]
    else:
        for nome, metodo, caminho, corpo in suite["endpoints"]:
            resultado[nome] = chamar(base, metodo, caminho, corpo)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            proc.terminate()
        proc.wait(timeout=15)

    if args.salvar:
        args.salvar.parent.mkdir(parents=True, exist_ok=True)
        args.salvar.write_text(json.dumps(resultado, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
        print(f"linha de base salva em {args.salvar}")
        for k, v in resultado.items():
            print(f"  {k:22} {v}")
        return 0 if subiu else 1

    ref_path = RAIZ / "reports" / f"_baseline-{args.projeto}.json"
    if not ref_path.exists():
        sys.exit(f"❌ sem linha de base: rode com --salvar {ref_path.relative_to(RAIZ)} antes")
    ref = json.loads(ref_path.read_text(encoding="utf-8"))

    previstas = suite.get("mudanca_esperada", {})
    difs, deliberadas = [], []
    print(f"{'endpoint':24} {'antes':>8}  {'depois':>8}")
    for nome, esperado in ref.items():
        if nome == "_boot":
            continue
        o = resultado.get(nome, {})
        antes, depois = esperado.get("status"), o.get("status")
        if antes == depois:
            marca = ""
        elif nome in previstas and depois == previstas[nome][0]:
            marca = "   <-- mudou de propósito"
            deliberadas.append((nome, antes, depois, previstas[nome][1]))
        else:
            marca = "   <-- REGRESSÃO"
            difs.append((nome, antes, depois))
        print(f"  {nome:22} {str(antes):>8}  {str(depois):>8}{marca}")

    if not resultado["_boot"]["subiu"]:
        print("\n❌ a aplicação NÃO subiu")
        print(resultado["_boot"].get("saida", ""))
        return 1
    if deliberadas:
        print("\nMudanças deliberadas (correção, não regressão):")
        for nome, a, d, motivo in deliberadas:
            print(f"  {nome}: {a} -> {d}  {motivo}")
    if difs:
        print(f"\n❌ {len(difs)} regressão(ões)")
        return 1
    total = len(ref) - 1
    print(f"\n✅ aplicação subiu e {total} endpoint(s) conferidos: "
          f"{total - len(deliberadas)} idênticos, {len(deliberadas)} corrigidos de propósito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
