"""Hora atual em UTC, sem a API deprecada.

`datetime.utcnow()` está deprecada desde o Python 3.12 e devolve um datetime
**ingênuo** (sem fuso). O substituto recomendado é `datetime.now(timezone.utc)`,
que devolve um datetime **consciente**.

Trocar direto quebraria a aplicação, e este é o ponto sutil: as colunas
`db.DateTime` do SQLite guardam datetime ingênuo. Se os novos valores passarem a
ser conscientes, qualquer comparação com um valor lido do banco levanta
`TypeError: can't compare offset-naive and offset-aware datetimes`, e o campo
`overdue` (que compara `due_date` com agora) quebra em toda rota.

Por isso a função devolve UTC **normalizado para ingênuo**: sai a chamada
deprecada, entra a recomendada, e o formato de armazenamento continua o mesmo.
Migrar as colunas para `DateTime(timezone=True)` é o passo seguinte, e está
declarado como pendência no relatório em vez de feito pela metade.
"""
from datetime import datetime, timezone


def agora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
