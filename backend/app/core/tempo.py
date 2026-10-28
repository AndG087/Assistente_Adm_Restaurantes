from datetime import UTC, date, datetime


def agora_utc() -> datetime:
    """Data e hora atuais em UTC, sem fuso (o DATETIME do MySQL não armazena fuso)."""
    return datetime.now(UTC).replace(tzinfo=None)


def hoje() -> date:
    """Data de hoje no relógio do computador (a aplicação roda localmente, no fuso do restaurante).

    Centralizada aqui para os testes poderem fixar a data.
    """
    return date.today()
