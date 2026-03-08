# zhang2：实验配置与结果（按算法）

说明：每行是一组实验配置（work_scale + repeats + CPU 核集合 + cores_per_task）的聚合统计；`total` 为该组 runs 的总耗时（按 mean×n 估算）。

## cpf

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 1.548745 | 1:17 | 1.454953/1.844514 | 1.466387 | 1:13 | 1.395093/1.728941 | 5.32% |

## lpf

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 1.519696 | 1:16 | 1.451724/1.721889 | 1.447548 | 1:12 | 1.398684/1.640577 | 4.75% |

## heft

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 1.580966 | 1:19 | 1.452606/2.781604 | 1.491830 | 1:15 | 1.399884/1.698390 | 5.64% |

## zhao2020

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 1.548107 | 1:17 | 1.447230/1.825792 | 1.459821 | 1:13 | 1.401763/1.626341 | 5.70% |

