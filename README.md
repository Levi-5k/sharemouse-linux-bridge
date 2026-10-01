# ShareMouse Linux Bridge

An experimental X11 interoperability bridge that lets a Windows ShareMouse client control native Linux applications when ShareMouse itself is running under Box64 and Wine.

> [!IMPORTANT]
> This is an unofficial community project. It is not affiliated with, endorsed by, or supported by Bartels Media GmbH. ShareMouse is proprietary software and is **not** included in this repository. Obtain it from its publisher and comply with its license.

## Why this exists

ShareMouse 7 can run on ARM64 Linux through Box64 and Wine, discover peers, and establish its normal encrypted sessions. Wine's injected Win32 input, however, stays inside Wine and does not reliably control native X11 applications.

This project bridges that final gap:

1. A small 32-bit DLL is loaded into the local `sharemouse.exe` process.
2. It mirrors calls to `SendInput()` and `SetCursorPos()` to a loopback-only UDP socket.
3. A native Python process converts those events into XTEST mouse and keyboard events.
4. A user-level watchdog detects crashes, missing hooks, lost listeners, duplicate processes, and frozen bridges, then repairs the stack automatically.

No ShareMouse network encryption is bypassed or reimplemented.

## Tested configuration

- Orange Pi ARM64
- Ubuntu 22.04 / XFCE / Xorg
- ShareMouse 7.0.27 (32-bit portable build)
- Box64 0.4.5
- Wine 11.16 WoW64
- Native `libX11` and `libXtst`

Other versions may require changes. Wayland is not supported.

## Repository contents

- `src/native_bridge.py` — loopback receiver and XTEST injector
- `src/sm_x11_hook.c` — Win32 input API hook DLL
- `src/inject_hook.c` — local DLL loader for `sharemouse.exe`
- `scripts/sharemouse-linux-bridge` — lifecycle and health manager
- `scripts/sharemouse-watchdog` — continuous self-healing watchdog
- `systemd/sharemouse-watchdog.service` — user service
- `scripts/capture-runtime` — local-only runtime archiver

## Quick start

See [docs/SETUP.md](docs/SETUP.md) for the full prerequisites and runtime layout.

```bash
sudo apt install gcc-mingw-w64-i686 python3 libx11-6 libxtst6 zstd x11-utils
make
make test
./scripts/install.sh
```

The installer does not download or redistribute ShareMouse, Wine, or Box64. Configure paths in:

```text
~/.config/sharemouse-linux-bridge/config.env
```

Check the supervised stack with:

```bash
sharemouse-linux-bridge health
systemctl --user status sharemouse-watchdog.service
```

Recovery history is stored in:

```text
~/.local/state/sharemouse-linux-bridge/watchdog.log
```

## Security model

The bridge binds only to `127.0.0.1:48655` and accepts fixed-size packets with a protocol magic/version. The hook sends only input event fields to that loopback socket. See [SECURITY.md](SECURITY.md) before use: this project intentionally performs local DLL injection and Win32 import-table patching, which security products may flag.

## Runtime archives

The optional archive mode restores a tested runtime into RAM-backed `/tmp` after login. These archives may contain proprietary binaries, machine identifiers, peer addresses, layouts, and Wine state. They are ignored by Git and must never be committed or redistributed.

## Limitations

- X11/Xorg only
- Intended for a trusted single-user desktop
- Clipboard and drag-and-drop are not bridged
- Advanced/media key coverage may vary by keyboard layout
- Startup can take one to three minutes on small ARM boards
- Box64/Wine/ShareMouse combinations are unsupported by their upstream vendors

## License

The original source in this repository is available under the MIT License. That license does not apply to ShareMouse, Wine, Box64, or other third-party software.
