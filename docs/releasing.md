# Releasing SystemCard

## First release setup

The first PyPI release is pending account setup. In your PyPI account, add a
[pending trusted publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
with these values:

| Field | Value |
| --- | --- |
| PyPI project name | `systemcard` |
| GitHub owner | `Degeneracy-Evil` |
| Repository | `SystemCard` |
| Workflow filename | `release.yml` |
| Environment | `pypi` |

No API token or repository secret is needed. The GitHub publish job uses a
short-lived identity issued for the configured workflow and environment.

## Build rehearsal

Run the **Release** workflow manually on `main`. This checks the package,
builds and tests CPython 3.12/3.13/3.14 manylinux2014 x86_64 wheels, and builds
and validates the source archive. A manual run does not publish to PyPI.
Download the wheel artifacts to install on another compatible machine before
the first public release:

```bash
python -m pip install /path/to/systemcard-0.1.0-*.whl
systemcard --section system --no-color
```

Download only the wheel matching the destination Python version. Python 3.12+
and Linux x86_64 with glibc 2.17+ are the initial supported environments.

## Publish

After account setup and a successful rehearsal, make sure the version in
`pyproject.toml` matches `src/systemcard/__init__.py`, then push its tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The tag must match the package version. All checks and artifact builds must
succeed before publishing. After publishing, a fresh runner installs the
version directly from PyPI and tests the native import and CLI.

Users can then install without cloning either repository:

```bash
python -m pip install systemcard
systemcard
```

PyPI release filenames cannot be reused. Later releases must use a new version
and matching tag; do not retag an already published release.
