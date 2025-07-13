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
cd dag-gen
pip install -r requirements.txt  # only needed for Python parsing
```

Ensure you have:

- Python ≥ 3.7
- clang (for parsing C/C++ source)
- graphviz (optional, for visualization)

## 🛠 Supported Languages

| Language | Parser Backend         | Dependency  |
| -------- | ---------------------- | ----------- |
| C        | LLVM Clang + Cally     | clang-12+   |
| C++      | LLVM Clang + Cally     | clang-12+   |
| Python   | ast module + custom IR | Python 3.7+ |

## 🚀 Usage

### C/C++

```bash
# Step 1: Generate LLVM IR
clang -S -emit-llvm example.c -o example.ll

# Step 2: Run the tool
./daggen_cxx example.ll
```

### Python

```bash
python daggen_py.py example.py
```

Output files will be generated as:

```
output/
 ├── example.json         # DAG in JSON format
 ├── example.dot          # Graphviz format
 └── example.png          # (optional) visualized DAG
```

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

```python
def A(): ...
def B(): A()
def C(): A(); B()
```

→ DAG:

```
C --> B --> A
```

## 📝 TODO

- [ ] Loop flattening and static unrolling
- [ ] Global variable/data dependency support
- [ ] Support for dynamic analysis (future)

## 🙌 Acknowledgements

This tool is built upon and extends:

- [`cally`](https://github.com/RTS-SYSU/cally): LLVM-based call graph extractor for C/C++

## 📄 License

MIT License

## 🧑‍💻 Contact

Maintainer: **Your Name**  
Email: your.email@example.com