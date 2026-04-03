# lpf 测时版本

此目录包含三个测时版本的源代码文件：

## 文件说明

1. **baseline_fifo.c**
   - 基于原始源代码
   - 插入了 FIFO 调度（优先级 99）
   - 包含 MAIN_ELAPSED_S 测时代码

2. **baseline_default.c**
   - 基于原始源代码
   - 使用默认调度策略
   - 包含 MAIN_ELAPSED_S 测时代码

3. **prio.c**
   - 基于插桩后的源代码
   - 包含动态优先级调度
   - 包含 MAIN_ELAPSED_S 测时代码

## 使用方法

1. 推荐运行 `./compile_and_run.sh` 脚本进行编译和全部测试。
2. 也可以直接在 VSCode/Cursor 中点击运行按钮（现在已配置 code-runner 支持 -pthread 等标志）。

注意：baseline_default.c 使用默认调度策略。

输出格式：
```
MAIN_ELAPSED_S=2.345678
```

## 编译命令

```bash
gcc -O2 -g -std=c11 -pthread -I"../../../../../level1" <源文件> -o <可执行文件> -lm
```
