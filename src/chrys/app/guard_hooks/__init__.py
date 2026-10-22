# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
#
# 随包分发的安全拦截规则包（prompt_guard.py / tool_guard.py / guard_core.py /
# rules.json 是 Hook 子进程直接执行的脚本与词典，不导入 chrys，只用标准库）。
#
# 注意：`[tool.hatch.build] artifacts` 的通配符包含 `*`。文件名以下划线开头的文件
# 不会被 hatch 打进 wheel，所以这里的资源文件一律不要用 `_` 前缀，否则安装出来的
# 规则包会在打包版里缺文件，而源码运行时看不出来。
