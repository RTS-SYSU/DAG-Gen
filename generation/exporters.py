# -*- coding: utf-8 -*-
"""
导出器模块
用于将mycallypro的解析结果导出为各种格式，包括 circle.txt 格式
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.model import CallGraph


def write_dot(path: Path, dot_str: str) -> None:
    """写入DOT文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dot_str, encoding="utf-8")


def write_circle_auto(graph: CallGraph, path: Path) -> None:
    """自动从CallGraph生成circle.txt（简化版，保持向后兼容）"""
    path.parent.mkdir(parents=True, exist_ok=True)
    content: List[str] = []
    content.append("互斥量")
    mutex_entries = _collect_mutex_entries(graph)
    content.extend(mutex_entries or [""])
    content.append("")
    content.append("信号量")
    sem_entries = _collect_semaphore_entries(graph)
    content.extend(sem_entries or [""])
    path.write_text("\n".join(content), encoding="utf-8")


def _collect_mutex_entries(graph: CallGraph) -> List[str]:
    idx = 1
    entries: List[str] = []
    stack: List[Tuple[str, str]] = []
    for func in sorted(graph.functions):
        seq = graph.functions[func].call_sequence
        for call in seq:
            if "pthread_mutex_lock" in call:
                stack.append((func, f"MUTEX_{idx}"))
            elif "pthread_mutex_unlock" in call and stack:
                lock_func, var = stack.pop()
                entries.append(f"{lock_func} {var} {idx}")
                idx += 1
    return entries


def _collect_semaphore_entries(graph: CallGraph) -> List[str]:
    idx = 1
    posts: List[Tuple[str, str]] = []
    entries: List[str] = []
    for func in sorted(graph.functions):
        seq = graph.functions[func].call_sequence
        for call in seq:
            if "sem_post" in call:
                posts.append((func, f"SEM_{idx}"))
            elif "sem_wait" in call and posts:
                post_func, var = posts.pop(0)
                entries.append(f"{post_func} {var} {idx}")
                idx += 1
    return entries


# ============================================================================
# Legacy格式导出器（用于从legacy.py的functions字典导出）
# ============================================================================

class CircleTxtExporter:
    """导出 circle.txt 格式的配置文件，供 dag_describe 使用"""
    
    def __init__(self, functions: Dict, expand_file: Path, source_file: Optional[Path] = None):
        self.functions = functions
        self.expand_file = expand_file
        self.source_file = source_file
        
        # 用于生成唯一编号
        self._id_counters: Dict[str, int] = {}
        
        # 存储提取的记录
        self.mutex_records: List[Dict] = []
        self.sem_records: List[Dict] = []
    
    def export(self, output_path: Path) -> None:
        """导出到指定路径"""
        # 1. 提取互斥锁和信号量信息
        self._extract_sync_primitives()
        
        # 2. 生成txt文件内容
        content = self._generate_txt_content()
        
        # 3. 写入文件
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding='utf-8')
    
    def _extract_sync_primitives(self) -> None:
        """从函数调用列表中提取互斥锁和信号量信息"""
        for func_name, func_data in self.functions.items():
            mycalls = func_data.get('mycalls', [])
            
            # 为每个函数维护API调用计数器
            api_counters = {}
            
            for idx, call_node in enumerate(mycalls):
                # 解析节点名
                node_info = self._parse_node_name(call_node)
                if not node_info:
                    continue
                
                api_name = node_info['api']
                
                # 判断是否是互斥锁或信号量API
                if self._is_mutex_api(api_name):
                    # 计算这是该API在该函数中第几次调用
                    api_key = f"{func_name}_{api_name}"
                    call_count = api_counters.get(api_key, 0)
                    api_counters[api_key] = call_count + 1
                    
                    record = self._extract_mutex_record(
                        call_node, node_info, func_name, call_count
                    )
                    if record:
                        self.mutex_records.append(record)
                
                elif self._is_sem_api(api_name):
                    # 计算这是该API在该函数中第几次调用
                    api_key = f"{func_name}_{api_name}"
                    call_count = api_counters.get(api_key, 0)
                    api_counters[api_key] = call_count + 1
                    
                    record = self._extract_sem_record(
                        call_node, node_info, func_name, call_count
                    )
                    if record:
                        self.sem_records.append(record)
    
    def _parse_node_name(self, node_name: str) -> Optional[Dict]:
        """
        解析节点名
        格式: "main/while/pthread_mutex_lock5"
        返回: {
            'full': 'main/while/pthread_mutex_lock5',
            'prefix': 'main/while',
            'api': 'pthread_mutex_lock',
            'seq': 5
        }
        """
        if not node_name:
            return None
        
        # 提取序号
        match = re.search(r'(\d+)$', node_name)
        if not match:
            return None
        
        seq_num = int(match.group(1))
        api_with_seq = node_name.split('/')[-1]
        api_name = api_with_seq[:-len(match.group(1))]
        
        # 提取前缀
        parts = node_name.rsplit('/', 1)
        prefix = parts[0] if len(parts) > 1 else ''
        
        return {
            'full': node_name,
            'prefix': prefix,
            'api': api_name,
            'seq': seq_num
        }
    
    def _is_mutex_api(self, api_name: str) -> bool:
        """判断是否是互斥锁API"""
        return 'pthread_mutex_lock' in api_name or 'pthread_mutex_unlock' in api_name
    
    def _is_sem_api(self, api_name: str) -> bool:
        """判断是否是信号量API"""
        return 'sem_post' in api_name or 'sem_wait' in api_name
    
    def _extract_mutex_record(
        self, 
        call_node: str, 
        node_info: Dict, 
        func_name: str, 
        call_index: int
    ) -> Optional[Dict]:
        """提取互斥锁记录"""
        api_name = node_info['api']
        
        # 提取源码位置
        line_num, file_name = self._extract_source_location(
            func_name, api_name, call_index
        )
        
        # 提取变量名（尝试从expand文件中获取）
        var_name = self._extract_variable_name(func_name, api_name, call_index)
        if not var_name:
            var_name = 'mutex'  # 默认值
        
        # 生成唯一编号
        idx_name = self._generate_unique_id(var_name, 'mutex')
        
        return {
            'node': call_node,
            'type': 'mutex',
            'var': var_name,
            'idx': idx_name,
            'line': line_num,
            'file': file_name,
            'api': api_name
        }
    
    def _extract_sem_record(
        self, 
        call_node: str, 
        node_info: Dict, 
        func_name: str, 
        call_index: int
    ) -> Optional[Dict]:
        """提取信号量记录"""
        api_name = node_info['api']
        
        # 提取源码位置
        line_num, file_name = self._extract_source_location(
            func_name, api_name, call_index
        )
        
        # 提取变量名
        var_name = self._extract_variable_name(func_name, api_name, call_index)
        if not var_name:
            var_name = 'sem'  # 默认值
        
        # 生成唯一编号
        idx_name = self._generate_unique_id(var_name, 'sem')
        
        return {
            'node': call_node,
            'type': 'sem',
            'var': var_name,
            'idx': idx_name,
            'line': line_num,
            'file': file_name,
            'api': api_name
        }
    
    def _extract_source_location(
        self, 
        func_name: str, 
        api_name: str, 
        call_index: int
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        从expand文件中提取源码位置信息
        RTL格式示例:
        (call_insn 42 41 43 (call (mem:QI (symbol_ref:DI ("pthread_mutex_lock")) 
            [0  S1 A8]) (const_int 0 [0])) "simpletest.c":31:5 -1
        """
        if not self.expand_file.exists():
            return None, None
        
        try:
            content = self.expand_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            # 构建多个正则表达式模式，尝试匹配不同格式
            escaped_api = re.escape(api_name)
            
            # 模式1: 完整匹配 symbol_ref + 源码位置在同一行或附近
            pattern1 = re.compile(
                rf'symbol_ref.*?"{escaped_api}".*?"([^"]+)":(\d+)',
                re.IGNORECASE
            )
            # 模式2: call_insn后面可能有源码位置
            pattern2 = re.compile(r'"([^"]+\.c)":(\d+)(?::(\d+))?')
            
            matches = []
            in_function = False
            current_location = None
            
            for i, line in enumerate(lines):
                # 检测函数边界
                if f';; Function {func_name}' in line:
                    in_function = True
                    current_location = None
                    continue
                elif line.startswith(';; Function ') and in_function:
                    break
                
                if in_function:
                    # 查找包含API名称的行
                    if escaped_api in line and 'symbol_ref' in line:
                        # 检查当前行是否有源码位置
                        loc_match = pattern2.search(line)
                        if loc_match:
                            matches.append((int(loc_match.group(2)), loc_match.group(1)))
                        else:
                            # 在前后几行查找位置信息
                            found = False
                            # 先向后找
                            for j in range(i+1, min(i+5, len(lines))):
                                loc_match = pattern2.search(lines[j])
                                if loc_match:
                                    matches.append((int(loc_match.group(2)), loc_match.group(1)))
                                    found = True
                                    break
                            # 再向前找
                            if not found:
                                for j in range(max(0, i-5), i):
                                    loc_match = pattern2.search(lines[j])
                                    if loc_match:
                                        matches.append((int(loc_match.group(2)), loc_match.group(1)))
                                        break
            
            # 根据call_index返回对应的匹配
            if matches and call_index < len(matches):
                line_num, file_name = matches[call_index]
                return line_num, file_name
            
        except Exception as e:
            # 调试：打印异常信息
            import sys
            print(f"Debug: Failed to extract location for {func_name}/{api_name}[{call_index}]: {e}", file=sys.stderr)
        
        return None, None
    
    def _extract_variable_name(
        self, 
        func_name: str, 
        api_name: str, 
        call_index: int
    ) -> Optional[str]:
        """
        尝试从expand文件中提取变量名
        """
        if not self.expand_file.exists():
            return None
        
        try:
            content = self.expand_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.splitlines()
            
            in_function = False
            api_count = 0
            
            for i, line in enumerate(lines):
                if f';; Function {func_name}' in line:
                    in_function = True
                    continue
                elif line.startswith(';; Function ') and in_function:
                    break
                
                if in_function and api_name in line:
                    if api_count == call_index:
                        # 向上搜索附近的symbol_ref（可能是变量）
                        for j in range(max(0, i-10), i):
                            var_match = re.search(r'\(symbol_ref[^"]*"([^"]+)"\)', lines[j])
                            if var_match:
                                var_candidate = var_match.group(1)
                                # 过滤掉函数名
                                if not var_candidate.startswith('pthread_') and \
                                   not var_candidate.startswith('sem_'):
                                    return var_candidate
                        break
                    api_count += 1
        
        except Exception:
            pass
        
        return None
    
    def _generate_unique_id(self, var_name: str, category: str) -> str:
        """为变量生成唯一编号"""
        key = f"{category}_{var_name}"
        if key not in self._id_counters:
            self._id_counters[key] = len([k for k in self._id_counters if k.startswith(category)]) + 1
        return f"{var_name}{self._id_counters[key]}"
    
    def _generate_txt_content(self) -> str:
        """生成txt文件内容"""
        lines = []
        
        # 互斥量部分
        if self.mutex_records:
            lines.append("互斥量")
            for record in self.mutex_records:
                line_parts = [
                    record['node'],
                    record['type'],
                    record['idx']
                ]
                if record['line'] is not None:
                    line_parts.append(str(record['line']))
                if record['file'] is not None:
                    line_parts.append(record['file'])
                
                lines.append(' '.join(line_parts))
            lines.append("")
            lines.append("")
        
        # 信号量部分
        if self.sem_records:
            lines.append("信号量")
            for record in self.sem_records:
                line_parts = [
                    record['node'],
                    record['type'],
                    record['idx']
                ]
                if record['line'] is not None:
                    line_parts.append(str(record['line']))
                if record['file'] is not None:
                    line_parts.append(record['file'])
                
                lines.append(' '.join(line_parts))
            lines.append("")
            lines.append("")
            lines.append("")
        
        return '\n'.join(lines)


def export_circle_txt(
    functions: Dict,
    expand_file: Path,
    output_path: Path,
    source_file: Optional[Path] = None
) -> None:
    """
    便捷函数：导出circle.txt格式的配置文件
    
    Args:
        functions: mycallypro解析的函数字典
        expand_file: GCC RTL expand文件路径
        output_path: 输出txt文件路径
        source_file: 源代码文件路径（可选）
    """
    exporter = CircleTxtExporter(functions, expand_file, source_file)
    exporter.export(output_path)
