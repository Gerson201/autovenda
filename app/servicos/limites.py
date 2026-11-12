"""Freio de tentativas repetidas (força bruta no login).

Guarda as tentativas em memória, por processo. É suficiente para a loja rodar
em um único processo, que é o cenário deste projeto. Em uma implantação com
vários processos ou máquinas, a contagem precisaria ficar em armazenamento
compartilhado (Redis, Memcached ou uma tabela no banco) — a interface desta
classe foi pensada para que só a implementação precise mudar.
"""

from collections import defaultdict
from datetime import datetime, timedelta


class ControleTentativas:
    """Janela deslizante: N tentativas falhas em J minutos bloqueiam por B minutos."""

    def __init__(self, maximo=5, janela_minutos=10, bloqueio_minutos=15):
        self.maximo = maximo
        self.janela = timedelta(minutes=janela_minutos)
        self.bloqueio = timedelta(minutes=bloqueio_minutos)
        self._falhas = defaultdict(list)
        self._bloqueios = {}

    def _agora(self):
        return datetime.now()

    def segundos_de_bloqueio(self, chave):
        """Quantos segundos faltam para a chave sair do bloqueio (0 se liberada)."""
        ate = self._bloqueios.get(chave)
        if ate is None:
            return 0
        restante = (ate - self._agora()).total_seconds()
        if restante <= 0:
            self._bloqueios.pop(chave, None)
            self._falhas.pop(chave, None)
            return 0
        return int(restante) + 1

    def bloqueada(self, chave):
        return self.segundos_de_bloqueio(chave) > 0

    def registrar_falha(self, chave):
        """Conta uma tentativa falha e devolve True se a chave acabou de ser bloqueada."""
        agora = self._agora()
        recentes = [t for t in self._falhas[chave] if agora - t < self.janela]
        recentes.append(agora)
        self._falhas[chave] = recentes
        if len(recentes) >= self.maximo:
            self._bloqueios[chave] = agora + self.bloqueio
            self._falhas[chave] = []
            return True
        return False

    def registrar_sucesso(self, chave):
        self._falhas.pop(chave, None)
        self._bloqueios.pop(chave, None)

    def limpar(self):
        self._falhas.clear()
        self._bloqueios.clear()
