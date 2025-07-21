# DAG-Gen: A Cross-Language DAG Generation Tool for C/C++/Python

> **Based on [chaudron/cally](https://github.com/chaudron/cally)**  
> DAG-Gen is a lightweight tool designed to analyze the control and data flow of programs and generate task-level DAGs from C, C++, and Python code, facilitating task scheduling and static analysis in real-time.

## ✨ Features

- ✅ Support for C, C++, and Python codebases
- ✅ Generates DAG (Directed Acyclic Graph) representing function/task dependencies
- ✅ Supports function-level and basic-block-level DAGs
- ✅ Output in graphviz (.dot) formats
- ✅ Easy to extend and integrate into existing analysis workflows

## 📦 Installation

```bash
git clone https://github.com/RTS-SYSU/dag-gen.git
```

Ensure you have:

- Python ≥ 3.7
- GCC (for C/C++ analysis, recommended version 9+)
- graphviz (optional, for visualization)

## 🛠 Supported Languages

| Language | Parser Backend             | Dependencies |
| -------- | -------------------------- | ------------ |
| C        | GCC + custom RTL extractor | gcc-9+       |
| C++      | GCC + custom RTL extractor | gcc-9+       |
| Python   | ast module + custom IR     | Python 3.7+  |

## 🚀 Usage

### C/C++ (based on GCC RTL)

```bash
# Use GCC to dump RTL IR (requires -fdump-rtl-expand support)
gcc -fdump-rtl-expand example.c

# Run DAG generation tool on the .expand file
待完成
```

### Python

待完成

## 📂 Directory Structure

```
dag-gen/
├── daggen_cxx/           # C/C++ DAG generator (based on cally)
├── daggen_py.py          # Python DAG generator
├── examples/             # Example input files
├── output/               # Output DAG files
└── README.md
```

## 🧪 Examples

### C example

```c
void A() { ... }
void B() { A(); }
void C() { A(); B(); }
```

→ DAG:

```
C --> B --> A
```

### Python example

待完成

## 📝 TODO

- [ ]
- [ ]
- [ ]

## 🙌 Acknowledgements

This tool is built upon and extends:

- [`cally`](https://github.com/chaudron/cally): LLVM-based call graph extractor for C/C++

## 📄 License

MIT License

## 🧑‍💻 Contact

Maintainer: **chove**  
Email: 1751679308@qq.com
