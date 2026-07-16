# SystemCard

SystemCard is a terminal system information card powered by [Sysal](https://github.com/Degeneracy-Evil/sysal).
It presents machine and current-process-visible resources in a concise Rich terminal interface.

## Local development

Initialize the Sysal dependency, then install with uv:

```bash
git submodule update --init --recursive
uv pip install -e '.[dev]'
systemcard
```

The local build requires CMake, a C++20 compiler, and Python 3.13 or newer. The compatible prebuilt Sysal shared library is vendored at `vendor/sysal/lib/libsysal.so`, then installed beside the native extension in the wheel.

## Compatibility

The release target is Linux systems with glibc 2.17 or newer (CentOS 7 / RHEL 7 and newer compatible distributions).
