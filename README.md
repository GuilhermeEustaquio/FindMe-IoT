# Find Me | Painel comunitário de alertas

**FIAP · Global Solution 2026/2 · Disruptive Architectures: IoT, IoB & Generative IA**

Em um ponto comunitário, o cidadão pode apertar um botão para consultar se há alertas ativos de desaparecimento de crianças e adolescentes. O Arduino Uno mostra o resultado com o LED embutido da placa. O painel sinaliza a disponibilidade de alertas autorizados. Para ver a divulgação, o cidadão consulta o Find Me. Para casos reais, os canais oficiais permanecem a referência para registrar o desaparecimento e encaminhar informações.

## Integrantes

| Nome | RM | Turma |
| --- | --- | --- |
| Caio Cantini Couto | informado no Portal FIAP | 2TDSPS |
| Guilherme Pinto Eustáquio | informado no Portal FIAP | 2TDSPS |
| Matheus Tavares | informado no Portal FIAP | 2TDSPS |

## Arquitetura e comunicação

[Diagrama em Mermaid](docs/arquitetura.mmd)

```mermaid
flowchart TB
    B["Botão em ponto comunitário"] -->|D2 e GND| A["Arduino Uno"]
    A -->|D13 interno| L["LED visível ao cidadão"]
    A <-->|USB serial a 9600 bps| G["Computador com gateway Python"]
    G <-->|Wi-Fi ou Ethernet| R["Roteador ou ponto de acesso"]
    R <-->|TCP/IP e HTTP(S)| J["API Find Me em Spring Boot"]
    J --> H[("H2 da API Java")]
```

1. O firmware usa `INPUT_PULLUP` e debounce de 40 ms para reconhecer um único acionamento. O Arduino emite `CONSULTAR` por serial USB.
2. O gateway autentica uma conta `COLABORADOR` pelo endpoint `POST /api/auth/login`. Consulta `GET /api/alertas?page=0&sizePage=1` com o JWT e usa o campo paginado `totalElements`. Se a API responder 401, tenta renovar o token uma vez.
3. O gateway retorna `ATIVO`, `LIVRE` ou `FALHA`. O Arduino aciona o LED D13 com base no estado. Nomes, descrições e outros campos do retorno HTTP ficam fora do protocolo serial e dos logs do painel.
4. No laboratório, a API pode rodar no mesmo computador em `127.0.0.1`. Entre máquinas, configure a URL da API acessível pela rede do laboratório. A arquitetura usa o computador como gateway para manter o Uno com hardware simples e a autenticação fora da placa. Para um ponto comunitário em rede, use HTTPS e credenciais dedicadas.

| LED L (D13) | Estado |
| --- | --- |
| Pulso breve a cada 1 s | Consulta em andamento ou leitura ainda indisponível/expirada |
| Aceso contínuo | Existe ao menos um alerta ativo |
| Apagado | A API respondeu com zero alertas ativos |
| Pisca rápido, 4 ciclos/s | Falha no gateway/API ou ausência de resposta em 10 s |

Uma leitura bem-sucedida fica visível por 30 s e, depois, o LED volta a pulsar lentamente até nova consulta. A falha tem sinal próprio para que indisponibilidade e zero alertas sejam distinguíveis. A contagem cobre o feed da API inteira. O painel não geolocaliza casos.

## Montagem e teste do circuito

| Componente | Ligação |
| --- | --- |
| Botão momentâneo | Um contato no pino D2, o outro no GND do Uno |
| LED L embutido no Uno | Controlado pelo pino D13, sem ligação externa |
| Cabo USB de dados | Uno para o computador do gateway. Transporta alimentação e serial |
| Computador e roteador | Gateway e servidor na mesma rede quando em máquinas distintas |

Use terminais de contatos opostos do botão. Abra `arduino/find_me_painel/find_me_painel.ino` na Arduino IDE, selecione **Arduino Uno** e a porta da placa, envie o sketch e feche o Monitor Serial antes de iniciar o gateway.

Também é possível testar só o circuito no Wokwi. Crie um projeto Arduino Uno, substitua o sketch e o `diagram.json` pelos arquivos da pasta `arduino/find_me_painel/` e inicie. Clique no botão ou pressione **C**. O Monitor Serial recebe `CONSULTAR`. Digite `ATIVO`, `LIVRE` ou `FALHA` e envie com a opção de nova linha dentro de dez segundos. Esse teste injeta a resposta manualmente. Para testar o gateway e o HTTP no simulador, use os testes de integração abaixo.

[Referência do circuito Arduino Uno no Wokwi](https://docs.wokwi.com/parts/wokwi-arduino-uno) · [Referência do botão](https://docs.wokwi.com/parts/wokwi-pushbutton)

## Executar com a API da equipe

1. Inicie o [projeto Java Find Me](https://github.com/caioccouto/FindMe-GlobalSolution) com **JDK 21** usando `mvnw.cmd spring-boot:run` no Windows ou `bash mvnw spring-boot:run` no Linux. Para a apresentação, use uma base H2 de testes com casos fictícios.
2. Na pasta deste projeto, instale a dependência usando `python -m pip install -r requirements.txt` com Python 3.10 ou posterior.
3. Configure as variáveis abaixo. Use o e-mail e a senha de demonstração de um **colaborador**. Os valores podem ser consultados na seção de teste do README da API Java. O gateway lê variáveis de ambiente, conforme `.env.example`.

```powershell
$env:FINDME_SERIAL_PORT = 'COM3'
$env:FINDME_BASE_URL = 'http://127.0.0.1:8080'
$env:FINDME_EMAIL = 'EMAIL_DE_TESTE'
$env:FINDME_SENHA = 'SENHA_DE_TESTE'
python gateway.py
```

No Linux, use `export FINDME_SERIAL_PORT=/dev/ttyACM0` e defina as outras variáveis com `export`. O gateway indica quando a porta está pronta.

4. Pressione o botão com o feed vazio. Crie um caso fictício como responsável, valide e publique o alerta como moderador e pressione de novo. Marque o caso como `LOCALIZADO` e repita. Os três resultados esperados são LED apagado, aceso e apagado, nessa ordem.

### Testes em simulação

No Linux com ferramentas AVR, core Arduino e simavr instalados, execute:

```bash
# Debian: gcc, gcc-avr, binutils-avr, avr-libc, arduino-core-avr e libsimavr-dev
bash tests/compilar_uno.sh

# Primeiro terminal
printf '0' > /tmp/findme-contagem.txt
python tests/api_simulada.py /tmp/findme-contagem.txt

# Segundo terminal
python tests/verificar_iot.py --simulada /tmp/findme-contagem.txt
```

O teste usa o firmware AVR compilado, injeta cliques no pino D2 emulado e lê os estados do pino D13 e da UART. Também usa a consulta HTTP do gateway. A API simulada fornece apenas dados fictícios e fica restrita ao endereço local. Para testar com a API Java, use uma base H2 de teste **vazia**, defina as variáveis do gateway e também `TESTE_RESPONSAVEL_EMAIL`, `TESTE_RESPONSAVEL_SENHA`, `TESTE_MODERADOR_EMAIL` e `TESTE_MODERADOR_SENHA`. Rode `python tests/verificar_iot.py`. Essa execução cria, publica e marca como localizado um caso fictício.

## Testes e evidências

| Caso | Critério |
| --- | --- |
| I01 · Debounce | Um pulso de 15 ms é ignorado. Pressionar e segurar gera apenas uma consulta |
| I02 · Feed vazio | Resposta `LIVRE` e LED apagado |
| I03 · Publicação | Resposta `ATIVO` e LED aceso continuamente |
| I04 · Localização | Caso sai do feed. Resposta `LIVRE` e LED apagado |
| I05 · Falha no HTTP | Resposta `FALHA` e seis transições de LED em 750 ms emulados |
| I06 · Ausência de resposta serial | Firmware sinaliza falha após o limite de 10 s emulados |
| I07 · Recuperação e validade | Novo resultado chega e a leitura expira após 30 s emulados |

Os sete cenários passaram com a API Java da equipe e também com a API simulada. Um teste separado abriu uma porta serial virtual com PySerial e passou os quatro cenários de troca de mensagens. Os resultados estão nos [logs de execução](evidencias/). Para repetir o teste da porta virtual (Linux, dependência instalada e porta TCP 8081 livre), execute `python tests/verificar_gateway_serial.py`. A montagem física ainda precisa ser executada para avaliar contato do botão, cabo e comportamento na rede do local.

## Uso de IA generativa

ChatGPT foi utilizado no desenvolvimento do firmware, do gateway, dos testes e da documentação.

## Envio à FIAP

No Portal do Aluno envie apenas o TXT de entrega fornecido à equipe, com os integrantes, os RMs, a turma e o link do projeto. Os RMs foram omitidos da versão pública de identificacao.txt.
