#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Mirror ShareMouse's Wine SendInput calls into the native X11 desktop."""

import ctypes
import os
import signal
import socket
import struct
import time

DISPLAY_NAME = os.environ.get("DISPLAY", ":0.0").encode()
PORT = 48655
MAGIC = 0x49584D53
PACKET = struct.Struct("<IHHiiII")
HEALTH_REQUEST = b"SMXI_HEALTH"
HEALTH_RESPONSE = b"SMXI_OK"

BRIDGE_READY = 0
BRIDGE_CURSOR = 1
BRIDGE_MOUSE = 2
BRIDGE_KEYBOARD = 3

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x1000
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

VK_KEYSYMS = {
    0x08: "BackSpace", 0x09: "Tab", 0x0C: "Clear", 0x0D: "Return",
    0x10: "Shift_L", 0x11: "Control_L", 0x12: "Alt_L", 0x13: "Pause",
    0x14: "Caps_Lock", 0x1B: "Escape", 0x20: "space", 0x21: "Prior",
    0x22: "Next", 0x23: "End", 0x24: "Home", 0x25: "Left",
    0x26: "Up", 0x27: "Right", 0x28: "Down", 0x2C: "Print",
    0x2D: "Insert", 0x2E: "Delete", 0x5B: "Super_L", 0x5C: "Super_R",
    0x5D: "Menu", 0x6A: "KP_Multiply", 0x6B: "KP_Add",
    0x6C: "KP_Separator", 0x6D: "KP_Subtract", 0x6E: "KP_Decimal",
    0x6F: "KP_Divide", 0x90: "Num_Lock", 0x91: "Scroll_Lock",
    0xA0: "Shift_L", 0xA1: "Shift_R", 0xA2: "Control_L",
    0xA3: "Control_R", 0xA4: "Alt_L", 0xA5: "Alt_R",
    0xBA: "semicolon", 0xBB: "equal", 0xBC: "comma", 0xBD: "minus",
    0xBE: "period", 0xBF: "slash", 0xC0: "grave", 0xDB: "bracketleft",
    0xDC: "backslash", 0xDD: "bracketright", 0xDE: "apostrophe",
}
for code in range(0x30, 0x3A):
    VK_KEYSYMS[code] = chr(code)
for code in range(0x41, 0x5B):
    VK_KEYSYMS[code] = chr(code + 32)
for code in range(0x60, 0x6A):
    VK_KEYSYMS[code] = f"KP_{code - 0x60}"
for code in range(0x70, 0x88):
    VK_KEYSYMS[code] = f"F{code - 0x6F}"

SCAN_KEYSYMS = {
    0x01: "Escape", 0x02: "1", 0x03: "2", 0x04: "3", 0x05: "4",
    0x06: "5", 0x07: "6", 0x08: "7", 0x09: "8", 0x0A: "9",
    0x0B: "0", 0x0C: "minus", 0x0D: "equal", 0x0E: "BackSpace",
    0x0F: "Tab", 0x10: "q", 0x11: "w", 0x12: "e", 0x13: "r",
    0x14: "t", 0x15: "y", 0x16: "u", 0x17: "i", 0x18: "o",
    0x19: "p", 0x1A: "bracketleft", 0x1B: "bracketright",
    0x1C: "Return", 0x1D: "Control_L", 0x1E: "a", 0x1F: "s",
    0x20: "d", 0x21: "f", 0x22: "g", 0x23: "h", 0x24: "j",
    0x25: "k", 0x26: "l", 0x27: "semicolon", 0x28: "apostrophe",
    0x29: "grave", 0x2A: "Shift_L", 0x2B: "backslash", 0x2C: "z",
    0x2D: "x", 0x2E: "c", 0x2F: "v", 0x30: "b", 0x31: "n",
    0x32: "m", 0x33: "comma", 0x34: "period", 0x35: "slash",
    0x36: "Shift_R", 0x37: "KP_Multiply", 0x38: "Alt_L", 0x39: "space",
    0x3A: "Caps_Lock", 0x3B: "F1", 0x3C: "F2", 0x3D: "F3",
    0x3E: "F4", 0x3F: "F5", 0x40: "F6", 0x41: "F7", 0x42: "F8",
    0x43: "F9", 0x44: "F10", 0x45: "Num_Lock", 0x46: "Scroll_Lock",
    0x47: "KP_7", 0x48: "KP_8", 0x49: "KP_9", 0x4A: "KP_Subtract",
    0x4B: "KP_4", 0x4C: "KP_5", 0x4D: "KP_6", 0x4E: "KP_Add",
    0x4F: "KP_1", 0x50: "KP_2", 0x51: "KP_3", 0x52: "KP_0",
    0x53: "KP_Decimal", 0x57: "F11", 0x58: "F12",
}
EXTENDED_SCAN_KEYSYMS = {
    0x1C: "KP_Enter", 0x1D: "Control_R", 0x35: "KP_Divide",
    0x37: "Print", 0x38: "Alt_R", 0x45: "Pause", 0x47: "Home",
    0x48: "Up", 0x49: "Prior", 0x4B: "Left", 0x4D: "Right",
    0x4F: "End", 0x50: "Down", 0x51: "Next", 0x52: "Insert",
    0x53: "Delete", 0x5B: "Super_L", 0x5C: "Super_R", 0x5D: "Menu",
}


def log(message):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}", flush=True)


x11 = ctypes.CDLL("libX11.so.6")
xtst = ctypes.CDLL("libXtst.so.6")
x11.XInitThreads.restype = ctypes.c_int
x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XDefaultScreen.argtypes = [ctypes.c_void_p]
x11.XDefaultScreen.restype = ctypes.c_int
x11.XDisplayWidth.argtypes = [ctypes.c_void_p, ctypes.c_int]
x11.XDisplayWidth.restype = ctypes.c_int
x11.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
x11.XDisplayHeight.restype = ctypes.c_int
x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
x11.XStringToKeysym.restype = ctypes.c_ulong
x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
x11.XKeysymToKeycode.restype = ctypes.c_uint
x11.XFlush.argtypes = [ctypes.c_void_p]
x11.XFlush.restype = ctypes.c_int
xtst.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_int, ctypes.c_ulong]
xtst.XTestFakeMotionEvent.restype = ctypes.c_int
xtst.XTestFakeRelativeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                              ctypes.c_int, ctypes.c_ulong]
xtst.XTestFakeRelativeMotionEvent.restype = ctypes.c_int
xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                      ctypes.c_int, ctypes.c_ulong]
xtst.XTestFakeButtonEvent.restype = ctypes.c_int
xtst.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                   ctypes.c_int, ctypes.c_ulong]
xtst.XTestFakeKeyEvent.restype = ctypes.c_int

x11.XInitThreads()
display = x11.XOpenDisplay(DISPLAY_NAME)
if not display:
    raise SystemExit(f"Cannot open X display {DISPLAY_NAME.decode()}")
screen = x11.XDefaultScreen(display)
width = x11.XDisplayWidth(display, screen)
height = x11.XDisplayHeight(display, screen)


def fake_button(button, pressed):
    xtst.XTestFakeButtonEvent(display, button, int(pressed), 0)


def click_button(button, count=1):
    for _ in range(max(1, min(count, 16))):
        fake_button(button, True)
        fake_button(button, False)


def handle_mouse(dx, dy, data, flags):
    if flags & MOUSEEVENTF_MOVE:
        if flags & MOUSEEVENTF_ABSOLUTE:
            x = round((dx & 0xFFFF) * (width - 1) / 65535)
            y = round((dy & 0xFFFF) * (height - 1) / 65535)
            xtst.XTestFakeMotionEvent(display, screen, x, y, 0)
        else:
            xtst.XTestFakeRelativeMotionEvent(display, dx, dy, 0)

    for mask, button, pressed in (
        (MOUSEEVENTF_LEFTDOWN, 1, True), (MOUSEEVENTF_LEFTUP, 1, False),
        (MOUSEEVENTF_MIDDLEDOWN, 2, True), (MOUSEEVENTF_MIDDLEUP, 2, False),
        (MOUSEEVENTF_RIGHTDOWN, 3, True), (MOUSEEVENTF_RIGHTUP, 3, False),
    ):
        if flags & mask:
            fake_button(button, pressed)

    signed_data = ctypes.c_int32(data).value
    if flags & MOUSEEVENTF_WHEEL:
        click_button(4 if signed_data > 0 else 5, abs(signed_data) // 120)
    if flags & MOUSEEVENTF_HWHEEL:
        click_button(7 if signed_data > 0 else 6, abs(signed_data) // 120)
    if flags & (MOUSEEVENTF_XDOWN | MOUSEEVENTF_XUP):
        button = 8 if (data & 0xFFFF) == 1 else 9
        fake_button(button, bool(flags & MOUSEEVENTF_XDOWN))


def keysym_to_keycode(name):
    keysym = x11.XStringToKeysym(name.encode("ascii"))
    return x11.XKeysymToKeycode(display, keysym) if keysym else 0


def handle_keyboard(packed_key, flags):
    vk = packed_key & 0xFFFF
    scan = (packed_key >> 16) & 0xFFFF
    pressed = not bool(flags & KEYEVENTF_KEYUP)

    if flags & KEYEVENTF_UNICODE:
        name = f"U{scan:04X}"
    elif flags & KEYEVENTF_SCANCODE:
        table = EXTENDED_SCAN_KEYSYMS if flags & KEYEVENTF_EXTENDEDKEY else SCAN_KEYSYMS
        name = table.get(scan & 0xFF) or VK_KEYSYMS.get(vk)
    else:
        name = VK_KEYSYMS.get(vk)
    if not name:
        log(f"unmapped key vk=0x{vk:02x} scan=0x{scan:02x} flags=0x{flags:x}")
        return
    keycode = keysym_to_keycode(name)
    if not keycode:
        log(f"no X keycode for {name} (vk=0x{vk:02x}, scan=0x{scan:02x})")
        return
    xtst.XTestFakeKeyEvent(display, keycode, int(pressed), 0)


listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("127.0.0.1", PORT))
listener.settimeout(1.0)
running = True
event_counts = {BRIDGE_CURSOR: 0, BRIDGE_MOUSE: 0, BRIDGE_KEYBOARD: 0}


def stop(_signum, _frame):
    global running
    del _signum, _frame
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
log(f"native X11 bridge listening on 127.0.0.1:{PORT}, display={DISPLAY_NAME.decode()}, size={width}x{height}")
while running:
    try:
        raw, address = listener.recvfrom(256)
    except socket.timeout:
        continue
    if address[0] == "127.0.0.1" and raw == HEALTH_REQUEST:
        listener.sendto(HEALTH_RESPONSE, address)
        continue
    if address[0] != "127.0.0.1" or len(raw) != PACKET.size:
        continue
    magic, version, kind, a, b, c, d = PACKET.unpack(raw)
    if magic != MAGIC or version != 1:
        continue
    if kind == BRIDGE_READY:
        log(f"hook ready: Windows PID={a}, SendInput patches={b}, SetCursorPos patches={c}")
    elif kind == BRIDGE_CURSOR:
        event_counts[kind] += 1
        if event_counts[kind] <= 3:
            log(f"received cursor event #{event_counts[kind]}")
        xtst.XTestFakeMotionEvent(display, screen,
                                  max(0, min(width - 1, a)),
                                  max(0, min(height - 1, b)), 0)
    elif kind == BRIDGE_MOUSE:
        event_counts[kind] += 1
        if event_counts[kind] <= 3:
            log(f"received mouse event #{event_counts[kind]}")
        handle_mouse(a, b, c, d)
    elif kind == BRIDGE_KEYBOARD:
        event_counts[kind] += 1
        if event_counts[kind] <= 3:
            log(f"received keyboard event #{event_counts[kind]}")
        handle_keyboard(a, c)
    x11.XFlush(display)

listener.close()
log("native X11 bridge stopped")
