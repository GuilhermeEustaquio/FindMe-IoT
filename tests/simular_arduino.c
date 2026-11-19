#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "avr_ioport.h"
#include "avr_uart.h"
#include "sim_avr.h"
#include "sim_elf.h"
#include "sim_io.h"
#include "sim_irq.h"

static char enviados[80];
static size_t tamanho;
static unsigned transicoes_led;
static int estado_led;
static int registrar_led;

static void capturar_serial(struct avr_irq_t *irq, uint32_t valor, void *param) {
    (void)irq;
    (void)param;
    if (valor == '\r') return;
    if (tamanho + 1 < sizeof enviados) {
        enviados[tamanho++] = valor == '\n' ? ',' : (char)valor;
        enviados[tamanho] = '\0';
    }
}

static void capturar_led(struct avr_irq_t *irq, uint32_t valor, void *param) {
    (void)irq;
    (void)param;
    int estado = valor & 1;
    if (registrar_led && estado != estado_led) transicoes_led++;
    estado_led = estado;
}

static void avancar(avr_t *avr, unsigned ms) {
    avr_cycle_count_t fim = avr->cycle + (avr_cycle_count_t)ms * 16000;
    while (avr->cycle < fim) {
        if (avr_run(avr) == cpu_Crashed) {
            fputs("Falha durante a simulacao AVR\n", stderr);
            exit(1);
        }
    }
}

int main(int argc, char **argv) {
    elf_firmware_t firmware = {0};
    if (argc != 2 || elf_read_firmware(argv[1], &firmware) != 0) return 2;

    avr_t *avr = avr_make_mcu_by_name("atmega328p");
    if (avr == NULL || avr_init(avr) != 0) return 2;
    avr->frequency = 16000000;
    avr_load_firmware(avr, &firmware);

    uint32_t flags = 0;
    avr_ioctl(avr, AVR_IOCTL_UART_SET_FLAGS('0'), &flags);
    avr_irq_t *botao = avr_io_getirq(avr, AVR_IOCTL_IOPORT_GETIRQ('D'), 2);
    avr_irq_t *led = avr_io_getirq(avr, AVR_IOCTL_IOPORT_GETIRQ('B'), 5);
    avr_irq_t *entrada = avr_io_getirq(avr, AVR_IOCTL_UART_GETIRQ('0'), UART_IRQ_INPUT);
    avr_irq_t *saida = avr_io_getirq(avr, AVR_IOCTL_UART_GETIRQ('0'), UART_IRQ_OUTPUT);
    avr_irq_register_notify(led, capturar_led, NULL);
    avr_irq_register_notify(saida, capturar_serial, NULL);
    avr_raise_irq(botao, 1);
    puts("PRONTO");
    fflush(stdout);

    char linha[80], comando[16], resposta[16];
    unsigned ms;
    while (fgets(linha, sizeof linha, stdin) != NULL) {
        if (sscanf(linha, "%15s %u", comando, &ms) != 2) return 2;
        tamanho = 0;
        enviados[0] = '\0';
        transicoes_led = 0;
        registrar_led = 1;
        if (strcmp(comando, "baixo") == 0) avr_raise_irq(botao, 0);
        else if (strcmp(comando, "alto") == 0) avr_raise_irq(botao, 1);
        else if (strcmp(comando, "serial") == 0) {
            if (sscanf(linha, "%*s %*u %15s", resposta) != 1) return 2;
            for (size_t i = 0; resposta[i] != '\0'; i++) {
                avr_raise_irq(entrada, (uint8_t)resposta[i]);
                avancar(avr, 2);
            }
            avr_raise_irq(entrada, '\n');
        } else if (strcmp(comando, "tempo") != 0) return 2;
        avancar(avr, ms);
        registrar_led = 0;
        printf("LED=%d MUDANCAS=%u UART=%s\n", estado_led, transicoes_led, enviados);
        fflush(stdout);
    }
    avr_terminate(avr);
    return 0;
}
