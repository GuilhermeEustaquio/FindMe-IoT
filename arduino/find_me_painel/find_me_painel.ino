#include <string.h>

const byte PINO_BOTAO = 2;
const unsigned long DEBOUNCE_MS = 40;
const unsigned long ESPERA_MS = 10000;
const unsigned long VALIDADE_MS = 30000;

enum Estado { INICIAL, AGUARDA, ATIVO, LIVRE, FALHA };
Estado estado = INICIAL;
unsigned long mudouEstado = 0;
unsigned long mudouBotao = 0;
bool leituraAnterior = HIGH;
bool botaoEstavel = HIGH;
char resposta[16];
byte tamanho = 0;
bool descartarLinha = false;

void mudarEstado(Estado novo, unsigned long agora) {
  estado = novo;
  mudouEstado = agora;
}

void lerResposta(unsigned long agora) {
  while (Serial.available() > 0) {
    char caractere = static_cast<char>(Serial.read());
    if (caractere == '\r') continue;
    if (caractere == '\n') {
      if (!descartarLinha && estado == AGUARDA) {
        resposta[tamanho] = '\0';
        if (strcmp(resposta, "ATIVO") == 0) mudarEstado(ATIVO, agora);
        else if (strcmp(resposta, "LIVRE") == 0) mudarEstado(LIVRE, agora);
        else if (strcmp(resposta, "FALHA") == 0) mudarEstado(FALHA, agora);
      }
      tamanho = 0;
      descartarLinha = false;
    } else if (tamanho < sizeof(resposta) - 1 && !descartarLinha) {
      resposta[tamanho++] = caractere;
    } else {
      descartarLinha = true;
    }
  }
}

void lerBotao(unsigned long agora) {
  bool leitura = digitalRead(PINO_BOTAO);
  if (leitura != leituraAnterior) {
    leituraAnterior = leitura;
    mudouBotao = agora;
  }
  if (leitura != botaoEstavel && agora - mudouBotao >= DEBOUNCE_MS) {
    botaoEstavel = leitura;
    if (botaoEstavel == LOW && estado != AGUARDA) {
      Serial.println(F("CONSULTAR"));
      mudarEstado(AGUARDA, agora);
    }
  }
}

void setup() {
  pinMode(PINO_BOTAO, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  unsigned long agora = millis();
  if (estado == AGUARDA && agora - mudouEstado >= ESPERA_MS) mudarEstado(FALHA, agora);
  if ((estado == ATIVO || estado == LIVRE) && agora - mudouEstado >= VALIDADE_MS) {
    mudarEstado(INICIAL, agora);
  }
  lerResposta(agora);
  lerBotao(agora);

  unsigned long duracao = agora - mudouEstado;
  bool ligar = estado == ATIVO ||
      ((estado == INICIAL || estado == AGUARDA) && duracao % 1000 < 180) ||
      (estado == FALHA && duracao % 250 < 125);
  digitalWrite(LED_BUILTIN, ligar ? HIGH : LOW);
}
