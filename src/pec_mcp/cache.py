"""
Camada simples de cache em memória com TTL para dimensões estáticas.
Evita round-trips repetitivos ao PostgreSQL para tabelas pequenas e imutáveis.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, Dict, Tuple

_CACHE: Dict[Tuple[str, str], Tuple[Any, float]] = {}


def cached_dimension(ttl_seconds: int = 3600) -> Callable:
    """
    Decorador para cachear resultados de consultas de dimensão em memória.
    O cache é invalidado automaticamente após ttl_seconds (padrão: 1 hora).
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Não incluir o Context na chave de cache para permitir reuso entre requests
            cache_args = tuple(repr(a) for a in args[1:]) if len(args) > 1 else ()
            cache_kwargs = tuple(sorted((k, repr(v)) for k, v in kwargs.items()))
            key = (func.__name__, str((cache_args, cache_kwargs)))

            now = time.time()
            if key in _CACHE:
                cached_val, timestamp = _CACHE[key]
                if now - timestamp < ttl_seconds:
                    return cached_val

            result = func(*args, **kwargs)
            _CACHE[key] = (result, now)
            return result

        def clear_func_cache() -> None:
            prefix = func.__name__
            keys_to_del = [k for k in _CACHE if k[0] == prefix]
            for k in keys_to_del:
                _CACHE.pop(k, None)

        wrapper.clear_cache = clear_func_cache
        return wrapper

    return decorator


def clear_dimension_cache() -> None:
    """Limpa todo o cache em memória."""
    _CACHE.clear()
