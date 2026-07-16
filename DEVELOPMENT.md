# SystemCard 开发设计文档

## 1. 项目定位

SystemCard 是一个面向终端用户的系统信息展示工具。它通过调用 Sysal 提供的结构化系统信息能力，将机器的硬件、软件、网络、加速器等信息整理为清晰、美观、适合终端阅读的输出。

Sysal 负责系统信息采集、解析、归一化与结构化建模。SystemCard 负责用户交互、展示模型构建、终端渲染与发布安装体验。两个项目之间保持清晰边界：Sysal 提供可靠的数据能力，SystemCard 提供友好的产品形态。

SystemCard 的目标使用方式是：

```bash
pipx install systemcard
systemcard
```

用户安装后即可直接在终端中查看当前机器的系统概况。

## 2. 总体架构

SystemCard 采用 Python 实现终端工具层，使用 Rich 等终端渲染库完成美观输出。Sysal 作为 C++20 核心库，通过 pybind11 绑定到 Python 侧。

整体调用链路为：

```text
SystemCard CLI
    ↓
Python 应用层
    ↓
pybind11 扩展模块
    ↓
Sysal C++ API
    ↓
结构化系统信息
    ↓
Python 展示模型
    ↓
Rich 终端渲染
```

Sysal 在构建阶段被编译为带 `-fPIC` 的静态库 `libsysal.a`，随后静态链接进入 pybind11 生成的 Python 扩展模块。最终发布的 wheel 中包含 Python 代码和 native 扩展模块，用户侧只感知 `systemcard` 这个命令。

## 3. Sysal 与 SystemCard 的边界

Sysal 的职责是返回准确、稳定、结构化的系统信息。它负责处理不同 Linux 发行版、不同硬件平台、不同系统文件布局带来的采集差异，并以统一结构向上层暴露。

SystemCard 的职责是将 Sysal 返回的信息转化为适合人类阅读的终端展示内容。它关心字段选择、信息分组、终端宽度、颜色主题、紧凑模式、详细模式和错误提示体验。

两个项目的边界可以概括为：

```text
Sysal: collect and normalize
SystemCard: present and explain
```

Sysal 的内部结构可以随着采集能力演进而调整。SystemCard 通过绑定层接收面向展示的轻量数据结构，从而保持展示逻辑稳定。

## 4. Python 绑定设计

SystemCard 通过 pybind11 调用 Sysal。绑定层应当保持轻量，主要完成三件事：

第一，调用 Sysal 的 C++ 接口获取系统快照。第二，从 Sysal 的结构化结果中提取 SystemCard 展示需要的字段。第三，将这些字段转换为 Python 原生对象，例如 `dict`、`list`、`str`、`int` 和 `bool`。

推荐的绑定接口形式为：

```python
from systemcard import _sysal

data = _sysal.collect()
```

其中 `data` 是 Python 原生结构，而不是 JSON 字符串。这样可以保留结构化数据的便利性，同时避免序列化和反序列化过程。

绑定层返回的数据应该以展示为中心，例如：

```text
system
cpu
memory
accelerators
network
storage
software
warnings
```

SystemCard 的 Python 层再将这些数据转换为内部展示模型，供渲染层使用。

## 5. SystemCard 内部结构

SystemCard 的 Python 代码可以划分为四个核心部分。

`cli` 负责命令行参数解析和程序入口调度。它处理参数，并决定最终渲染方式。

`collector` 负责调用 API，接收 native 扩展返回的数据，并进行必要的异常处理。

`model` 负责构建展示模型。它将 Sysal 返回的原始展示数据整理为更适合渲染的结构，例如系统摘要、CPU 卡片、内存卡片、GPU 列表、网络列表和告警信息。

`render` 负责终端输出。它使用 Rich 完成颜色、表格、面板、对齐、紧凑布局和宽度适配。

推荐目录结构为：

```text
systemcard/
├── pyproject.toml
├── README.md
├── src/
│   └── systemcard/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── collector.py
│       ├── model.py
│       ├── render.py
│       ├── theme.py
│       └── _sysal*.so
├── bindings/
│   └── pybind_sysal.cpp
└── third_party/
    └── sysal/
```

## 6. 终端展示设计

SystemCard 的默认输出应该强调清晰、紧凑和美观。信息按照用户阅读机器状态时的自然顺序组织：系统概况、CPU、内存、加速器、网络、存储、软件环境和提示信息。

默认模式适合直接阅读，紧凑模式适合快速扫视，分区模式适合只查看某一类资源。

推荐命令形式为：

```bash
systemcard
systemcard --compact
```

输出风格应当兼顾服务器环境和现代终端。颜色用于辅助区分信息层级，关键字段保持对齐，未知或缺失字段使用统一的弱化样式展示。终端宽度较小时，布局自动收缩为更紧凑的形式。

## 7. 构建与发布策略

SystemCard 以 PyPI wheel 的形式发布。用户推荐使用 `pipx` 安装，从而获得独立的 Python 执行环境和全局可用的 `systemcard` 命令。

构建阶段在兼容老系统的 Linux 环境中完成。Sysal 的预编译产物面向 glibc 2.17+（CentOS 7 / RHEL 7）兼容，因此 SystemCard 的 native 扩展也应延续这一兼容目标。发布构建应当避免在过新的桌面发行版环境中直接产出 wheel。

推荐构建策略为：

```text
Sysal source
    ↓
libsysal.a with -fPIC
    ↓
pybind11 extension
    ↓
systemcard wheel
```

native 扩展优先静态链接 `libsysal.a`。C++ 运行时依赖应通过构建配置进行控制，降低用户环境中 `libstdc++` 版本差异带来的影响。

发布前应在 CentOS 7 或等价老环境中验证：

```bash
python -m pip install systemcard-*.whl
python -c "import systemcard._sysal"
systemcard
systemcard --compact
```

这一步用于确认 Python 扩展能够成功加载，Sysal 能够正常采集，SystemCard 能够完成终端渲染。

## 8. 版本演进计划

v0.0.1 目标是完成最小可用版本。该版本提供基本 CLI、Sysal 绑定、默认终端展示、紧凑模式和 CentOS 7 兼容 wheel。

v0.0.x 目标是完善展示体验。该版本增强 Rich 渲染效果，加入分区查看、终端宽度适配、无颜色输出和更清晰的错误提示。

v0.1.0 目标是形成稳定工具。该版本完善发布流程，补充自动化构建与测试，扩展更多系统字段，并稳定 SystemCard 展示数据结构。

## 9. 开发原则

SystemCard 的开发应围绕“安装简单、输出清晰、结构稳定”展开。Sysal 的能力通过绑定层进入 Python，Python 层专注于组织信息和优化展示体验。

绑定层保持薄而稳定，展示模型保持面向用户，渲染层保持可替换和可扩展。Sysal 的结构化能力越完整，SystemCard 的终端展示就越自然；SystemCard 的价值在于把这些结构化信息转化为用户一眼能看懂的机器名片。
