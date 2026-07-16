# 启动方式

这里介绍启动方式。

1. 提供shell使用脚本（这个只是过渡使用，或者追求新版本和测试）
由于项目需要做成多文件结构，故为了方便用户使用，提供一个 Bootstrap 脚本，例如：
curl -fsSL https://raw.githubusercontent.com/you/SystemCard/main/run.sh | bash

逻辑如下：
如果有 uv:
  uvx --from git+https://github.com/you/SystemCard.git SystemCard

否则如果有 pipx:
  pipx run --spec git+https://github.com/you/SystemCard.git SystemCard

否则如果有 python3 + pip:
  创建临时 venv
  pip install git+https://github.com/you/SystemCard.git
  运行 SystemCard
  退出后删除临时 venv

否则:
  提示需要 python3

2. 发布到pypi（主要使用这个方案）
发布到pypi，用pip或pipx直接使用
