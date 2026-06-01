"""Exceções do domínio."""


class OlxError(Exception):
    """Erro base."""


class OlxFetchError(OlxError):
    """Falha HTTP ou rede."""


class OlxParseError(OlxError):
    """HTML/JSON inesperado — possível mudança no site."""


class OlxRateLimitError(OlxFetchError):
    """HTTP 429 ou bloqueio temporário."""


class OlxAuthError(OlxError):
    """Falha de autenticação OAuth ou sessão OLX."""
