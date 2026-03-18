# zhang22 Weight Calibration Report

- generated_at: 2026-03-17T20:58:14+08:00
- host: ubuntu
- busy_work_scale: 300
- zhang22_work_scale: 5
- calibration_repeats: 8

## Busy Calibration

| weight | per_call_mean_s | per_call_mean_ms | total_mean_s | stdev_s |
| --- | ---: | ---: | ---: | ---: |
| 1.0 | 0.001480396 | 1.480396 | 0.004441187 | 0.000326433 |
| 2.0 | 0.002801515 | 2.801515 | 0.008404546 | 0.000052383 |
| 5.0 | 0.007032847 | 7.032847 | 0.021098540 | 0.001098891 |
| 10.0 | 0.014042865 | 14.042865 | 0.042128596 | 0.000483032 |
| 20.0 | 0.029832440 | 29.832440 | 0.089497320 | 0.010650488 |
| 50.0 | 0.070438282 | 70.438282 | 0.211314845 | 0.012458939 |
| 100.0 | 0.135767145 | 135.767145 | 0.407301435 | 0.022647861 |

## zhang22 Current vs busy=0

- current mean: `0.010948 s`
- busy=0 mean: `0.000240 s`
- estimated compute share: `97.8036%`
- estimated structural share: `2.1964%`

## Interpretation

- `busy=0` 版本保留线程、锁、信号量、join、affinity，只把计算节点替换为空计算，因此它近似表示结构底噪。
- `busy_calibration` 给出单个 `busy_wait_seconds(weight)` 调用在当前实现下的平均时间，可作为后续块权重重建的计算成本映射。
