# DAG 权重参数优化工作延续（zhang11）

## 1. 目标与背景
- 目标：通过调整 `源文件/zhang11/zhang11.c` 的 `C1~C16`，让 `prio` 相对 `baseline(FIFO)` 在四算法（`cpf/lpf/heft/zhao2020`）上都获得稳定正收益，理想目标 `improvement_ratio > 10%`。
- 当前结论：仅靠本 DAG 现有结构（16 段、强依赖、并行窗口有限）很难稳定达到 10% 级别，需谨慎迭代并严格看统计口径。

## 2. 当前仓库真实状态（以文件为准）
### 2.1 当前权重（最新）
文件：`源文件/zhang11/zhang11.c`

```c
#define C1 70.0
#define C2 6.0
#define C3 42.0
#define C4 75.0
#define C5 6.0
#define C6 42.0
#define C7 80.0
#define C8 6.0
#define C9 50.0
#define C10 3.0
#define C11 6.0
#define C12 6.0
#define C13 5.0
#define C14 1.0
#define C15 1.0
#define C16 1.0
```

### 2.2 可直接复用脚本
1. 一键四算法测时脚本（正式对比）
- `tools/run_zhang11_4alg_sudo.sh`
- 默认参数：`WORK_SCALE=100 REPEATS=20 CORES_PER_TASK=2`
- `USE_SUDO=auto`（默认）会自动检测 `sudo -n`，无权限时自动降级 no-sudo 并把结果写到 `zhang11_<algo>_nosudo_*`

## 3. 已验证的关键事实（必须知道）
1. `no-sudo` 时，优先级设置会失败（`EPERM`），结果会退化为“插桩开销 + 噪声对比”，不适合作为最终结论。
2. 需要 `sudo`（或等价 `CAP_SYS_NICE`）才能让 `SCHED_FIFO` 真实生效。
3. 当前 `runtime_compare` 多数结果是 `parsed_from_stdout=false`，也就是 wall-time 回退口径；该口径可用，但汇报中必须明确说明。
4. 分块 DAG 相关产物路径：
- 分块图：`中间结果/zhang11/pipeline/blocks/level2/effective_line_merge/dag_seg.dot/png`
- 权重：`中间结果/zhang11/pipeline/timing/level2/effective_line_merge/timing.json`
- 优先级：`中间结果/zhang11/pipeline/schedule/level2/effective_line_merge/<algo>/schedule.json`
5. 当前机器 `sudo -n` 不可用时，`runtime_compare` 无法启用真实 FIFO；此时结果仅用于调参趋势，不作为最终结论。

## 4.1 最新三轮结果（2026-03-14，no-sudo，ws100 r20）
- `r0`（旧权重）：`cpf +1.0615%`，`lpf -0.6144%`，`heft -0.4720%`，`zhao2020 +0.1931%`
- `r1`（当前权重）：`cpf +1.8327%`，`lpf -0.0625%`，`heft -0.2880%`，`zhao2020 -0.1378%`
- `r2`（回撤 C10~C13）：`cpf +0.7430%`，`lpf +0.6846%`，`heft -0.6165%`，`zhao2020 -0.1188%`
- 结论：按“最差算法收益最大化（max-min）”选择 `r1` 作为当前最稳配置；但四算法全正仍未达成，且 no-sudo 口径不能作为最终结论。

## 4. 新窗口接手：最短执行路径
在新窗口中按以下顺序执行。

### 步骤 1：确认当前权重与脚本
```bash
cd /home/chove/桌面/mycallyplus_v1
nl -ba 源文件/zhang11/zhang11.c | sed -n '16,40p'
ls -la tools/run_zhang11_4alg_sudo.sh
```

### 步骤 2：如需改权重，仅改 `C1~C16`
- 不改线程结构/同步关系/函数骨架。
- 改完后进入步骤 3。

### 步骤 3：一键跑四算法（sudo）
```bash
cd /home/chove/桌面/mycallyplus_v1
./tools/run_zhang11_4alg_sudo.sh
```
可选：
```bash
WORK_SCALE=100 REPEATS=20 CORES_PER_TASK=2 ./tools/run_zhang11_4alg_sudo.sh
```

### 步骤 4：一键汇总四算法结果
```bash
cd /home/chove/桌面/mycallyplus_v1
python3 - << 'PY'
import json,glob,os
for a in ['cpf','lpf','heft','zhao2020']:
    roots=sorted(glob.glob(f'tools/runtime_compare/实验结果/zhang11_{a}_*'))
    if not roots:
        print(a, 'NO_RESULT_ROOT')
        continue
    ds=sorted(glob.glob(os.path.join(roots[-1], '*')))
    if not ds:
        print(a, 'NO_RESULT')
        continue
    d=ds[-1]
    s=json.load(open(os.path.join(d,'summary.json')))
    bm=s['baseline']['stats']['mean_s']
    pm=s['prio']['stats']['mean_s']
    impr=(bm-pm)/bm*100 if bm else 0
    print(f"{a}: baseline={bm:.6f}s prio={pm:.6f}s improvement={impr:.4f}% dir={d}")
PY
```

## 5. 调权策略（延续版）
目标是“四算法同时收益”，优先保证稳定正收益，再追求 10%：
1. 重：四算法共同高优先级段（入口+关键链尾）
- `C7, C4, C1, C9, C6, C3`
2. 轻：分歧段/同步桥
- `C8, C5, C2, C11, C12, C13`
3. 极轻：主线程串行尾
- `C14, C15, C16`
4. 每轮增幅建议 `15%~25%`，不要一次极端放大。

## 6. 常见坑（避免重复踩）
1. 改源码后未重建 DAG/pipeline，会导致产物与源码不一致。
2. 用 no-sudo 数据做最终结论，会误判算法收益。
3. 只看单次最优值不可靠，必须看 `n=20` 均值和波动。
4. 若结果目录被清理，`ls` 可能看不到历史结果；按步骤 3 重跑即可。

## 7. 下一窗口建议执行清单
- [ ] 读取本文件
- [ ] 确认 `zhang11.c` 当前权重
- [ ] 改 `C1~C16`（如需）
- [ ] 执行 `./tools/run_zhang11_4alg_sudo.sh`
- [ ] 跑汇总脚本，记录四算法指标
- [ ] 决策是否进入下一轮

---
最后更新时间：2026-03-14（本地会话交接）
