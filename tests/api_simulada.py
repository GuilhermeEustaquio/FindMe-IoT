"""Servidor HTTP de bancada. O arquivo informado contém a contagem simulada."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys


class FindMeSimulado(BaseHTTPRequestHandler):
    def responder(self, status, dados):
        corpo = json.dumps(dados).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_POST(self):
        if self.path != "/api/auth/login":
            self.responder(404, {})
            return
        credenciais = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if credenciais.get("email") == "teste@findme.example" and credenciais.get("senha") == "teste-local":
            self.responder(200, {"token": "token-ficticio"})
        else:
            self.responder(401, {})

    def do_GET(self):
        if self.path != "/api/alertas?page=0&sizePage=1":
            self.responder(404, {})
        elif self.headers.get("Authorization") != "Bearer token-ficticio":
            self.responder(401, {})
        else:
            try:
                total = int(self.server.arquivo_contagem.read_text())
            except (OSError, ValueError):
                self.responder(503, {})
                return
            self.responder(200, {"content": [], "totalElements": total})


if __name__ == "__main__":
    servidor = ThreadingHTTPServer(("127.0.0.1", 8081), FindMeSimulado)
    servidor.arquivo_contagem = Path(sys.argv[1])
    print("API simulada em http://127.0.0.1:8081", flush=True)
    servidor.serve_forever()
