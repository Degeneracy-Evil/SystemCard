# SystemCard 当前开发范围

联合七项交付清单暂存于 [Sysal 开发计划](../sysal/docs/development-plan.md)。
本项目已具备 CLI、Rich 展示、公开 API 绑定、按栏目实际采集、容器配额展示、
固定脱敏展示快照、bootstrap 与 wheel 发布工作流。

- Sysal 固定版本与 SHA-256，在 CMakeLists.txt 中维护；不在此项目编译 Sysal。
- Runtime 最低 Python 3.6.8 / glibc 2.17，开发工具 Python 3.12 / uv locked。
- wheel 工作流覆盖 CPython 3.6–3.14，并在 CentOS 7 系统 Python 上安装验证。
- 单个字段或域缺失时继续显示可用信息；参数错误在采集前返回。
- 默认展示整机信息、进程可见资源与 cgroup 配额，保持三者语义独立。
- 开发记录写在 Git；覆盖率只报告，不设硬门槛。

## 后续工作

首次 PyPI 发布等待账号 Trusted Publisher 配置；当前版本保持 0.1.0。
AMD/Intel 实机、NVIDIA MIG 实机、复杂 SYCL 子设备选择器仍需对应环境推进。
后续测试以真实问题和支持环境为依据补充，避免逐项复刻实现。
