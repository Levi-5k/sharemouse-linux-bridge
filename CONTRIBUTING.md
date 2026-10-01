# Contributing

Contributions are welcome for portability, key mapping, diagnostics, and safer recovery behavior.

Before opening a pull request:

```bash
make
make test
shellcheck scripts/*
```

Do not commit or upload ShareMouse binaries, Wine prefixes, runtime archives, packet captures containing private data, peer addresses, credentials, machine IDs, or compiled hook/injector binaries.

Keep changes focused on interoperability with software the user is authorized to run. This project does not accept features intended to bypass licensing, authentication, encryption, or access controls.
