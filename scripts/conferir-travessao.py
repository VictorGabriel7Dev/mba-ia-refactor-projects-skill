#!/usr/bin/env python3
"""Guard: nenhum travessao no repositorio, e o motivo nao e estetico.

Regra perene da casa: o travessao longo entrega texto de IA e o objetivo e copy
humana. Nao e so estilo. O caractere ja quebrou num sistema legado que gravou
lixo no lugar dele, e num expurgo anterior mediu-se que **40 das 1094 mensagens
que um bot mandou em 30 dias** sairam com travessao para clientes reais, porque
o prompt tinha o caractere dentro de string viva e o modelo imita a pontuacao
que le.

Uma regra que depende de alguem lembrar de rodar `grep` antes do merge nao se
sustenta. Esta trava sozinha, no CI.

Ao corrigir, use a pontuacao do CONTEXTO, nunca um replace cego por um unico
caractere:

    "Termo <travessao> descricao"  ->  "Termo: descricao"
    fronteira de oracao / aposto   ->  virgula ou ponto final
    separador de marca em titulo   ->  middot
    faixa numerica colada          ->  hifen

Duas valvulas, ambas com motivo escrito no proprio arquivo:

  `.travessao-ignore`     globs de arquivo fora do escopo (conteudo de terceiro,
                          arquivo gerado, codigo vendorizado).
  `.travessao-permitido`  strings LITERAIS que sao identificador de sistema
                          externo (ex.: nome de item do Vaultwarden, que o
                          `bw get item` resolve por nome exato). Reescrever
                          quebraria o comando documentado.

Uso:
    python3 scripts/conferir-travessao.py              # 0 limpo, 1 achou
    python3 scripts/conferir-travessao.py --autoteste  # prova o guard nos 2 sentidos
"""

from __future__ import annotations

import fnmatch
import os
import re
import sys

# Escritos como escape de proposito: se o caractere aparecesse literal aqui,
# este arquivo seria o primeiro a violar a propria regra e o expurgo o
# corromperia. Ja aconteceu.
PROIBIDOS = {
    "\u2014": "em-dash",
    "\u2013": "en-dash",
    "\u2015": "barra horizontal",
}

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXTENSOES = {
    ".md",
    ".txt",
    ".py",
    ".sh",
    ".sql",
    ".yml",
    ".yaml",
    ".html",
    ".kt",
    ".kts",
    ".swift",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".conf",
    ".css",
    ".service",
    ".timer",
    ".path",
    ".toml",
    ".tmpl",
    ".tpl",
    ".xml",
    ".c",
    ".h",
    ".ini",
    ".cfg",
    ".http",
    ".jsonl",
    ".mermaid",
    ".alloy",
    ".pro",
    ".gradle",
    ".properties",
    ".j2",
    ".svg",
    ".editorconfig",
    ".env",
}

DIRS_FORA = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".gradle",
    ".idea",
    ".next",
}

# LICENSE fica de fora em TODOS os repos, de proposito: documento legal
# padronizado, identico na casa inteira. Reescrever so aqui criaria drift
# juridico entre repos. Expurgo ali, se um dia houver, e passada propria.
FORA_SEMPRE = ("LICENSE", "LICENSE.txt", "LICENSE.md", "NOTICE")


SEM_EXT_OK = {"Dockerfile", "Makefile", "CODEOWNERS", ".editorconfig", ".env"}

# Literal de string sem letra nem digito, ou classe de regex: e' um CONJUNTO DE
# CARACTERES, nao uma frase. Trocar o travessao ali muda comportamento. Caso real:
# `cut.rstrip(" .,;:<em><en>")` corta pontuacao do fim de titulo de produto e de
# materia, que sao texto de TERCEIRO e continuam trazendo o caractere. Reescrever
# quebrou o corte e o ruff acusou B005.
_RE_LITERAL = re.compile(r"""(?:[rbfu]{0,2})(['"])((?:\\.|(?!\1).)*)\1""")


def _conjunto_de_caracteres(corpo: str) -> bool:
    if not any(c in corpo for c in PROIBIDOS):
        return False
    if not any(c.isalnum() for c in corpo):
        return True
    classe = "[" + "".join(PROIBIDOS) + "]"
    return bool(re.search(r"\[[^\]]*" + classe + r"[^\]]*\]", corpo))


def _tirar_conjuntos(linha: str) -> str:
    for m in _RE_LITERAL.finditer(linha):
        if _conjunto_de_caracteres(m.group(2)):
            linha = linha.replace(m.group(0), "")
    return linha


def _tem_shebang(caminho: str) -> bool:
    """Script sem extensao tambem entra: `scripts/vw-sync-secrets` e texto nosso."""
    try:
        with open(caminho, "rb") as fh:
            return fh.read(2) == b"#!"
    except OSError:
        return False


def _ler_config(nome: str) -> list[str]:
    caminho = os.path.join(RAIZ, nome)
    if not os.path.isfile(caminho):
        return []
    linhas = []
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.rstrip("\n")
            if not linha.strip() or linha.lstrip().startswith("#"):
                continue
            linhas.append(linha)
    return linhas


def globs_ignorados() -> list[str]:
    return [linha.strip() for linha in _ler_config(".travessao-ignore")]


def literais_permitidos() -> list[str]:
    """Identificadores de sistema externo. Vem com o caractere literal, de
    proposito: o arquivo de excecao e o unico lugar do repo onde ele pode
    aparecer, e e por isso que ele mesmo entra em `FORA_SEMPRE` implicito."""
    return [linha.strip() for linha in _ler_config(".travessao-permitido")]


def _e_texto_nosso(nome: str, ext: str, caminho: str) -> bool:
    """Extensao conhecida, nome dispensado de extensao, ou script com shebang."""
    if ext in EXTENSOES or nome in SEM_EXT_OK:
        return True
    return not ext and _tem_shebang(caminho)


def arquivos() -> list[str]:
    ignorados = globs_ignorados()
    achados = []
    for base, dirs, files in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in DIRS_FORA]
        for f in files:
            caminho = os.path.join(base, f)
            rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
            if f in FORA_SEMPRE or rel in (".travessao-permitido", ".travessao-ignore"):
                continue
            ext = os.path.splitext(f)[1].lower()
            if not _e_texto_nosso(f, ext, caminho):
                continue
            if any(fnmatch.fnmatch(rel, g) for g in ignorados):
                continue
            achados.append(caminho)
    return sorted(achados)


def _mascarar(linha: str, permitidos: list[str]) -> str:
    """Some com o que nao e prosa antes de procurar: identificador externo e
    conjunto de caracteres."""
    for literal in permitidos:
        if literal and literal in linha:
            linha = linha.replace(literal, "")
    return _tirar_conjuntos(linha)


def ocorrencias() -> list[str]:
    permitidos = literais_permitidos()
    achados = []
    for caminho in arquivos():
        try:
            with open(caminho, encoding="utf-8") as fh:
                texto = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        if not any(c in texto for c in PROIBIDOS):
            continue
        rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
        for n, linha in enumerate(texto.split("\n"), 1):
            limpa = _mascarar(linha, permitidos)
            for char, nome in PROIBIDOS.items():
                if char in limpa:
                    achados.append(f"{rel}:{n} ({nome}): {linha.strip()[:110]}")
                    break
    return achados


def autoteste() -> int:
    """Um guard so vale se for provado nos DOIS sentidos.

    Resultado vazio nao prova nada: pode ser filtro de extensao errado, lista de
    arquivos vazia ou padrao que nao casa. Aqui o guard tem de ACUSAR um
    travessao plantado e ABSOLVER um identificador externo declarado.
    """
    falhas = []

    lista = arquivos()
    if len(lista) < 3:
        falhas.append(f"varreu so {len(lista)} arquivo(s): o filtro esta errado")

    for char, nome in PROIBIDOS.items():
        if char not in _mascarar(f"texto {char} texto", []):
            falhas.append(f"nao detectaria {nome} plantado")

    conjunto = 'x.rstrip(" .,;:' + list(PROIBIDOS)[0] + '")'
    if any(c in _mascarar(conjunto, []) for c in PROIBIDOS):
        falhas.append("conjunto de caracteres nao foi dispensado")
    sujo_conjunto = conjunto + "  # nota " + list(PROIBIDOS)[0] + " aqui e prosa"
    if not any(c in _mascarar(sujo_conjunto, []) for c in PROIBIDOS):
        falhas.append("dispensar o conjunto escondeu um travessao real na mesma linha")

    permitidos = literais_permitidos()
    if permitidos:
        alvo = permitidos[0]
        if any(c in _mascarar(f"prefixo {alvo} sufixo", permitidos) for c in PROIBIDOS):
            falhas.append("literal permitido nao foi mascarado")
        sujo = f"prefixo {alvo} sufixo " + list(PROIBIDOS)[0] + " texto novo"
        if not any(c in _mascarar(sujo, permitidos) for c in PROIBIDOS):
            falhas.append("mascarar o permitido escondeu um travessao real")

    if falhas:
        for f in falhas:
            print(f"AUTOTESTE FALHOU: {f}", file=sys.stderr)
        return 1
    print(f"autoteste OK: {len(lista)} arquivo(s), deteccao e excecao provadas")
    return 0


def main() -> int:
    if "--autoteste" in sys.argv:
        return autoteste()
    achados = ocorrencias()
    if not achados:
        print(f"OK: nenhum travessao em {len(arquivos())} arquivo(s) do escopo")
        return 0
    print(f"ERRO: travessao em {len(achados)} lugar(es).", file=sys.stderr)
    print(
        "Troque pela pontuacao do CONTEXTO, nunca por um caractere fixo: "
        "':' em termo/descricao, ',' ou '.' em fronteira de oracao, "
        "middot em separador de titulo, hifen em faixa numerica.",
        file=sys.stderr,
    )
    for a in achados[:40]:
        print(f"    {a}", file=sys.stderr)
    if len(achados) > 40:
        print(f"    ... e mais {len(achados) - 40}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
