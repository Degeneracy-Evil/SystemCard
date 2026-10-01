# SystemCard 开发计划

## 当前约束

- Sysal 使用固定版本与 SHA-256 的 GitHub Release package，当前为 v0.0.8。
- SystemCard 仅依赖 Sysal 的公开头文件和公开序列化 API；不得依赖或读取其内部实现。
- Python 环境、依赖与锁文件统一由 `uv sync` 管理。
- 当前阶段只要求在本地开发环境跑通；暂不规划 Python 版本矩阵与跨平台发布矩阵。
- Linux 兼容性目标为 glibc 2.17+（CentOS 7 / RHEL 7）。

## 目标与边界

SystemCard 负责 Python CLI、展示数据契约、Rich 渲染、安装与发布体验。Sysal 负责系统信息采集与归一化。

绑定层必须保持很薄：只调用 Sysal 的公共 `System::collect()`、`SysalError`、`Collect` 与 `to_json()` API，并向 Python 返回普通的 `dict`、`list`、`str`、`int`、`bool` 与 `None`。不得将 Sysal C++ 对象、Reader、Parser、后端或 RawStore 细节暴露给 Python。

默认输出同时区分整机资源和当前进程可见资源，避免容器、MPI 或 cpuset 环境下产生误导。完整采集失败应提供清晰错误；单个采集域失败则继续展示可用信息并呈现 Sysal warnings。

## 规划目录结构

```text
SystemCard/
├── pyproject.toml                  # 包元数据、CLI 入口、构建配置、依赖
├── README.md                       # 安装、用法、示例、兼容性
├── DEVELOPMENT.md                  # 架构与开发约定
├── LAUNCH.md                       # Bootstrap 与 PyPI 发布方案
├── plan.md                         # 当前开发计划
├── docs/
│   ├── binding-contract.md         # Sysal 到 Python 的稳定数据契约
│   └── release.md                  # 本地与 CentOS 7 wheel 验证流程
├── src/
│   └── systemcard/
│       ├── __init__.py
│       ├── __main__.py             # `python -m systemcard`
│       ├── cli.py                  # 参数解析、调度、退出码
│       ├── collector.py            # native 调用与错误转换
│       ├── schema.py               # 数据契约、缺失值规范与基础校验
│       ├── model.py                # 原始快照到展示模型
│       ├── formatters.py           # 容量、频率、速率、未知值格式化
│       ├── render.py               # Rich 终端渲染
│       ├── theme.py                # 颜色与样式
│       └── _native.*.so            # 编译产物，不提交源码库
├── bindings/
│   └── pybind_sysal.cpp            # C++ 适配层，仅使用 Sysal 公共 API
├── scripts/
│   └── check.py                    # Ruff、mypy 与 pytest 统一检查入口
├── tests/
│   ├── fixtures/                   # 固定、脱敏的 Sysal JSON 快照
│   ├── test_collector.py
│   ├── test_model.py
│   ├── test_formatters.py
│   ├── test_render.py
│   └── test_cli.py
└── .github/workflows/ci.yml        # 与本地相同的质量检查和 smoke test
```

## 分阶段步骤

### 1. 工程基础与文档

- 完善 `pyproject.toml`：包元数据、`systemcard` 命令入口与本地开发依赖。
- 初始化 `src/` 包结构、测试配置。
- 完善 README：安装、最小用法与 glibc 2.17+ 声明。
- 使用 `uv sync --locked --dev` 安装本地开发所需依赖。

### 2. 固定 Sysal 依赖与数据契约

- 通过 GitHub Release package 消费 Sysal，并固定版本与 SHA-256。
- 在 `binding-contract.md` 明确 SystemCard 消费的字段、单位、可选字段、缺失值与契约版本。
- 以 Sysal 公共 `to_json()` 输出作为事实源；SystemCard 只依赖自身版本化的数据契约。

### 3. C++ 绑定层

- 实现 `_native.collect()`：调用 `System::collect()`，通过公开 `to_json()` 转换为 Python 原生对象。
- 支持默认、完整和按域采集所需的 `Collect` 范围。
- 将 `SysalError` 映射为明确的 Python 异常，并保留 `warnings` 与 `meta`。
- 本地验证扩展可以导入并完成一次真实采集。

### 4. Python 采集与展示模型

- `collector.py` 统一 native 模块加载、采集调用与用户可读的错误信息。
- `schema.py` 对数据进行最小校验并标准化缺失值。
- `model.py` 构建面向用户的卡片模型，渲染层不直接遍历 Sysal 原始层级。
- 默认摘要覆盖系统、CPU、内存、可见加速器、网络、存储、关键软件环境与告警。

### 5. CLI 与 Rich 渲染

- 默认模式：完整、清晰的机器名片。
- `--compact`：关键摘要。
- `--no-color`：日志和无颜色终端。
- `--section <name>`：按 `cpu`、`memory`、`accelerators`、`network`、`storage`、`software` 查看。
- 根据终端宽度自动收缩布局；未知值统一显示为弱化的 `—`。
- 定义成功、采集失败和参数错误的退出码。

### 6. 测试与本地验收

- Python 单元测试以固定 JSON fixture 为主，不依赖本机硬件或 Sysal 内部行为。
- native smoke test 验证扩展导入、真实采集、warning 与异常路径。
- 为默认、紧凑、无颜色及窄终端输出建立快照测试。
- 本地验收：安装开发包后运行 `systemcard`、`systemcard --compact`、`systemcard --no-color`。

### 7. 构建与发布准备

- 下载 Sysal Release package 并静态链接其中的 `libsysal.a`；SystemCard 构建流程不负责编译 Sysal。
- 先确保本地 wheel 可以安装和运行。
- 本地流程稳定后，再补充 CentOS 7 / glibc 2.17+ wheel 验证与 CI。

### 8. 启动与发布

- 实现优先使用 `uvx`、其次 `pipx`、最后临时 venv 的 Bootstrap 脚本。
- 完成版本、许可证、README 渲染和 wheel 内容检查后发布 PyPI。
- 推荐用户安装方式：`pipx install systemcard`。

## 推荐执行顺序

先完成第 1 至第 4 阶段，得到一条能够真实采集并形成展示模型的本地纵向链路；之后实现 CLI 与视觉体验；最后处理 wheel、CentOS 7 验证和发布自动化。


工程验证采用 base-py 的只读检查与 staged snapshot hook；格式修复显式执行。Python 开发工具保持 3.12，最低运行版本为 CentOS 7 系统自带的 3.6.8，覆盖率仅报告，不设置硬门槛，开发记录写在 Git 提交中。
