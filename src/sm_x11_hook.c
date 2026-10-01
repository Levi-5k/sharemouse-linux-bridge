// SPDX-License-Identifier: MIT
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>
#include <stdint.h>
#include <string.h>

#define BRIDGE_MAGIC 0x49584d53u /* "SMXI" in little-endian memory */
#define BRIDGE_PORT 48655

enum bridge_kind {
    BRIDGE_READY = 0,
    BRIDGE_CURSOR = 1,
    BRIDGE_MOUSE = 2,
    BRIDGE_KEYBOARD = 3
};

#pragma pack(push, 1)
struct bridge_packet {
    uint32_t magic;
    uint16_t version;
    uint16_t kind;
    int32_t a;
    int32_t b;
    uint32_t c;
    uint32_t d;
};
#pragma pack(pop)

typedef UINT (WINAPI *send_input_fn)(UINT, LPINPUT, int);
typedef BOOL (WINAPI *set_cursor_pos_fn)(int, int);

static SOCKET bridge_socket = INVALID_SOCKET;
static struct sockaddr_in bridge_address;
static send_input_fn real_SendInput;
static set_cursor_pos_fn real_SetCursorPos;

static void bridge_send(uint16_t kind, int32_t a, int32_t b, uint32_t c, uint32_t d)
{
    struct bridge_packet packet;

    if (bridge_socket == INVALID_SOCKET) return;
    packet.magic = BRIDGE_MAGIC;
    packet.version = 1;
    packet.kind = kind;
    packet.a = a;
    packet.b = b;
    packet.c = c;
    packet.d = d;
    sendto(bridge_socket, (const char *)&packet, sizeof(packet), 0,
           (const struct sockaddr *)&bridge_address, sizeof(bridge_address));
}

static UINT WINAPI hooked_SendInput(UINT count, LPINPUT inputs, int size)
{
    UINT i;

    if (inputs && size == sizeof(INPUT)) {
        for (i = 0; i < count; ++i) {
            const INPUT *input = &inputs[i];
            if (input->type == INPUT_MOUSE) {
                bridge_send(BRIDGE_MOUSE, input->mi.dx, input->mi.dy,
                            input->mi.mouseData, input->mi.dwFlags);
            } else if (input->type == INPUT_KEYBOARD) {
                bridge_send(BRIDGE_KEYBOARD,
                            (int32_t)((uint32_t)input->ki.wVk |
                                      ((uint32_t)input->ki.wScan << 16)),
                            (int32_t)input->ki.time,
                            input->ki.dwFlags, 0);
            }
        }
    }
    return real_SendInput ? real_SendInput(count, inputs, size) : 0;
}

static BOOL WINAPI hooked_SetCursorPos(int x, int y)
{
    bridge_send(BRIDGE_CURSOR, x, y, 0, 0);
    return real_SetCursorPos ? real_SetCursorPos(x, y) : TRUE;
}

static int patch_import(HMODULE module, FARPROC target, FARPROC replacement)
{
    IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)module;
    IMAGE_NT_HEADERS *nt;
    IMAGE_IMPORT_DESCRIPTOR *imports;
    DWORD old_protect;
    int patched = 0;

    if (!dos || !target || dos->e_magic != IMAGE_DOS_SIGNATURE) return 0;
    nt = (IMAGE_NT_HEADERS *)((BYTE *)module + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return 0;
    if (!nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress) return 0;

    imports = (IMAGE_IMPORT_DESCRIPTOR *)((BYTE *)module +
        nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);
    for (; imports->Name; ++imports) {
        IMAGE_THUNK_DATA *thunk = (IMAGE_THUNK_DATA *)((BYTE *)module + imports->FirstThunk);
        for (; thunk->u1.Function; ++thunk) {
            FARPROC *slot = (FARPROC *)&thunk->u1.Function;
            if (*slot != target) continue;
            if (!VirtualProtect(slot, sizeof(*slot), PAGE_READWRITE, &old_protect)) continue;
            *slot = replacement;
            VirtualProtect(slot, sizeof(*slot), old_protect, &old_protect);
            FlushInstructionCache(GetCurrentProcess(), slot, sizeof(*slot));
            ++patched;
        }
    }
    return patched;
}

static DWORD WINAPI install_hooks(LPVOID unused)
{
    WSADATA data;
    HMODULE user32;
    HMODULE executable;
    int send_patches;
    int cursor_patches;

    (void)unused;
    if (WSAStartup(MAKEWORD(2, 2), &data) == 0) {
        bridge_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        memset(&bridge_address, 0, sizeof(bridge_address));
        bridge_address.sin_family = AF_INET;
        bridge_address.sin_port = htons(BRIDGE_PORT);
        bridge_address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    }

    user32 = GetModuleHandleA("user32.dll");
    executable = GetModuleHandleA(NULL);
    if (!user32 || !executable) return 1;

    real_SendInput = (send_input_fn)GetProcAddress(user32, "SendInput");
    real_SetCursorPos = (set_cursor_pos_fn)GetProcAddress(user32, "SetCursorPos");

    send_patches = patch_import(executable, (FARPROC)real_SendInput,
                                (FARPROC)hooked_SendInput);
    cursor_patches = patch_import(executable, (FARPROC)real_SetCursorPos,
                                  (FARPROC)hooked_SetCursorPos);
    bridge_send(BRIDGE_READY, (int32_t)GetCurrentProcessId(),
                send_patches, (uint32_t)cursor_patches, 0);
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        HANDLE thread;
        DisableThreadLibraryCalls(instance);
        thread = CreateThread(NULL, 0, install_hooks, NULL, 0, NULL);
        if (thread) CloseHandle(thread);
    } else if (reason == DLL_PROCESS_DETACH) {
        if (bridge_socket != INVALID_SOCKET) closesocket(bridge_socket);
        WSACleanup();
    }
    return TRUE;
}
