# zhang1：实验配置与结果（按算法）

说明：每行是一组实验配置（work_scale + repeats + CPU 核集合 + cores_per_task）的聚合统计；`total` 为该组 runs 的总耗时（按 mean×n 估算）。

## cpf

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 2.147378 | 1:47 | 2.010881/2.347150 | 2.093191 | 1:45 | 2.020402/2.323599 | 2.52% |

## lpf

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 1.977975 | 1:39 | 1.844748/2.157591 | 1.918842 | 1:36 | 1.838704/2.069135 | 2.99% |

## heft

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 2.155977 | 1:48 | 1.971098/2.394531 | 2.107108 | 1:45 | 1.918716/2.279489 | 2.27% |

## zhao2020

| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |
|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|
| 100 | 50 | 0-1 (c2) | 1.994350 | 1:40 | 1.864947/2.176627 | 1.927404 | 1:36 | 1.855442/2.044294 | 3.36% |

