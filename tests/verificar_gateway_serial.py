"""Valida a troca de mensagens pela serial virtual em Linux, com a API de bancada."""

import os
from pathlib import Path
import pty
import select
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def aguardar_api():
    for _ in range(40):
        try:
            urlopen("http://127.0.0.1:8081/", timeout=0.25).close()
            return
        except HTTPError as erro:
            if erro.code == 404:
                return
            raise
        except URLError:
            time.sleep(0.1)
    raise RuntimeError("API de bancada nao iniciou.")


def aguardar_resposta(master, tempo):
    if not select.select([master], [], [], tempo)[0]:
        return b""
    resposta = bytearray(os.read(master, 32))
    while b"\n" not in resposta and select.select([master], [], [], tempo)[0]:
        resposta.extend(os.read(master, 32))
    return bytes(resposta)


def executar():
    with TemporaryDirectory() as pasta:
        contador = Path(pasta) / "contagem"
        contador.write_text("0")
        master, slave = pty.openpty()
        env = dict(os.environ,
                   FINDME_SERIAL_PORT=os.ttyname(slave),
                   FINDME_BASE_URL="http://127.0.0.1:8081",
                   FINDME_EMAIL="teste@findme.example", FINDME_SENHA="teste-local")
        servidor = subprocess.Popen([sys.executable, str(ROOT / "tests/api_simulada.py"), str(contador)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        gateway = None
        try:
            aguardar_api()
            gateway = subprocess.Popen([sys.executable, str(ROOT / "gateway.py")],
                                       env=env, stdout=subprocess.PIPE, text=True)
            if not select.select([gateway.stdout], [], [], 5)[0]:
                raise RuntimeError("Gateway nao abriu a serial virtual.")
            assert "Gateway pronto" in gateway.stdout.readline()

            os.write(master, b"COMANDO_INVALIDO\n")
            assert aguardar_resposta(master, 0.4) == b""
            print("Comando invalido ignorado na serial virtual.")

            for esperado in (b"LIVRE\n", b"ATIVO\n", b"FALHA\n"):
                if esperado == b"ATIVO\n":
                    contador.write_text("2")
                if esperado == b"FALHA\n":
                    contador.unlink()
                os.write(master, b"CONSULTAR\r\n")
                resposta = aguardar_resposta(master, 4)
                assert resposta == esperado, (resposta, esperado)
                print("CONSULTAR ->", resposta.decode().strip())

            print("Serial virtual: 4 de 4 cenarios aprovados.")
        finally:
            for processo in (gateway, servidor):
                if processo is not None:
                    processo.terminate()
                    processo.wait(timeout=5)
            os.close(master)
            os.close(slave)


if __name__ == "__main__":
    executar()
