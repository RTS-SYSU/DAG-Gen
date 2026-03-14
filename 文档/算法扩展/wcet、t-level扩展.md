可以，下面我直接给你一份**适合喂给 Codex 的实现说明**，目标是为 ScratchDAG 新增两个优先级算法：

1. `wcet_first`
2. `t_level`

我会按“**算法定义 → 如何从 DAG 得到优先级 → 伪代码 → 工程实现要求 → 与现有算法关系**”的方式写，尽量让 Codex 能直接落地。

在当前 ScratchDAG 实现里，节点 `cost` 的工程来源统一约定为 `pipeline/timing` 输出的 `avg_ns`。默认对同一分块 DAG 测时 10 次，并使用这 10 次结果汇总得到的平均值；若调用方显式覆盖重复次数，调度算法仍统一消费该次测时输出中的 `avg_ns`。

---

# 一、给 Codex 的总说明

你可以先把下面这段作为总任务描述喂给 Codex：

```text
请在 ScratchDAG 的优先级分配模块中新增两个 DAG 节点优先级算法：

1. wcet_first
2. t_level

输入是一个带权 DAG：
- 每个节点有唯一 id
- 每个节点有执行代价/权重 cost（可视为 WCET）
- DAG 提供 predecessors 和 successors 信息

输出是：
- 一个 priority map: {node_id: priority_value}

要求：
- priority_value 数值越大，表示优先级越高
- 算法必须只基于 DAG 结构和节点权重计算
- 结果应可直接用于后续调度器：在 ready 集合中选择 priority 最大的节点
- 代码风格与现有 b-level / cpf / zhao2020 实现保持一致
- 如果图非 DAG，需要显式报错
- 算法实现应保持可复现，必要时加入稳定的 tie-break 规则（如 node_id）

其中：
- wcet_first: 优先级直接等于节点自身 cost
- t_level: 优先级基于从 source 到该节点的最长路径长度计算，但由于系统统一采用“priority 越大越先执行”，因此需要将 t_level 转换为“更靠近 DAG 起点、更应优先执行”的数值形式

请分别实现：
- compute_wcet_first_priority(dag, cost_map)
- compute_t_level_priority(dag, cost_map)

并把它们注册到统一的 priority policy 枚举或工厂函数中。
```

---

# 二、算法 1：wcet-first

下面这部分你可以直接单独喂给 Codex。

---

## 1. 算法定义

```text
算法名称：wcet_first

核心思想：
- 节点自身执行代价（WCET / cost）越大，优先级越高
- 不做任何图传播
- 不考虑后继路径长度
- 不考虑前驱路径长度
- 只利用节点本身的 cost
```

数学定义：

对于任意节点 ( v )：

[
priority(v) = C(v)
]

其中：

* ( C(v) ) 为节点 ( v ) 的执行代价/权重

---

## 2. 如何从 DAG 得到优先级

```text
从 DAG 得到优先级的方法非常简单：

1. 遍历 DAG 中所有节点
2. 读取每个节点的 cost
3. 直接令该节点 priority = cost
4. 返回 priority map
```

注意：

* 该算法虽然输入是 DAG，但实际上不依赖 DAG 的边结构
* DAG 结构只在后续调度阶段用于约束 ready 集合
* 该算法本质上是一个局部启发式：ready 节点中 cost 最大者优先

---

## 3. 伪代码

```text
function compute_wcet_first_priority(dag, cost_map):
    priority = empty map

    for each node v in dag.nodes:
        if v not in cost_map:
            raise error("missing cost for node")
        priority[v] = cost_map[v]

    return priority
```

如果要写成 Python 风格伪代码：

```python
def compute_wcet_first_priority(dag, cost_map):
    priority = {}
    for v in dag.nodes():
        if v not in cost_map:
            raise ValueError(f"Missing cost for node {v}")
        priority[v] = cost_map[v]
    return priority
```

---

## 4. 工程要求

```text
实现要求：
- 时间复杂度 O(V)
- 空间复杂度 O(V)
- 保持 deterministic
- 若 cost 缺失，抛出异常
- 若节点 cost 为负数，可视项目约定决定是否允许；若不允许，显式报错
```

建议：

* 如果现有系统里 cost 已经保证合法，就不用重复做太多检查
* priority 值可保留为 float / int，不要强制转整型

---

## 5. 调度语义

```text
该算法生成的 priority 用于后续调度器：
- 在所有 ready 节点中
- 选择 priority 最大的节点先执行

即：
max(priority[v]) wins
```

---

## 6. 与现有算法关系

```text
wcet_first 与现有 b-level / cpf / zhao2020 的区别：

- 比 b-level 更简单：不做后向传播
- 比 cpf 更简单：不识别关键路径
- 比 zhao2020 更简单：不做复杂结构分析
- 可作为一个 baseline，用于体现“只利用局部节点代价”的效果
```

---

# 三、算法 2：t-level

这个算法需要说清楚一点，因为它和你现有“优先级越大越先执行”的系统约定之间有一个方向问题。

---

## 1. 算法定义

```text
算法名称：t_level

核心思想：
- t-level 表示从 DAG 入口到当前节点的最长路径长度
- 它反映一个节点“最早何时可能被触达”
- source 节点的 t-level 最小
- 越靠后的节点 t-level 越大
```

标准数学定义：

对于 source 节点 ( v )：

[
tlevel(v) = 0
]

对于非 source 节点 ( v )：

[
tlevel(v) = \max_{u \in Pred(v)} \left( tlevel(u) + C(u) \right)
]

其中：

* ( Pred(v) ) 表示 ( v ) 的前驱节点集合
* ( C(u) ) 表示前驱节点 ( u ) 的执行代价

注意这里的定义是：

* **从 source 到当前节点之前的最长累计代价**
* 通常**不包含当前节点自身 cost**

---

## 2. 直接 t-level 不能直接当“越大越优先”的 priority

这是关键点，你要明确告诉 Codex。

```text
t-level 的原始含义是“离起点越远，值越大”
但我们的调度系统约定是“priority 越大，越先执行”

因此不能直接把 t-level 原值作为最终调度优先级，否则会导致：
- 越靠后的节点 priority 越高
- 与 DAG 正向执行直觉相反
- 对 ready 队列选择没有合理的前置优先含义
```

所以你需要两种选择：

---

## 3. 推荐实现方式：保留计算结果 + 转成调度优先级

### 方案 A：返回“反向 t-level 优先级”

推荐你用这个。

先正常计算：

[
tlevel(v)
]

再令：

[
priority(v) = T_{\max} - tlevel(v)
]

其中：

[
T_{\max} = \max_{x \in V} tlevel(x)
]

这样有几个好处：

* source 节点 t-level 小，所以 priority 大
* 越靠近 DAG 起点，优先级越高
* 和你系统里“priority 越大越先执行”的约定一致
* 数值非负，便于调试和打印

---

### 方案 B：直接返回负的 t-level

也可以，但不如方案 A 直观：

[
priority(v) = -tlevel(v)
]

这样：

* t-level 越小，priority 越大（更接近 0）
* 逻辑成立
* 但调试输出不直观

**我建议你让 Codex 用方案 A。**

---

## 4. 如何从 DAG 得到 t-level 优先级

这部分可以直接喂给 Codex：

```text
从 DAG 得到 t-level priority 的步骤如下：

1. 先检查图是否为 DAG
2. 对 DAG 做拓扑排序
3. 按拓扑序正向遍历每个节点，计算原始 tlevel：
   - 若节点是 source，则 tlevel[v] = 0
   - 否则：
       tlevel[v] = max(tlevel[u] + cost[u] for u in predecessors[v])
4. 遍历所有节点，求 Tmax = max(tlevel[v])
5. 将原始 tlevel 转换为统一的“越大越优先”的 priority：
   - priority[v] = Tmax - tlevel[v]
6. 返回 priority map
```

---

## 5. t-level 的伪代码

### 5.1 原始 t-level 计算

```text
function compute_raw_t_level(dag, cost_map):
    topo = topological_sort(dag)
    tlevel = empty map

    for v in topo:
        preds = predecessors(v)
        if preds is empty:
            tlevel[v] = 0
        else:
            tlevel[v] = max(tlevel[u] + cost_map[u] for u in preds)

    return tlevel
```

### 5.2 转成最终 priority

```text
function compute_t_level_priority(dag, cost_map):
    tlevel = compute_raw_t_level(dag, cost_map)
    Tmax = max(tlevel.values())

    priority = empty map
    for each node v in dag.nodes:
        priority[v] = Tmax - tlevel[v]

    return priority
```

### Python 风格伪代码

```python
def compute_t_level_priority(dag, cost_map):
    topo = dag.topological_sort()
    tlevel = {}

    for v in topo:
        preds = dag.predecessors(v)
        if not preds:
            tlevel[v] = 0
        else:
            tlevel[v] = max(tlevel[u] + cost_map[u] for u in preds)

    tmax = max(tlevel.values()) if tlevel else 0

    priority = {v: tmax - tlevel[v] for v in dag.nodes()}
    return priority
```

---

## 6. 例子

建议你把这个例子也给 Codex，方便它自测。

DAG：

```text
A(2)
├── B(5)
└── C(3)
B ──┐
    ├── D(4)
C ──┘
```

其中：

* cost(A)=2
* cost(B)=5
* cost(C)=3
* cost(D)=4

### 第一步：计算原始 t-level

* A 是 source：

[
tlevel(A)=0
]

* B 的前驱是 A：

[
tlevel(B)=tlevel(A)+C(A)=0+2=2
]

* C 的前驱是 A：

[
tlevel(C)=0+2=2
]

* D 的前驱是 B, C：

[
tlevel(D)=\max(tlevel(B)+C(B),\ tlevel(C)+C(C))
]
[
=\max(2+5,\ 2+3)=7
]

所以：

* A = 0
* B = 2
* C = 2
* D = 7

### 第二步：转换为统一 priority

[
T_{\max}=7
]

因此：

* priority(A)=7-0=7
* priority(B)=7-2=5
* priority(C)=7-2=5
* priority(D)=7-7=0

最终：

```text
A: 7
B: 5
C: 5
D: 0
```

这意味着：

* 越靠近源点，优先级越高
* 更适合作为“前向层次优先”策略

---

## 7. 工程要求

```text
实现要求：
- 时间复杂度 O(V + E)
- 空间复杂度 O(V)
- 必须依赖拓扑排序
- 若图中存在环，应显式抛错
- 若节点缺失 cost，应显式抛错
```

建议同时保留一个调试接口：

* `raw_tlevel`
* `priority`

方便实验时打印分析。

例如：

```python
return {
    "raw_tlevel": tlevel,
    "priority": priority,
}
```

如果当前框架不方便，就只返回 priority，但内部日志里可以打印 raw_tlevel。

---

## 8. 与 b-level 的区别

这部分你最好也一并告诉 Codex，避免它写混。

```text
t-level 与 b-level 的核心区别：

1. b-level：
   - 从当前节点往后看
   - 度量“从该节点到 DAG 终点还有多长”
   - 越靠近关键后继路径，优先级越高

2. t-level：
   - 从 DAG 起点往前看
   - 度量“到达该节点之前已经经历了多长路径”
   - 原始值越大说明越靠后
   - 若要用于本系统的调度优先级，需要做方向转换
```

再强调一次：

* **b-level 是后向最长路**
* **t-level 是前向最长路**

---

# 四、你可以直接喂给 Codex 的完整版实现指令

下面这段我帮你整理成更完整的“工程 prompt”，你可以直接发给 Codex。

```text
请在 ScratchDAG 的 priority assignment 模块中新增两个优先级算法：wcet_first 和 t_level。

一、输入假设
输入是一个带权 DAG：
- dag.nodes() 返回全部节点
- dag.predecessors(v) 返回前驱节点列表
- dag.successors(v) 返回后继节点列表
- dag.topological_sort() 返回拓扑序
- cost_map[v] 给出节点 v 的执行代价（WCET-like cost）

二、统一输出约定
输出一个 priority map:
    {node_id: priority_value}
并保持系统统一语义：
    priority_value 越大，表示优先级越高，
    调度器在 ready 集合中选择 priority 最大的节点执行。

三、算法定义

1. wcet_first
定义：
    priority(v) = cost_map[v]

特点：
- 不依赖 DAG 边结构
- 只基于节点自身执行代价
- 作为 baseline 算法

实现要求：
- 遍历所有节点
- 检查 cost 是否存在
- 返回 priority map
- 时间复杂度 O(V)

2. t_level
先计算原始 t-level：

- 若 v 是 source（没有前驱）：
      tlevel(v) = 0
- 否则：
      tlevel(v) = max(tlevel(u) + cost_map[u] for u in predecessors(v))

这个 tlevel 表示从 DAG 起点到达当前节点之前的最长路径长度，不包含当前节点自身 cost。

由于系统约定是“priority 越大越先执行”，而原始 tlevel 越大表示节点越靠后，所以不能直接把 tlevel 作为最终 priority。

请采用如下转换方式：
    Tmax = max_v tlevel(v)
    priority(v) = Tmax - tlevel(v)

这样 source 节点优先级最高，越靠后的节点优先级越低。

实现要求：
- 必须基于拓扑排序正向 DP
- 若图非 DAG，抛出异常
- 若 cost 缺失，抛出异常
- 时间复杂度 O(V+E)

四、示例
示例 DAG：
A(2)
├── B(5)
└── C(3)
B ──┐
    ├── D(4)
C ──┘

wcet_first:
A=2, B=5, C=3, D=4

raw tlevel:
A=0
B=2
C=2
D=7

Tmax=7
最终 t_level priority:
A=7
B=5
C=5
D=0

五、代码组织要求
请：
- 新增 compute_wcet_first_priority(dag, cost_map)
- 新增 compute_t_level_priority(dag, cost_map)
- 将其接入统一的策略分派接口，如：
    compute_priority(dag, cost_map, policy)
  其中 policy 支持：
    "wcet_first"
    "t_level"
- 与现有 b-level / cpf / zhao2020 风格保持一致
- 尽量补充最小单元测试或示例测试

六、注意事项
- 不要把 t-level 和 b-level 混淆
- b-level 是后向最长路
- t-level 是前向最长路
- 本次只实现节点优先级计算，不修改调度器主体逻辑
```

---

# 五、我对你这套算法组合的建议

你现在这五个算法：

1. `wcet-first`
2. `b-level`
3. `t-level`
4. `zhao2020`
5. `cpf`

整体上已经很完整了，而且层次很清楚：

* `wcet-first`：局部代价优先
* `t-level`：前向层次优先
* `b-level`：后向关键路径优先
* `cpf`：关键路径优先
* `zhao2020`：更复杂的结构感知策略

这套非常适合做实验对比。

如果你论文里要解释它们的差异，可以浓缩成一句：

> 不同优先级分配策略分别从节点局部代价、前向路径深度、后向关键路径长度以及关键链结构等不同角度刻画 DAG 节点的重要性。

---

如果你愿意，我下一条可以继续帮你做两件事中的一个：
我可以把这五个算法统一整理成一份 **“ScratchDAG 优先级算法设计文档”**，或者直接帮你写一版 **实验章节里介绍这五种算法的论文式表述**。
