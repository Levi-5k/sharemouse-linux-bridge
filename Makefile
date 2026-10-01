ifeq ($(origin CC), default)
CC := i686-w64-mingw32-gcc
endif
PYTHON ?= python3
CFLAGS ?= -O2 -Wall -Wextra
BUILD_DIR := build

.PHONY: all clean test install

all: $(BUILD_DIR)/sm_x11_hook.dll $(BUILD_DIR)/inject_hook.exe

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/sm_x11_hook.dll: src/sm_x11_hook.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -shared -s -static-libgcc -o $@ $< -lws2_32

$(BUILD_DIR)/inject_hook.exe: src/inject_hook.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -s -static-libgcc -o $@ $<

test:
	$(PYTHON) -m py_compile src/native_bridge.py
	bash -n scripts/sharemouse-linux-bridge scripts/sharemouse-watchdog scripts/capture-runtime scripts/install.sh
	grep -q 'SMXI_HEALTH' src/native_bridge.py

install: all test
	./scripts/install.sh

clean:
	rm -rf $(BUILD_DIR) src/__pycache__
