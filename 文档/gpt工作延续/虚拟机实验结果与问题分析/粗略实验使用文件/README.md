# 粗略实验使用文件

本目录保存 2026-03-19 虚拟机粗略实验实际使用的输入文件，按 `zhang/算法名` 组织。

目录说明：

- `runtime_task.json`
  - 本次粗略实验的原始任务配置
- `zhang1/<algo>/`
- `zhang2/<algo>/`
- `zhang3/<algo>/`
  - 每个目录内包含：
    - `source_original.c`
    - `source_instrumented.c`

算法列表：

- `cpf`
- `heft`
- `zhao2020`
- `wcet_first`
- `t_level`

这些文件来自以下原始位置：

```text
中间结果/<zhang>/pipeline/instrument/level2/effective_line_merge/<algo>/
```

用途：

- 追溯本次粗略实验到底跑了哪些源码文件
- 后续复现实验时，避免再次从 `runtime_task.json` 反查
- 便于按样例和算法逐项检查输入
