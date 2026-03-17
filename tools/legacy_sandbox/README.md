# legacy_sandbox

用于回归验证 `pthread_create` 绑定逻辑的独立副本工具。

## 目的
- 在不影响正式入口的前提下，快速验证 `expand -> dag.dot` 的 `create` 绑定是否正确。
- 对照正式实现 `mycallyplus_v1/generation/legacy.py` 的行为。

## 输入
- 必需：GCC RTL `*.expand` 文件。
- 可选：`--source-file <path/to/source.c>`（用于 source fallback）。
- 常用：`--threads-only`、`--output-base <path>`。

## 输出
默认输出到 `--output-base/中间结果/<base>/`：
- `生成dag图/dag.dot`
- `生成dag图/dag.png`（需额外执行 `dot -Tpng` 渲染）
- `生成dag图/functions_full.json`
- `生成dag图/functions_ranges.json`
- `生成dag图/debug/mycalls_meta_internal.json`

## 运行方式
在仓库外层目录执行（固定 PYTHONPATH）：

```bash
PYTHONPATH=/home/chove/桌面 python3 tools/legacy_sandbox/legacy_sandbox.py \
  --threads-only \
  --source-file /home/chove/桌面/mycallyplus_v1/源文件/zhang1/zhang1.c \
  --output-base /home/chove/桌面/mycallyplus_v1/tools/legacy_sandbox/out \
  /home/chove/桌面/mycallyplus_v1/中间结果/zhang1/配置文件/zhang1.c.233r.expand \
  > /home/chove/桌面/mycallyplus_v1/tools/legacy_sandbox/out/中间结果/zhang1/生成dag图/dag.dot

dot -Tpng \
  /home/chove/桌面/mycallyplus_v1/tools/legacy_sandbox/out/中间结果/zhang1/生成dag图/dag.dot \
  -o /home/chove/桌面/mycallyplus_v1/tools/legacy_sandbox/out/中间结果/zhang1/生成dag图/dag.png
```

## 与正式链路关系
- `tools/legacy_sandbox` 仅用于验证。
- 正式产出和模块化实验输入以 `mycallyplus_v1/generation/legacy.py` 为准。
