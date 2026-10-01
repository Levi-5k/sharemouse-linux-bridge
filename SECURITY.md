# Security

## Important behavior

This project intentionally:

- loads a locally built DLL into a running `sharemouse.exe` process;
- calls `CreateRemoteThread` and `LoadLibraryA` from a local helper;
- patches `SendInput` and `SetCursorPos` entries in the executable's import table;
- synthesizes native X11 keyboard and mouse input through XTEST.

These techniques overlap with behaviors used by malware and may trigger antivirus, EDR, or sandbox detections. Review and build the source yourself. Do not use prebuilt binaries from untrusted parties.

## Network exposure

The native bridge binds only to `127.0.0.1:48655`. It does not open a LAN-facing service, decrypt ShareMouse traffic, inspect clipboard data, or transmit event data off the machine.

ShareMouse itself continues to use its configured UDP 1046 and TCP 6555 listeners. Apply ShareMouse's own security controls and restrict the local network as appropriate.

## Trust model

This project is intended for a trusted, single-user X11 desktop. Any process running as the same user can generally interact with the X11 session and could send packets to the loopback bridge. X11 does not provide strong per-application input isolation.

Runtime archives and Wine prefixes can contain:

- proprietary software;
- peer addresses and names;
- machine identifiers;
- layout and security settings.

Keep them private with mode `0600`; they are excluded by `.gitignore` and must not be attached to issues.

## Reporting a vulnerability

Do not publish sensitive runtime data or credentials in an issue. Open a GitHub security advisory for vulnerabilities in this repository's original code. Report ShareMouse vulnerabilities directly to its publisher.
