# Priority Instrumentation Overhead Report

- generated_at: 2026-03-17T20:27:22+08:00
- host: ubuntu
- helper_mode: probe
- note: `probe` mode keeps the instrumentation call path but reapplies the current scheduling policy/priority, so it measures insertion cost without intended scheduling benefit.

## Summary

| variant | family | insert_count | mean_s | median_s | stdev_s | delta_vs_baseline_s | overhead_ratio | avg_prio_fail_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| standalone_baseline | standalone | 0 | 0.185016 | 0.179393 | 0.013629 | 0.000000 | 0.0000 | 0.00 |
| standalone_main_once | standalone | 1 | 0.178416 | 0.178400 | 0.012566 | -0.006601 | -0.0357 | 0.00 |
| standalone_phase_4sites | standalone | 4 | 0.176940 | 0.170833 | 0.015342 | -0.008076 | -0.0437 | 0.00 |
| zhang22_baseline | zhang22 | 0 | 0.026112 | 0.025165 | 0.003128 | 0.000000 | 0.0000 | 0.00 |
| zhang22_main_entry_only | zhang22 | 1 | 0.022919 | 0.022691 | 0.000481 | -0.003193 | -0.1223 | 0.00 |
| zhang22_worker_entries_only | zhang22 | 3 | 0.022998 | 0.022957 | 0.000789 | -0.003114 | -0.1192 | 0.00 |
| zhang22_main_segments_only | zhang22 | 8 | 0.024104 | 0.023666 | 0.001457 | -0.002008 | -0.0769 | 0.00 |
| zhang22_all_segments | zhang22 | 14 | 0.023715 | 0.023258 | 0.000962 | -0.002397 | -0.0918 | 0.00 |

## Insertions

- `standalone_baseline`: lines=[] priorities=[] helper_mode=probe
- `standalone_main_once`: lines=[50] priorities=[99] helper_mode=probe
- `standalone_phase_4sites`: lines=[50, 51, 52, 53] priorities=[99, 98, 97, 96] helper_mode=probe
- `zhang22_baseline`: lines=[] priorities=[] helper_mode=probe
- `zhang22_main_entry_only`: lines=[132] priorities=[99] helper_mode=probe
- `zhang22_worker_entries_only`: lines=[98, 113, 125] priorities=[91, 90, 89] helper_mode=probe
- `zhang22_main_segments_only`: lines=[132, 169, 172, 177, 181, 185, 189, 192] priorities=[99, 98, 97, 96, 95, 94, 93, 92] helper_mode=probe
- `zhang22_all_segments`: lines=[132, 169, 172, 177, 181, 185, 189, 192, 125, 113, 116, 98, 101, 105] priorities=[99, 98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86] helper_mode=probe
