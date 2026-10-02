# Setup

## 1. Requirements

You need all of the following before this bridge can work:

- An Xorg/X11 desktop with the XTEST extension
- Native ARM64 `libX11.so.6` and `libXtst.so.6`
- Python 3.10 or newer
- A working Box64 installation
- A Wine x86_64 WoW64 build capable of running 32-bit Windows executables
- A user-supplied ShareMouse portable installation
- A Wine prefix in which ShareMouse can discover peers and listen on UDP 1046 / TCP 6555
- MinGW i686 compiler tools to build the hook and injector

Example build dependencies on Ubuntu 22.04:

```bash
sudo apt install gcc-mingw-w64-i686 python3 libx11-6 libxtst6 zstd x11-utils
```

Confirm XTEST:

```bash
DISPLAY=:0.0 xdpyinfo | grep XTEST
```

## 2. Build and install the bridge

```bash
git clone https://github.com/Levi-5k/sharemouse-linux-bridge.git
cd sharemouse-linux-bridge
make
make test
./scripts/install.sh
```

The build creates a 32-bit DLL and injector locally. Compiled `.dll` and `.exe` files are intentionally not committed.

## 3. Configure runtime paths

Edit:

```text
~/.config/sharemouse-linux-bridge/config.env
```

The default layout matches the tested Orange Pi deployment:

```text
/tmp/box64-root
/tmp/sharemouse-wine
/tmp/sharemouse-portable/ShareMouse
/tmp/orangepi-sharemouse/prefix
```

If Box64, Wine, ShareMouse, and the prefix are stored persistently elsewhere, override `BOX64_ROOT`, `WINE_ROOT`, `APP_ROOT`, `WORK_ROOT`, and `PREFIX`. When all configured runtime files exist, no archives are needed.

## 4. Optional RAM-backed runtime mode

For systems where the compatibility runtime lives in `/tmp`, first start and validate the complete local setup manually. Then run:

```bash
sharemouse-capture-runtime
```

This creates private archives under:

```text
~/.local/share/sharemouse-linux/
```

The launcher restores those archives after reboot. Never publish them; they contain third-party binaries and may include machine-specific state.

Expected archive members are:

```text
sharemouse-static.tar.zst
  box64-root/
  sharemouse-wine/
  sharemouse-portable/

sharemouse-prefix.tar.zst
  orangepi-sharemouse/prefix/
```

## 5. Enable supervision

The installer enables the service. Start it after the runtime is ready:

```bash
systemctl --user daemon-reload
systemctl --user enable --now sharemouse-watchdog.service
```

A graphical login and working X display are required. The first startup can take several minutes.

## 6. Validate

```bash
sharemouse-linux-bridge health
sharemouse-linux-bridge status
systemctl --user status sharemouse-watchdog.service
ss -ltnup | grep -E ':(1046|6555|48655)\b'
```

A healthy stack has exactly one `sharemouse.exe`, one native bridge, ShareMouse listeners with non-saturated queues on 1046/6555, a loopback listener on 48655, no visible ShareMouse application-error dialog, and the hook mapped into `sharemouse.exe`.

## 7. Troubleshooting

```bash
tail -f ~/.local/state/sharemouse-linux-bridge/watchdog.log
sharemouse-linux-bridge repair
```

If Wine is present but input does not cross into native applications, check that the hook is active:

```bash
sharemouse-linux-bridge status
```

If `/tmp` restoration fails, verify free RAM-backed storage and archive integrity:

```bash
df -h /tmp
zstd -t ~/.local/share/sharemouse-linux/*.zst
```

Keep adequate free space on the root filesystem. A full filesystem can prevent Wine and the watchdog from recovering cleanly.
