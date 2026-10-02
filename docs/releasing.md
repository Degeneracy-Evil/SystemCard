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
builds and tests CPython 3.6–3.14 manylinux2014 x86_64 wheels, and builds
and validates the source archive. A manual run does not publish to PyPI.
Download the wheel artifacts to install on another compatible machine before
the first public release:

```bash
python -m pip install /path/to/systemcard-0.1.0-*.whl
systemcard --section system --no-color
```

Download only the wheel matching the destination Python version. Python 3.6.8+
and Linux x86_64 with glibc 2.17+ are the initial supported environments.
CentOS 7 needs `python3 -m pip install --upgrade pip==21.3.1` first because its
packaged pip predates manylinux2014 wheel support. This does not replace Python.

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

## 更新 Sysal 依赖

先在 Sysal 仓库生成 CentOS 7/GCC 兼容 GitHub Release，下载其正式 tar.gz 并计算 SHA-256。
同步更新 CMakeLists.txt 的 SYSAL_VERSION、SYSAL_PACKAGE_URL 默认值与 SYSAL_PACKAGE_SHA256，
不要使用另一次本地打包的摘要替代正式资产摘要。删除旧 build 目录，再重新安装开发包，
确认实际采集的 meta.sysal_version 与固定版本一致。SystemCard 不重新编译 Sysal。

本轮 bootstrap 已验证 uvx 的 Python 3.12 wheel 路径和 CentOS 7/Python 3.6.8 临时 venv 路径。
后者在真实 --cpus=1.5、--memory=512m 的容器中显示配额，运行环境无需编译器或开发头文件。
