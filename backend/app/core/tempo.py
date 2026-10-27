from datetime import UTC, datetime


def agora_utc() -> datetime:
    """Data e hora atuais em UTC, sem fuso (o DATETIME do MySQL não armazena fuso)."""
    return datetime.now(UTC).replace(tzinfo=None)
