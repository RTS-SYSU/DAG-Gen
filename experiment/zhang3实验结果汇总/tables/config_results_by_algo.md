# zhang3：实验配置与结果（按算法）

说明：每行是一组实验配置（work_scale + repeats + CPU 核集合 + cores_per_task）的聚合统计；`total` 为该组 runs 的总耗时（按 mean×n 估算）。

## cpf

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 5.511522 | 4:36 | 5.118879/6.882273 | 5.409270 | 4:30 | 4.936379/6.926151 | 1.86% |
| 100 | 50 | 0-1 (c2) | 5.531636 | 4:37 | 5.106928/6.246210 | 5.403116 | 4:30 | 4.942672/6.422132 | 2.32% |

## lpf

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 5.494671 | 4:35 | 5.140073/6.112922 | 5.493295 | 4:35 | 4.959049/6.356397 | 0.03% |

## heft

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 5.512748 | 4:36 | 4.994054/6.141955 | 5.366593 | 4:28 | 4.932786/6.461541 | 2.65% |
| 100 | 50 | 0-1 (c2) | 5.557649 | 4:38 | 5.220866/6.610505 | 5.423754 | 4:31 | 4.966071/6.542013 | 2.41% |

## zhao2020

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 5.603352 | 4:40 | 5.077922/6.397022 | 5.395263 | 4:30 | 4.957493/6.685597 | 3.71% |

