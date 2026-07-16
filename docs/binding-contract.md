# Native binding contract

The native extension exposes only `systemcard._native.collect(scope="default")`.
It returns JSON-compatible Python values generated through Sysal's public `to_json()` API.

Supported scopes are `default`, `basic`, and `full`. `default` gathers all user-facing domains except raw evidence; `full` additionally requests Sysal raw evidence but does not expose it in the returned snapshot.

Python modules must treat every field other than the top-level mapping as optional. The public snapshot contains `info`, `warnings`, and `meta`; presentation code must degrade gracefully when an optional Sysal field is absent.

The binding must not expose C++ Sysal object instances or include headers outside `third_party/sysal/include/sysal/`.
