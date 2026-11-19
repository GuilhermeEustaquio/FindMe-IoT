#!/usr/bin/env bash
# Compila o firmware Arduino Uno e o simulador para testes em Linux.
set -euo pipefail
cd "$(dirname "$0")/.."
raiz="${AVR_USR:-/usr}"
core="$raiz/share/arduino/hardware/arduino/avr"
sim_lib="$raiz/lib/$(gcc -print-multiarch)"
build="$PWD/build"
mkdir -p "$build"
flags=(-Os -DF_CPU=16000000L -DARDUINO=10819 -DARDUINO_AVR_UNO
       -DARDUINO_ARCH_AVR -mmcu=atmega328p -ffunction-sections -fdata-sections
       -I"$core/cores/arduino" -I"$core/variants/standard")
objetos=()
for fonte in "$core"/cores/arduino/*.{c,cpp,S}; do
  [[ -f "$fonte" ]] || continue
  objeto="$build/$(basename "$fonte").o"
  compilador="$raiz/bin/avr-gcc"
  opcoes=()
  if [[ "$fonte" == *.cpp ]]; then
    compilador="$raiz/bin/avr-g++"
    opcoes=(-std=gnu++11 -fno-exceptions)
  fi
  "$compilador" "${flags[@]}" "${opcoes[@]}" -c "$fonte" -o "$objeto"
  objetos+=("$objeto")
done
"$raiz/bin/avr-g++" "${flags[@]}" -include Arduino.h -x c++ -std=gnu++11 -c \
  arduino/find_me_painel/find_me_painel.ino -o "$build/painel.o"
"$raiz/bin/avr-g++" -mmcu=atmega328p -Wl,--gc-sections "${objetos[@]}" "$build/painel.o" -o "$build/painel.elf"
"$raiz/bin/avr-size" "$build/painel.elf"
gcc -std=c11 -Wall -Wextra -Werror -I"$raiz/include/simavr" -L"$sim_lib" \
  -Wl,-rpath,"$sim_lib" -Wl,-rpath-link,"$sim_lib" tests/simular_arduino.c -lsimavr -o "$build/simular_arduino"
