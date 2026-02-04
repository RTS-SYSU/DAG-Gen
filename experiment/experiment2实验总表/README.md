# experiment2 实验总表

本目录存放对 experiment2 的跨平台汇总表与可视化产物（虚拟机 vs RK3588S）。

- `tables/`：汇总表（CSV/Markdown）
- `scripts/`：生成汇总表的脚本
一句话结论（先给你结论）

最省事：Python + pandas + matplotlib / seaborn 自动出图
最适合答辩：关键指标表 + 2–3 张趋势/对比图
最专业：LaTeX（booktabs）或 Pandoc 自动生成论文级表格

下面展开。

方案一：Python 自动“汇总 + 排版 + 出图”（最推荐 ⭐⭐⭐⭐⭐）

你已经有：

config_results_all.csv

config_results_by_platform.md

👉 直接用 pandas 读 CSV，自动生成：

汇总表（均值、min/max、提升百分比）

对比柱状图 / 折线图

一键导出 PNG（直接塞 PPT）

1️⃣ 汇总统计（示例）
import pandas as pd

df = pd.read_csv("config_results_all.csv")

summary = (
    df.groupby(["platform", "work_scale"])
      .agg(
          baseline_mean=("baseline_mean", "mean"),
          prio_mean=("prio_mean", "mean"),
          improvement=("improvement", "mean"),
      )
      .reset_index()
)

print(summary)


👉 你可以很快得到一句话结论用的数据，比如：

在 VM 与 RK3588S 平台上，prio 相比 baseline 稳定提升 24%–30%。

2️⃣ 画一张**“答辩友好”的图**

推荐图 1：baseline vs prio（柱状图）

import matplotlib.pyplot as plt

subset = df[df["platform"] == "RK3588S"]

plt.figure(figsize=(6,4))
plt.plot(subset["work_scale"], subset["baseline_mean"], label="baseline", marker="o")
plt.plot(subset["work_scale"], subset["prio_mean"], label="prio", marker="o")

plt.xlabel("Work Scale")
plt.ylabel("Execution Time (s)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("rk3588_compare.png", dpi=300)


👉 PPT 非常好用，一眼就能看出趋势。

3️⃣ 直接生成“可贴 PPT 的表格”
ppt_table = summary.round(2)
ppt_table.to_csv("ppt_summary.csv", index=False)


你可以：

直接贴到 PPT

或复制到 Excel 微调样式

方案二：Markdown → LaTeX / Word（论文 & 正式材料 ⭐⭐⭐⭐）

你已经有一个 config_results_by_platform.md，这是个宝。

A️⃣ LaTeX（论文级）
\begin{table}[t]
\centering
\caption{Performance comparison on RK3588S}
\begin{tabular}{lccc}
\toprule
Work Scale & Baseline (s) & Prio (s) & Improvement \\
\midrule
50  & 4.50 & 3.18 & 29.3\% \\
100 & 8.98 & 6.47 & 28.0\% \\
\bottomrule
\end{tabular}
\end{table}


👉 非常适合你这种体系结构 / 实时系统方向。

B️⃣ Pandoc（Markdown → Word / PDF）
pandoc config_results_by_platform.md -o results.docx


👉 老师 / 项目组 / 非技术评审非常友好。

方案三：Excel / Google Sheets（应急但不推荐 ⭐⭐⭐）

适合：

快速改颜色

人工标注

不适合：

可复现

多轮实验

给你一个答辩用的“标准结果结构”模板

你后面 PPT / 论文都可以按这个来：

1️⃣ 实验设置

平台：VM / RK3588S

核心数：c4

对比方法：baseline vs prio

2️⃣ 核心指标

平均执行时间

WCET（或 max）

提升比例（%）

3️⃣ 关键结论（1 行）

在所有配置下，prio 调度在 VM 与 RK3588S 平台上均带来 23%–30% 的稳定性能提升，且提升随负载规模保持一致。

如果你愿意，我可以直接帮你做 3 件事之一

你选一个就行：

1️⃣ 直接帮你把 CSV 生成「PPT 级图 + 汇总表」
2️⃣ 帮你写“实验结果分析段落”（论文 / 答辩版）
3️⃣ 告诉我你最终用在：PPT / 论文 / 结题报告，我按场景帮你排版

你现在这批数据，其实已经非常好看了，差的只是“展示方式”。

