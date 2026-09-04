"""Derivação e verificação de senha.

Antes a senha ia para o banco em texto plano e era conferida por igualdade dentro
da própria query SQL, o que a tornava também o vetor da injeção. Agora: scrypt,
salt por usuário, e comparação em tempo constante.
"""
import hashlib
import hmac
import os

_N, _R, _P, _TAM = 2 ** 14, 8, 1, 32


def hash_senha(senha: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    derivada = hashlib.scrypt(senha.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_TAM)
    return f"scrypt${salt.hex()}${derivada.hex()}"


def verificar_senha(senha: str, guardada: str | None) -> bool:
    if not guardada or not guardada.startswith("scrypt$"):
        return False
    try:
        _, salt_hex, hash_hex = guardada.split("$", 2)
        derivada = hashlib.scrypt(senha.encode("utf-8"), salt=bytes.fromhex(salt_hex),
                                  n=_N, r=_R, p=_P, dklen=_TAM)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derivada, bytes.fromhex(hash_hex))
