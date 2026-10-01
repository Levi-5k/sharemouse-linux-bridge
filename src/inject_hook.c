// SPDX-License-Identifier: MIT
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <string.h>

static DWORD find_process(const char *name)
{
    PROCESSENTRY32 entry;
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    DWORD pid = 0;

    if (snapshot == INVALID_HANDLE_VALUE) return 0;
    memset(&entry, 0, sizeof(entry));
    entry.dwSize = sizeof(entry);
    if (Process32First(snapshot, &entry)) {
        do {
            if (lstrcmpiA(entry.szExeFile, name) == 0) {
                pid = entry.th32ProcessID;
                break;
            }
        } while (Process32Next(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return pid;
}

int main(int argc, char **argv)
{
    const char *process_name;
    const char *dll_path;
    DWORD pid;
    HANDLE process;
    HANDLE thread;
    LPVOID remote_path;
    SIZE_T path_size;
    SIZE_T written;
    DWORD result = 0;
    HMODULE kernel32;
    LPTHREAD_START_ROUTINE load_library;

    if (argc != 3) {
        fprintf(stderr, "Usage: %s process.exe C:\\path\\hook.dll\n", argv[0]);
        return 2;
    }
    process_name = argv[1];
    dll_path = argv[2];
    pid = find_process(process_name);
    if (!pid) {
        fprintf(stderr, "Process not found: %s\n", process_name);
        return 3;
    }

    process = OpenProcess(PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION |
                          PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ,
                          FALSE, pid);
    if (!process) {
        fprintf(stderr, "OpenProcess(%lu) failed: %lu\n", (unsigned long)pid,
                (unsigned long)GetLastError());
        return 4;
    }

    path_size = strlen(dll_path) + 1;
    remote_path = VirtualAllocEx(process, NULL, path_size, MEM_COMMIT | MEM_RESERVE,
                                 PAGE_READWRITE);
    if (!remote_path) {
        fprintf(stderr, "VirtualAllocEx failed: %lu\n", (unsigned long)GetLastError());
        CloseHandle(process);
        return 5;
    }
    if (!WriteProcessMemory(process, remote_path, dll_path, path_size, &written) ||
        written != path_size) {
        fprintf(stderr, "WriteProcessMemory failed: %lu\n", (unsigned long)GetLastError());
        VirtualFreeEx(process, remote_path, 0, MEM_RELEASE);
        CloseHandle(process);
        return 6;
    }

    kernel32 = GetModuleHandleA("kernel32.dll");
    load_library = (LPTHREAD_START_ROUTINE)GetProcAddress(kernel32, "LoadLibraryA");
    thread = CreateRemoteThread(process, NULL, 0, load_library, remote_path, 0, NULL);
    if (!thread) {
        fprintf(stderr, "CreateRemoteThread failed: %lu\n", (unsigned long)GetLastError());
        VirtualFreeEx(process, remote_path, 0, MEM_RELEASE);
        CloseHandle(process);
        return 7;
    }

    if (WaitForSingleObject(thread, 10000) != WAIT_OBJECT_0) {
        fprintf(stderr, "Timed out waiting for LoadLibraryA in process %lu\n",
                (unsigned long)pid);
        TerminateThread(thread, 9);
    } else {
        GetExitCodeThread(thread, &result);
    }
    printf("Injected into %s (Windows PID %lu), module=%08lx\n", process_name,
           (unsigned long)pid, (unsigned long)result);

    CloseHandle(thread);
    VirtualFreeEx(process, remote_path, 0, MEM_RELEASE);
    CloseHandle(process);
    return result ? 0 : 8;
}
