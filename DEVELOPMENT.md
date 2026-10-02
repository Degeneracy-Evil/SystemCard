# SystemCard 开发设计

## 调用与边界

CLI 参数校验 → collector → systemcard._native → Sysal 公共 System::collect /
to_json → Python dict → model → Rich render。

绑定只包含发布包的公开头文件，通过公开 JSON 序列化保留 warnings/meta，
不暴露 Sysal C++ 对象，不复制内部 Reader/Parser 逻辑。
采集位掩码见 [绑定契约](docs/binding-contract.md)。`--section` 实际缩小采集范围；
`--compact` 采集 system/cpu/memory/accelerators 及必要依赖。

## 模型与展示

schema 处理缺失值；model 构建卡片；render 处理终端宽度和颜色。
CPU affinity、CPU 时间配额、整机内存与 cgroup 内存上限/当前用量分别展示。
MIG 通过 parent_uuid 与物理 GPU 关联，分开计数；软件卡片显示 ROCm、Level Zero
和已识别的通用库。未知值统一为 `—`，已知无限制显示 Unlimited；不完整层级中的限额显示为 `≤ 数值 (partial)`。
栏目通过显式映射决定采集位掩码和卡片构建函数，只执行选中的展示构建。
schema 集中处理结构、整数与有限数值读取，避免 bool 被误当作容量、枚举或频率。
固定展示样本位于 tests/fixtures，快照覆盖默认、紧凑、窄终端、缺失信息和容器数据。
样本是人工合成脱敏数据，不能代替厂商实机验收。

## 构建与兼容

CMake 下载固定版本与 SHA-256 的 Sysal Release package，静态链接其中 libsysal.a。
Sysal 包由 CentOS 7 / GCC 兼容构建提供；wheel 以 manylinux2014 x86_64 发布。
Python 3.8+ 使用 scikit-build-core；3.6/3.7 使用兼容 backend 和同一个 CMake target。
旧解释器使用 Rich 12，Python 3.6 使用 dataclasses backport。
开发工具使用 Python 3.12，runtime 源码保持 Python 3.6.8 语法兼容。

```bash
uv sync --locked --dev
uv run --locked systemcard --section cpu,memory --no-color
```

依赖升级后删除旧 build 目录并重新安装项目，防止 CMake CACHE 保留旧 URL / digest。
本地验证发布前的新包可以同时设置 CMake 的 SYSAL_VERSION、SYSAL_PACKAGE_URL
与 SYSAL_PACKAGE_SHA256；默认配置始终指向 GitHub 发布包。

工程规则沿用 base-py：显式格式修复、只读检查、staged snapshot hook，覆盖率无硬门槛。
优先用构建与真实采集验证开发成果；完整检查入口保留给最终验收与 CI。
安装、临时启动和 PyPI 状态见 [LAUNCH.md](LAUNCH.md)。
