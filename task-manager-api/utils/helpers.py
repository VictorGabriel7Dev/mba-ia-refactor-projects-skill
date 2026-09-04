"""Utilitários de formatação e validação.

Limpeza feita aqui, todas apontadas pela auditoria:

- `datetime.utcnow()` (deprecada desde o Python 3.12) trocada por `utils.tempo.agora_utc`
- `type(tags) == list` virou `isinstance`, que não quebra com subclasse de list
- `MIN_PASSWORD_LENGTH = 4` saiu daqui: a política agora é `config.constants.SENHA_MIN`
- imports sem uso removidos (`os`, `json`, `sys`, `math`, `hashlib`)
- `except:` nu de `parse_date` passou a capturar `ValueError`/`TypeError`
"""
import re
from datetime import datetime

from config.constants import (COR_PADRAO, FORMATOS_DATA, PRIORIDADE_MAX, PRIORIDADE_MIN,
                              STATUS_VALIDOS, TITULO_MAX, TITULO_MIN)
from utils.tempo import agora_utc

_EMAIL = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')


def format_date(date_obj):
    return str(date_obj) if date_obj else None


def calculate_percentage(part, total):
    return 0 if not total else round((part / total) * 100, 2)


def validate_email(email):
    return bool(_EMAIL.match(email or ''))


def sanitize_string(s):
    return s.strip() if s else s


def log_action(action, details=None):
    print(f"[{agora_utc()}] ACTION: {action}")
    if details:
        print(f"  DETAILS: {details}")


def parse_date(date_string):
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(date_string, formato)
        except (TypeError, ValueError):
            continue
    return None


def is_valid_color(color):
    return bool(color) and len(color) == 7 and color[0] == '#'


def process_task_data(data, existing_task=None):
    """Validação em lote. Devolve (dados, erro), como antes."""
    resultado = {}

    if 'title' in data:
        titulo = (data['title'] or '').strip()
        if not titulo:
            return None, 'Título não pode ser vazio'
        if not TITULO_MIN <= len(titulo) <= TITULO_MAX:
            return None, f'Título deve ter entre {TITULO_MIN} e {TITULO_MAX} caracteres'
        resultado['title'] = titulo

    if 'description' in data:
        resultado['description'] = data['description']

    if 'status' in data:
        if data['status'] not in STATUS_VALIDOS:
            return None, 'Status inválido'
        resultado['status'] = data['status']

    if 'priority' in data:
        try:
            p = int(data['priority'])
        except (TypeError, ValueError):
            return None, 'Prioridade inválida'
        if not PRIORIDADE_MIN <= p <= PRIORIDADE_MAX:
            return None, f'Prioridade deve ser entre {PRIORIDADE_MIN} e {PRIORIDADE_MAX}'
        resultado['priority'] = p

    if 'due_date' in data:
        if data['due_date']:
            parsed = parse_date(data['due_date'])
            if not parsed:
                return None, 'Data inválida'
            resultado['due_date'] = parsed
        else:
            resultado['due_date'] = None

    if 'tags' in data:
        tags = data['tags']
        resultado['tags'] = ','.join(tags) if isinstance(tags, list) else tags

    return resultado, None


DEFAULT_COLOR = COR_PADRAO
