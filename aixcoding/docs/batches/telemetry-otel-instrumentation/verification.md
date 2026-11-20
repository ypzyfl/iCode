# 验证摘要：外置 OTel 业务埋点

## 2026-11-20 官方源码证据

只读查询官方 `openJiuwen-ai/iCode`：0.36.0=`78802f87d07f053fe560d680e4696c2bf322e2c2`；0.35.2=`2fd777f626649d53d7ccd701e26a1a7ada569ce8`。按完整SHA读取官方源码，不使用fork同名tag作证明。

读取0.36.0的15文件（14 Python+pyproject）；11个与0.35.2共同Python文件静态比较为7同4变，改变涉及tool_events、clients、engine和ACP。AST核对11个候选签名相同，但结果hook等语义变化，故不能据此认定运行兼容。源码/脚本副本和本地过程日志不提交，官方永久链接见design。

## 本次提交范围及检查

仅六件文档与一份ADR，基于 `main_aixcoding_cli`，无上游源码、依赖、CI、安装器或产品代码变更。默认文档检查允许ADR/self-review草案；不声明最终closure通过、不加豁免。运行检查的命令和实际结果于提交前追加。

G1–G4/T1–T16、真实后台/桌面及运行前后官方hash尚未验证，不计入通过。设计已确认不代表ADR、依赖审批和运行时条件已全部满足。

提交前实际执行（复用既有工具环境，未安装依赖）：

```bash
uv run --no-sync python aixcoding/tools/check_docs.py
uv run --no-sync python aixcoding/tools/gen_customizations.py --strict
uv run --no-sync ruff check --no-fix --no-cache aixcoding/
uv run --no-sync ruff format --check --no-cache aixcoding/
git diff --check
```

均exit 0：check_docs OK（28 ADR/49 design/48 self-review）；registry 106 rows/154 markers/24 retired IDs/0 warnings；Ruff All checks passed，format 429 files；七文档文本/链接/围栏检查0 errors。Ruff首次因新工作区缓存写权限退出2，改只读--no-cache后通过，未弱化规则。uv提示既有解释器不满足固定Python3.14.10，仅静态文档检查，不冒充目标环境运行验证。
