# Code2DAG

<p align="center">
    <img src="./assets/logo.svg" alt="Code2DAG" width="30%">
</p>

<p align="center">
    <a href="https://github.com" rel="nofollow">
        <img src="https://img.shields.io/badge/Parallel_Programs-DAG_Construction-orange.svg">
    </a>
    <a href="https://github.com" rel="nofollow">
        <img src="https://img.shields.io/badge/Platform-Linux%20%7C%20POSIX-brightgreen.svg">
    </a>
    <a href="https://github.com" rel="nofollow">
        <img src="https://img.shields.io/badge/Python-%E2%89%A53.8-yellow.svg">
    </a>
</p>

<p align="center">
    <a href="README.md">English</a> | <a href="README_zh.md">中文</a>
</p>

**Code2DAG** is an automated toolchain for constructing scheduling-oriented DAG task models from parallel C programs. Starting from a source file and its GCC RTL intermediate representation, Code2DAG extracts inter-thread execution dependencies, constructs and minimizes a program DAG, annotates each node with its execution time, and generates instrumented programs with scheduling priorities for DAG-guided scheduling.

Evaluated on a real-time Linux platform, Code2DAG-guided scheduling reduces makespan by **13.73% on average** (up to **30.87%**) compared to Linux's Completely Fair Scheduler.


---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Pipeline Overview](#pipeline-overview)
- [Requirements and Installation](#requirements-and-installation)
- [CLI Reference](#cli-reference)
- [Output Structure](#output-structure)
- [Scheduling Policies](#scheduling-policies)
- [Example Output: `zhang1`](#example-output-zhang1)
- [Evaluation Summary](#evaluation-summary)
- [Terminology](#terminology)
- [Scope and Limitations](#scope-and-limitations)
- [Repository Layout](#repository-layout)

---

## Overview

Modern parallel programs exhibit complex, non-trivial execution dependencies among threads. These dependency structures can be represented as *Directed Acyclic Graphs* (DAGs), which in turn enable DAG-based scheduling to reduce program makespan by exploiting critical-path awareness. However, constructing a correct and compact DAG from real parallel programs is non-trivial: function calls, thread lifecycle events, and synchronization operations must all be precisely captured.

Existing dependency-extraction approaches either focus on specific dependency types in isolation (e.g., control flow or data flow), or rely on dynamic observations from particular program runs, making the resulting graphs tied to specific runs rather than program-level representations.

**Code2DAG** bridges this gap. It performs a joint static analysis of source code and GCC Register Transfer Language (RTL) to extract three categories of inter-thread dependencies — sequential function-call chains, thread lifecycle relations (`pthread_create`/`pthread_join`), and synchronization constraints (`sem_post`/`sem_wait`, `pthread_mutex_lock`/`pthread_mutex_unlock`) — and unifies them into a single DAG. It then automates the full workflow from raw source code to instrumented programs that can be directly scheduled using DAG-based methods, without manual annotation or model construction.

---

## Key Features

- **Automated DAG construction** from parallel C source code and GCC RTL, requiring no manual annotation
- **Three dependency types** captured: sequential (function-call chains), thread lifecycle (`pthread_create`/`pthread_join`), and synchronization (`sem_post`/`sem_wait`, `pthread_mutex_lock`/`pthread_mutex_unlock`)
- **Synchronization-aware node merging** that reduces graph size while preserving correctness across all dependency constraint types
- **Execution time annotation** via automated boundary instrumentation, producing an annotated DAG
- **Scheduling evaluation** with two baselines (`CFS` and `SCHED_FIFO`) and three DAG-guided policies (LPF, HEFT, and Zhao)
- **Instrumented code generation**: inserts runtime scheduling priorities into C programs
- **Interactive GUI workbench** for DAG visualization, pipeline control, and result inspection

---

## Quick Start

The recommended first example is `zhang1`.

From the repository parent:

```bash
python3 -m Code2DAG.pipeline.cli run_all \
  --source Code2DAG/source_files/zhang1/zhang1.c \
  --level level2 \
  --rule effective_line_merge
```

Upon successful completion, final outputs are published under `results/zhang1/`.

To launch the interactive GUI workbench instead:

```bash
python3 Code2DAG/run_gui.py
```

---

## Pipeline Overview

Code2DAG operates as a two-layer pipeline:

<p align="center">
    <img src="./assets/figures/code2dag_pipeline_overview.png" alt="Overview of the Code2DAG pipeline" width="95%">
</p>

**Stage a — Source/RTL Analysis:** Parses the C source file and the corresponding GCC RTL `.expand` dump using a state machine driven by regular-expression matching to extract function headers, symbol references, source locations, and variable identifiers.

**Stage b — Dependency Extraction:** Identifies three categories of inter-thread relations:
- *Sequential dependencies*: direct function-call chains within a thread
- *Thread lifecycle dependencies*: `pthread_create` / `pthread_join` relationships
- *Synchronization dependencies*: `sem_post` / `sem_wait` and `pthread_mutex_lock` / `pthread_mutex_unlock` pairings

**Stage c — DAG Construction:** Constructs the *original DAG* where each node represents a retained callee (program operation) and each directed edge encodes a dependency constraint derived from the DAG Construction IR.

**Stage d — Node Merging:** Applies a two-stage synchronization-aware merging algorithm. Stage 1 merges ordinary nodes and mutex-protected regions. Stage 2 performs upward and downward directional passes to merge synchronization control nodes (`create`, `join`, `post`, `wait`) with neighboring intermediate nodes, producing the *minimized DAG*.

**Stage e — Runtime Measurement:** Instruments the program at segment boundaries, executes it, and records average node execution times to produce the *annotated DAG*.

**Stage f — Priority Assignment:** Applies the selected scheduling policy over the annotated DAG to compute node priorities. Priorities are enforced at runtime by inserting `sp.sched_priority = prior_n` and `pthread_setschedparam(...)` at the entry of each node, producing the *executable DAG* as an instrumented C source file.

---

## Requirements and Installation

| Dependency | Version | Purpose |
|:---|:---|:---|
| Python | ≥ 3.8 | Pipeline runtime |
| GCC | any modern | RTL dump generation and instrumented program compilation |
| Graphviz (`dot`) | any modern | DAG rendering to PNG/SVG |

Quick environment check:

```bash
python3 --version
gcc --version
dot -V
```

Python package dependencies (see `requirements.txt`):

```text
networkx>=2.6
pillow>=9.0.0
pydot>=1.4.2
matplotlib>=3.5
pandas>=1.5
seaborn>=0.12
flask>=2.2
```
```bash
git clone <repository-url>
cd <repo-parent>
pip install -r Code2DAG/requirements.txt
```

Verify that GCC and Graphviz are available in your `PATH`. No compilation step is required for the Python pipeline itself.

**Directory note:** When running as a package module, execute from the repository parent:

```bash
python3 -m Code2DAG.pipeline.cli <subcommand> [options]
```

To run from an arbitrary working directory, add the repository parent to `PYTHONPATH`:

```bash
PYTHONPATH=/abs/path/to/<repo-parent> python3 -m Code2DAG.pipeline.cli list
```

---

## CLI Reference

The pipeline is controlled through `python3 -m Code2DAG.pipeline.cli`. The primary subcommand is `run_all`, which executes all stages end-to-end.

```text
python3 -m Code2DAG.pipeline.cli <subcommand> [options]
```

| Subcommand | Description |
|:---|:---|
| `run_all` | Execute the full pipeline: collect → blocks → timing → schedule → instrument |
| `collect` | Stage a–c: parse source/RTL and construct the original DAG |
| `blocks` | Stage d: apply node merging to produce the minimized DAG |
| `timing` | Stage e: instrument and profile node execution times |
| `schedule` | Stage f: compute scheduling priorities using the selected policy |
| `instrument` | Generate the final instrumented C source (executable DAG) |
| `list` | List available cases and their pipeline states |

**Key options for `run_all`:**

| Option | Description |
|:---|:---|
| `--source <path>` | Path to the input C source file |
| `--level <level1\|level2>` | Segmentation level; `level2` enables synchronization-aware merging |
| `--rule <rule>` | Node merging rule; `effective_line_merge` is the default |
| `--algo <name>` | Priority-assignment policy to use for generated instrumented outputs |

---

## Output Structure

For each processed case, Code2DAG publishes final outputs under `results/` and retains intermediate artifacts under `intermediate_results/`:

```text
results/<case_name>/
├── graphs/
│   ├── original_dag.png           # Original DAG visualization
│   ├── block_dag.png              # Minimized DAG visualization
│   └── original_dag.round.dot    # DOT source for the original DAG
└── algorithms/
    ├── FIFO/
    │   ├── source/FIFO.c          # SCHED_FIFO baseline output
    │   └── meta/summary.json      # Artifact metadata
    ├── LPF/
    ├── heft/
    └── zhao2020/
```

`results/` is the primary entry point for end-users. The `intermediate_results/` tree exposes internal pipeline stages and is intended for debugging and inspection.

---

## Scheduling Policies

Following the paper's evaluation setup, Code2DAG compares two Linux/non-DAG baselines with three DAG-guided scheduling policies:

| Policy | Type | Description |
|:---|:---|:---|
| **CFS** | Baseline | Linux Completely Fair Scheduler; the default Linux scheduler and the main comparison baseline |
| **SCHED_FIFO** | Baseline | Does not use a global DAG structure; assigns priorities according to the node with the largest estimated execution cost |
| **LPF** | DAG-guided | Longest-Path-First; assigns higher priorities to nodes on longer DAG paths |
| **HEFT** | DAG-guided | Rank-based task ordering from the HEFT scheduling method |
| **Zhao2020** | DAG-guided | Rule-based priority strategy from Zhao et al. (2020) |

The generated `SCHED_FIFO`, LPF, HEFT, and Zhao2020 programs are built from the same annotated DAG so their runtime results are directly comparable. CFS is measured by running the original program under the default Linux scheduler.

---

## Example Output: `zhang1`

**Input:** [source_files/zhang1/zhang1.c](source_files/zhang1/zhang1.c)

**Published outputs:**

| Output | Path |
|:---|:---|
| Original DAG | [results/zhang1/graphs/original_dag.png](results/zhang1/graphs/original_dag.png) |
| Minimized DAG | [results/zhang1/graphs/block_dag.png](results/zhang1/graphs/block_dag.png) |
| DOT source | [results/zhang1/graphs/original_dag.round.dot](results/zhang1/graphs/original_dag.round.dot) |
| LPF executable | [results/zhang1/algorithms/LPF/source/LPF.c](results/zhang1/algorithms/LPF/source/LPF.c) |
| HEFT executable | [results/zhang1/algorithms/heft/source/heft.c](results/zhang1/algorithms/heft/source/heft.c) |
| Zhao2020 executable | [results/zhang1/algorithms/zhao2020/source/zhao2020.c](results/zhang1/algorithms/zhao2020/source/zhao2020.c) |

**Suggested reading order:**
1. Start from the input program [zhang1.c](source_files/zhang1/zhang1.c).
2. Open [original_dag.png](results/zhang1/graphs/original_dag.png) to inspect the original DAG.
3. Open [block_dag.png](results/zhang1/graphs/block_dag.png) to inspect the minimized (merged) DAG.
4. Compare the instrumented programs under `results/zhang1/algorithms/` across scheduling strategies.
5. Consult each `meta/summary.json` for the artifact mapping and metadata.

---

## Evaluation Summary

Experiments are conducted on a VMware virtual machine running Ubuntu 20.04.6 LTS, equipped with a 13th Gen Intel Core i5-13400F processor at approximately 2.5 GHz, running a real-time Linux kernel (5.15.96-rt61). Each experiment is repeated 100 times and the average execution time is reported.

### Experimental Setup

Six representative DAG structures (DAG 1–6) with diverse topologies are evaluated under two CPU affinity configurations:

- **2-core** setting: CPU affinity `0–1`
- **4-core** setting: CPU affinity `0–1–2–3`

The evaluation follows the paper's comparison setup: two baselines, Linux CFS and `SCHED_FIFO`, are compared with three DAG-guided policies generated by Code2DAG: LPF, HEFT, and Zhao.

### Results

<table align="center">
<thead>
<tr>
<th align="center">Configuration</th>
<th align="center">Metric</th>
<th align="center">Result</th>
</tr>
</thead>
<tbody>
<tr>
<td align="center">2-core &amp; 4-core (all DAGs)</td>
<td align="center">Average makespan reduction vs. CFS</td>
<td align="center"><strong>13.73%</strong></td>
</tr>
<tr>
<td align="center">Best case (DAG 3, 4-core)</td>
<td align="center">Makespan reduction vs. CFS</td>
<td align="center"><strong>30.87%</strong></td>
</tr>
<tr>
<td align="center">Instrumentation overhead</td>
<td align="center">Per-node priority insertion cost</td>
<td align="center"><strong>~0.2 µs</strong></td>
</tr>
</tbody>
</table>

DAG-guided policies outperform CFS on most DAG structures and both core configurations. The improvement is most pronounced on DAGs with clear critical-path structure (DAG 3, DAG 4, DAG 5, DAG 6), while gains are limited on structures with near-equal path lengths where DAG-awareness provides less differentiation.

---

## Terminology

The following terms are used consistently throughout this tool and the companion paper:

| Term | Definition |
|:---|:---|
| **Original DAG** | The DAG constructed directly from source code and GCC RTL analysis |
| **Minimized DAG** | The DAG after synchronization-aware node merging |
| **Annotated DAG** | The minimized DAG with runtime execution costs attached to each node |
| **Executable DAG** | The instrumented C program generated from the priority-assigned annotated DAG |

Correspondence between terms and published output files:

| File | Corresponds to |
|:---|:---|
| `results/<case>/graphs/original_dag.png` | Original DAG (visual) |
| `results/<case>/graphs/block_dag.png` | Minimized DAG (merged graph view) |
| `results/<case>/algorithms/<algo>/source/<algo>.c` | Executable DAG (instrumented source) |

---

## Scope and Limitations

Code2DAG is designed for parallel C programs that express concurrency and synchronization through standard POSIX interfaces:

- Thread lifecycle: `pthread_create`, `pthread_join`
- Semaphore synchronization: `sem_post`, `sem_wait`
- Mutual exclusion: `pthread_mutex_lock`, `pthread_mutex_unlock`

---

## Repository Layout

```text
Code2DAG/
├── pipeline/               # CLI entry points and pipeline stage implementations
│   ├── cli.py              # Main command-line interface
│   ├── runner.py           # Pipeline orchestration
│   ├── collector.py        # DAG collection and construction
│   ├── timing.py           # Profiling and cost annotation
│   ├── schedule.py         # Priority policy dispatch
│   ├── instrument.py       # Priority instrumentation and code generation
│   ├── algo/               # Priority policy implementations (SCHED_FIFO baseline, LPF, HEFT, Zhao)
│   └── rules/              # Node merging rule implementations
├── generation/             # Source and RTL analysis, DAG construction
├── core/                   # Shared data models and parsing utilities
├── level1/                 # Level-1 segmentation and instrumentation
├── level2/                 # Level-2 segmentation with synchronization-aware merging
├── ui/                     # GUI workbench
├── visualization/          # Interactive DAG viewer
├── assets/                 # Logo and visual assets
├── source_files/           # Input C programs (test cases)
├── results/                # Final published outputs (DAG views, instrumented code)
├── intermediate_results/   # Internal pipeline artifacts
├── tools/                  # Auxiliary tools (runtime comparison, benchmarking)
├── requirements.txt
└── README.md
```

---
