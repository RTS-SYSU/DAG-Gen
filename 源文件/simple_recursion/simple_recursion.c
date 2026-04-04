/*
 * simple_recursion.c — 用于验证「多级实例图 / 递归」在 DAG 上的行为（最小用例）
 *
 * 线程 + busy 的综合 Pipeline 用例见 ../simple/simple.c（本目录勿再放第二个 main，否则 timing 会链接失败）。
 *
 * 设计意图（对应 Code2DAG v2 展开器）：
 *
 * 1) 线性链 main -> a -> b -> c
 *    期望 v2：路径形如 main/a#1/b#1/c#1，内部节点互不塌缩。
 *
 * 2) 直接递归 d(n)：d 内部再次调用 d（RTL 中会多一条 CALL d）
 *    当前 v2 实现：展开栈中已含 d 时会生成 __cycle__d__ 占位节点，
 *    避免无限展开；这是「静态图」上的安全截断，不是运行时的 n 层。
 *
 * 3) 互递归 e <-> f：e 调 f，f 调 e
 *    期望 v2：第二轮进入已在栈中的函数时同样落为 cycle 占位，
 *    边上仍能看出「调用意图」，而不会把所有层压成单一节点名。
 *
 * 编译生成 RTL（在项目根目录执行）：
 *   gcc -O0 -fdump-rtl-expand -c 源文件/simple_recursion/simple_recursion.c
 *   会生成 simple_recursion.c.233r.expand（文件名因 GCC 版本可能略有差异）
 *
 * 生成 v2 DAG（在桌面 Code2DAG 目录，PYTHONPATH 含父目录）：
 *   python3 -m Code2DAG generate \
 *     --source-file 源文件/simple_recursion/simple_recursion.c \
 *     --output-base . \
 *     源文件/simple/simple_recursion.c.233r.expand
 *
 * 产物目录：中间结果/simple_recursion/生成dag图/v2/
 */

#include <stdio.h>

static void leaf(void) {
    puts("leaf");
}

static void chain_c(void) {
    leaf();
}

static void chain_b(void) {
    chain_c();
}

static void chain_a(void) {
    chain_b();
}

/* 直接递归：用于观察 v2 的 __cycle__ 截断 */
static void direct_rec(int n) {
    leaf();
    if (n > 0) {
        direct_rec(n - 1);
    }
    leaf();
}

static void mutual_f(int n);

static void mutual_e(int n) {
    leaf();
    if (n > 0) {
        mutual_f(n - 1);
    }
    leaf();
}

static void mutual_f(int n) {
    leaf();
    if (n > 0) {
        mutual_e(n - 1);
    }
    leaf();
}

int main(void) {
    chain_a();

    direct_rec(2);

    mutual_e(1);

    return 0;
}
