# zhang3 粗略实验（ws10 × r10 × 5 算法）

- **含义**：与 `tools/runtime_compare/配置文件/zhang123_5algo_ws10_r10_cpu01_sudo.json` 中 **zhang3 段** 相同口径——`work_scale=10`、`repeats=10`、CPU `0,1`、每任务 2 核、`use_sudo`，用于快速看 baseline vs prio 趋势（非正式 ws100 长实验）。
- **配置**：`tools/runtime_compare/配置文件/zhang3_5algo_ws10_r10_cpu01_sudo.json`
- **结果目录**：本目录下 `zhang3_5algo_ws10_r10_cpu01_sudo/<时间戳>_ws10_r10/summary.json`

## 重新跑一遍

```bash
cd /home/firefly/Desktop/ScratchDAG
python3 tools/runtime_compare/main.py --cli --queue-mode \
  --results-root "/home/firefly/Desktop/ScratchDAG/experiment/第四次实验结果/rk3588/rough_zhang3_ws10_r10" \
  --config tools/runtime_compare/配置文件/zhang3_5algo_ws10_r10_cpu01_sudo.json \
  --wait --no-resume
```

说明：若默认 `tools/runtime_compare/实验结果/logs/cli.log` 无写权限（例如 root 占用），请始终用 `--results-root` 指到本目录。
