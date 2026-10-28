"""Limite de tentativas por chave (e-mail ou IP) numa janela de tempo, guardado em memória.

Suficiente para um sistema que roda num único processo local. Ao reiniciar o backend, a contagem zera.
"""

import threading
import time
from collections import defaultdict, deque


class LimiteTentativas:
    def __init__(self, maximo: int, janela_segundos: float) -> None:
        self.maximo = maximo
        self.janela = janela_segundos
        self._tentativas: dict[str, deque[float]] = defaultdict(deque)
        self._trava = threading.Lock()

    def _descartar_antigas(self, chave: str, agora: float) -> deque[float]:
        fila = self._tentativas[chave]
        while fila and fila[0] <= agora - self.janela:
            fila.popleft()
        return fila

    def segundos_bloqueado(self, *chaves: str) -> int:
        """0 se todas as chaves podem tentar; senão, quantos segundos faltam para liberar."""
        agora = time.monotonic()
        with self._trava:
            espera = 0.0
            for chave in chaves:
                fila = self._descartar_antigas(chave, agora)
                if len(fila) >= self.maximo:
                    espera = max(espera, fila[0] + self.janela - agora)
        return int(espera) + 1 if espera > 0 else 0

    def registrar(self, *chaves: str) -> None:
        agora = time.monotonic()
        with self._trava:
            for chave in chaves:
                self._descartar_antigas(chave, agora).append(agora)

    def limpar(self, *chaves: str) -> None:
        """Sem chaves, zera tudo (usado nos testes)."""
        with self._trava:
            if not chaves:
                self._tentativas.clear()
            for chave in chaves:
                self._tentativas.pop(chave, None)
