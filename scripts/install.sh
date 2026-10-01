#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bin_dir="$HOME/.local/bin"
lib_dir="$HOME/.local/lib/sharemouse-linux-bridge"
service_dir="$HOME/.config/systemd/user"
applications_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/sharemouse-linux-bridge"
data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/sharemouse-linux"

for command in python3 zstd tar systemctl xdpyinfo ss; do
    command -v "$command" >/dev/null || { echo "Missing required command: $command" >&2; exit 1; }
done
[[ -f "$root/build/sm_x11_hook.dll" && -f "$root/build/inject_hook.exe" ]] || {
    echo "Build artifacts are missing. Run 'make' first." >&2
    exit 1
}

mkdir -p "$bin_dir" "$lib_dir" "$service_dir" "$applications_dir" "$config_dir"
install -m 700 "$root/scripts/sharemouse-linux-bridge" "$bin_dir/sharemouse-linux-bridge"
install -m 700 "$root/scripts/sharemouse-watchdog" "$bin_dir/sharemouse-watchdog"
install -m 700 "$root/scripts/capture-runtime" "$bin_dir/sharemouse-capture-runtime"
install -m 700 "$root/src/native_bridge.py" "$lib_dir/native_bridge.py"
install -m 600 "$root/build/sm_x11_hook.dll" "$lib_dir/sm_x11_hook.dll"
install -m 700 "$root/build/inject_hook.exe" "$lib_dir/inject_hook.exe"
install -m 644 "$root/systemd/sharemouse-watchdog.service" "$service_dir/sharemouse-watchdog.service"
install -m 755 "$root/desktop/sharemouse-linux-bridge.desktop" "$applications_dir/sharemouse-linux-bridge.desktop"
[[ -e "$config_dir/config.env" ]] || install -m 600 "$root/config.env.example" "$config_dir/config.env"

systemctl --user daemon-reload
systemctl --user enable sharemouse-watchdog.service
if [[ -r "$data_dir/sharemouse-static.tar.zst" && -r "$data_dir/sharemouse-prefix.tar.zst" ]]; then
    systemctl --user restart sharemouse-watchdog.service
    echo "Installed and started the supervised bridge."
else
    echo "Installed the bridge, but runtime archives are not present."
    echo "Run $bin_dir/sharemouse-capture-runtime after preparing the local runtime, then start:"
    echo "  systemctl --user start sharemouse-watchdog.service"
fi
