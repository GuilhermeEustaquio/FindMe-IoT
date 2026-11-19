"""Converte a contagem de alertas ativos da API Find Me em estados seriais."""

import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ApiFindMe:
    def __init__(self, base_url, email, senha):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.senha = senha
        self.token = None
        self.http = build_opener(SemRedirecionamento())

    def _json(self, rota, body=None, token=None):
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        requisicao = Request(self.base_url + rota, data=body, headers=headers)
        with self.http.open(requisicao, timeout=2) as resultado:
            resposta = json.load(resultado)
        if not isinstance(resposta, dict):
            raise ValueError("JSON fora do contrato Find Me")
        return resposta

    def _entrar(self):
        body = json.dumps({"email": self.email, "senha": self.senha}).encode("utf-8")
        token = self._json("/api/auth/login", body=body).get("token")
        if not isinstance(token, str) or not token:
            raise ValueError("Token ausente ou invalido")
        self.token = token

    def total_ativos(self):
        if self.token is None:
            self._entrar()
        rota = "/api/alertas?page=0&sizePage=1"
        try:
            resposta = self._json(rota, token=self.token)
        except HTTPError as erro:
            if erro.code != 401:
                raise
            self.token = None
            self._entrar()
            resposta = self._json(rota, token=self.token)

        total = resposta.get("totalElements")
        if type(total) is not int or total < 0:
            raise ValueError("totalElements ausente ou invalido")
        return total


def consultar(api):
    try:
        total = api.total_ativos()
    except (URLError, OSError, ValueError) as erro:
        print(f"FALHA | {type(erro).__name__}", flush=True)
        return b"FALHA\n"

    estado = "ATIVO" if total else "LIVRE"
    print(f"{estado} | alertas ativos={total}", flush=True)
    return (estado + "\n").encode("ascii")


def main():
    import serial

    porta = os.getenv("FINDME_SERIAL_PORT")
    url = os.getenv("FINDME_BASE_URL", "http://127.0.0.1:8080")
    email = os.getenv("FINDME_EMAIL")
    senha = os.getenv("FINDME_SENHA")
    parsed = urlsplit(url)
    if not porta or not email or not senha or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        print("Configure FINDME_SERIAL_PORT, FINDME_BASE_URL, FINDME_EMAIL e FINDME_SENHA.", file=sys.stderr)
        return 2

    api = ApiFindMe(url, email, senha)
    try:
        with serial.Serial(porta, 9600, timeout=0.2, write_timeout=2) as canal:
            time.sleep(2)  # Abrir a serial pode reiniciar o Uno.
            print(f"Gateway pronto na porta {porta}. Pressione o botao.", flush=True)
            linha = bytearray()
            descartar_linha = False
            while True:
                caractere = canal.read(1)
                if not caractere or caractere == b"\r":
                    continue
                if caractere == b"\n":
                    if not descartar_linha and linha == b"CONSULTAR":
                        canal.write(consultar(api))
                    linha.clear()
                    descartar_linha = False
                elif len(linha) < 32:
                    linha.extend(caractere)
                else:
                    descartar_linha = True
    except KeyboardInterrupt:
        return 0
    except serial.SerialException as erro:
        print(f"Erro serial na porta {porta}: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
