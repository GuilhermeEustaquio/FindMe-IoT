"""Exercita GPIO, UART emulada e consultas de rede usando o firmware compilado."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gateway import ApiFindMe, consultar


class Arduino:
    def __enter__(self):
        self.proc = subprocess.Popen(
            [str(ROOT / "build/simular_arduino"), str(ROOT / "build/painel.elf")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        for linha in self.proc.stdout:
            if linha.strip() == "PRONTO":
                return self
        raise RuntimeError("Simulador AVR indisponivel.")

    def __exit__(self, *args):
        self.proc.stdin.close()
        self.proc.wait(timeout=5)
        self.proc.stdout.close()

    def comando(self, texto):
        print("> " + texto, end="  ", flush=True)
        self.proc.stdin.write(texto + "\n")
        self.proc.stdin.flush()
        linha = self.proc.stdout.readline().strip()
        print(linha, flush=True)
        led, mudancas, uart = (trecho.partition("=")[2] for trecho in linha.split())
        return int(led), int(mudancas), uart

    def acionar(self):
        assert self.comando("baixo 85")[2] == "CONSULTAR,"
        assert self.comando("baixo 300")[2] == ""
        assert self.comando("alto 80")[2] == ""

    def receber(self, resposta):
        return self.comando("serial 25 " + resposta.decode().strip())


def pedir(base, rota, metodo="GET", dados=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(base + rota, data=json.dumps(dados).encode() if dados is not None else None,
                  method=metodo, headers=headers)
    with urlopen(req, timeout=5) as resp:
        bruto = resp.read()
        return json.loads(bruto) if bruto else None


def preparar_caso(base):
    def entrar(prefixo):
        return pedir(base, "/api/auth/login", "POST", {
            "email": os.environ[prefixo + "_EMAIL"],
            "senha": os.environ[prefixo + "_SENHA"],
        })["token"]

    responsavel = entrar("TESTE_RESPONSAVEL")
    moderador = entrar("TESTE_MODERADOR")
    caso = pedir(base, "/api/casos", "POST", {
        "nomeDesaparecido": "Pessoa ficticia de teste", "idade": 12,
        "descricao": "Caso ficticio exclusivo do teste de integracao.",
        "ultimaLocalizacaoConhecida": "Regiao ficticia",
        "dataDesaparecimento": "2026-11-10",
    }, responsavel)
    caso_id = caso["id"]
    print(f"API criou caso ficticio {caso_id} em EM_ANALISE.")
    return moderador, caso_id


def executar(base, api, contador=None):
    with Arduino() as placa:
        print("\nI01 | Estabilizacao e debounce")
        assert placa.comando("tempo 1200")[1] >= 2
        assert placa.comando("baixo 15")[2] == ""
        assert placa.comando("alto 70")[2] == ""

        moderador = caso_id = None
        if contador:
            contador.write_text("0")
        else:
            moderador, caso_id = preparar_caso(base)

        print("\nI02 | Sem alertas ativos")
        placa.acionar()
        assert placa.receber(consultar(api))[0] == 0

        print("\nI03 | Publicacao e atualizacao do LED")
        if contador:
            contador.write_text("2")
        else:
            pedir(base, f"/api/casos/{caso_id}/status", "PATCH", {"status": "VALIDADO"}, moderador)
            pedir(base, "/api/alertas", "POST", {
                "casoId": caso_id, "titulo": "Alerta ficticio",
                "descricaoPublica": "Divulgacao autorizada para demonstracao.",
            }, moderador)
            print("API validou e publicou o alerta.")
        placa.acionar()
        assert placa.receber(consultar(api))[0] == 1
        assert placa.comando("tempo 500")[:2] == (1, 0)

        print("\nI04 | Localizacao e retirada do alerta")
        if contador:
            contador.write_text("0")
        else:
            pedir(base, f"/api/casos/{caso_id}/status", "PATCH", {"status": "LOCALIZADO"}, moderador)
            print("API marcou o caso como LOCALIZADO.")
        placa.acionar()
        assert placa.receber(consultar(api))[0] == 0
        assert placa.comando("tempo 500")[:2] == (0, 0)

        print("\nI05 | Falha HTTP ou de conexao")
        if contador:
            contador.unlink()
            api_falha = api
        else:
            api_falha = ApiFindMe("http://127.0.0.1:1", "teste", "teste")
        placa.acionar()
        assert placa.receber(consultar(api_falha))[0] == 1
        assert placa.comando("tempo 750")[1] >= 5

        print("\nI06 | Sem resposta serial")
        placa.acionar()
        assert placa.comando("tempo 10500")[1] >= 22

        print("\nI07 | Recuperacao e validade da leitura")
        if contador:
            contador.write_text("0")
        placa.acionar()
        assert placa.receber(consultar(api))[0] == 0
        assert placa.comando("tempo 31000")[1] >= 2
        print("\nResultado: 7 de 7 cenarios aprovados.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulada", type=Path, help="arquivo de contagem da API simulada")
    argumentos = parser.parse_args()
    if argumentos.simulada:
        base = "http://127.0.0.1:8081"
        api = ApiFindMe(base, "teste@findme.example", "teste-local")
    else:
        base = os.getenv("FINDME_BASE_URL", "http://127.0.0.1:8080")
        api = ApiFindMe(base, os.environ["FINDME_EMAIL"], os.environ["FINDME_SENHA"])
    try:
        executar(base, api, argumentos.simulada)
    except HTTPError as erro:
        print(f"Falha na API: HTTP {erro.code} em {erro.url}", file=sys.stderr)
        raise
