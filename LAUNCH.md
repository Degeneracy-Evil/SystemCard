# 安装与临时启动

首次 PyPI 发布仍等待账号配置。当前可从 GitHub Wheels / Release 工作流下载
匹配解释器和平台的 wheel，再安装或交给启动脚本运行。

```bash
python3 -m pip install /path/to/systemcard.whl
systemcard --compact
SYSTEMCARD_SPEC=/path/to/systemcard.whl bash run.sh --section cpu,memory --no-color
```

run.sh 优先 uvx，再 pipx，最后创建临时 venv；退出时清理临时 venv，
透传 CLI 参数和退出码。venv 路径要求 Python 3.6.8+；CentOS 7 自动升级 pip 至21.3.1，
Python 3.7 使用 pip<24.1，其余解释器使用当前 pip。

| 环境变量 | 用法 |
| --- | --- |
| SYSTEMCARD_SPEC | 本地 wheel、包规格、URL 或 git+https 包；默认 systemcard |
| SYSTEMCARD_VERSION | 指定 PyPI 版本，与 SPEC 互斥 |
| SYSTEMCARD_RUNNER | auto（默认）、uvx、pipx 或 venv；可显式验证旧解释器 |

例如在 PyPI 发布后：

```bash
pipx install systemcard
SYSTEMCARD_VERSION=0.1.0 bash run.sh --compact
```

也可以下载项目脚本后检查并运行：

```bash
curl -fsSL https://raw.githubusercontent.com/Degeneracy-Evil/SystemCard/main/run.sh -o run.sh
bash run.sh --compact
```

直接从 Git 安装需要 C++20 编译器、CMake 和构建依赖，已有兼容 wheel 的使用者
无需这些工具。发布流程见 [docs/releasing.md](docs/releasing.md)。
