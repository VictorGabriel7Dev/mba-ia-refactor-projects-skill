"""Derivação e verificação de senha.

Substitui `hashlib.md5(pwd).hexdigest()` sem salt, que estava no modelo de usuário:
MD5 é quebrado para senha, e sem salt duas contas com a mesma senha têm o mesmo
digest, o que entrega o grupo inteiro numa tabela arco-íris.
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
    if not guardada or not str(guardada).startswith("scrypt$"):
        return False
    try:
        _, salt_hex, hash_hex = guardada.split("$", 2)
        derivada = hashlib.scrypt(senha.encode("utf-8"), salt=bytes.fromhex(salt_hex),
                                  n=_N, r=_R, p=_P, dklen=_TAM)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derivada, bytes.fromhex(hash_hex))
