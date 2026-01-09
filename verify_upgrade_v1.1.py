#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mycallyplus v1.1 升级验证脚本

验证所有修改是否正确完成
"""

import sys
from pathlib import Path

def check_file_content(file_path: Path, search_text: str, should_exist: bool = True) -> bool:
    """检查文件内容是否包含指定文本"""
    try:
        content = file_path.read_text(encoding='utf-8')
        exists = search_text in content
        
        if should_exist and exists:
            return True
        elif not should_exist and not exists:
            return True
        else:
            return False
    except Exception as e:
        print(f"❌ 错误读取文件 {file_path}: {e}")
        return False

def main():
    print("=" * 70)
    print("Mycallyplus v1.1 升级验证")
    print("=" * 70)
    print()
    
    # 获取项目根目录
    script_dir = Path(__file__).resolve().parent
    
    total_checks = 0
    passed_checks = 0
    
    # 检查项列表
    checks = [
        # GUI v3 检查
        {
            "file": script_dir / "ui/gui_v3.py",
            "search": 'self.base_dir = Path(__file__).resolve().parent.parent',
            "should_exist": True,
            "name": "gui_v3.py - base_dir 修改为 parent.parent"
        },
        {
            "file": script_dir / "ui/gui_v3.py",
            "search": '"mycallypro"',
            "should_exist": False,
            "name": "gui_v3.py - 移除 mycallypro 字符串"
        },
        
        # GUI 检查
        {
            "file": script_dir / "ui/gui.py",
            "search": 'self.base_dir = Path(__file__).resolve().parent.parent',
            "should_exist": True,
            "name": "gui.py - base_dir 修改为 parent.parent"
        },
        {
            "file": script_dir / "ui/gui.py",
            "search": '# 调用 legacy，指定output_base为mycallyplus目录',
            "should_exist": True,
            "name": "gui.py - 注释更新为 mycallyplus"
        },
        {
            "file": script_dir / "ui/gui.py",
            "search": '# legacy 会生成在 mycallyplus/配置文件',
            "should_exist": True,
            "name": "gui.py - 注释路径更新"
        },
        
        # Legacy 检查
        {
            "file": script_dir / "generation/legacy.py",
            "search": 'config.output_base = str(Path(__file__).parent.parent)',
            "should_exist": True,
            "name": "legacy.py - output_base 修改为 parent.parent"
        },
        {
            "file": script_dir / "generation/legacy.py",
            "search": '# 如果没有指定output_base，默认使用mycallyplus目录',
            "should_exist": True,
            "name": "legacy.py - 注释更新为 mycallyplus"
        },
        
        # 文档检查
        {
            "file": script_dir / "FULL_FEATURE_GUIDE_CN.md",
            "search": 'GUI/推荐：`mycallyplus/`',
            "should_exist": True,
            "name": "FULL_FEATURE_GUIDE_CN.md - base 取值更新"
        },
        {
            "file": script_dir / "FULL_FEATURE_GUIDE_CN.md",
            "search": '--output-base <DIR>`：指定输出根目录（推荐 `mycallyplus/`',
            "should_exist": True,
            "name": "FULL_FEATURE_GUIDE_CN.md - output-base 推荐值更新"
        },
        {
            "file": script_dir / "FULL_FEATURE_GUIDE_CN.md",
            "search": '以 `<base>=mycallyplus/`',
            "should_exist": True,
            "name": "FULL_FEATURE_GUIDE_CN.md - 输出文件路径示例更新"
        },
        
        # 新增文档检查
        {
            "file": script_dir / "UPGRADE_v1.1_独立化.md",
            "search": "Mycallyplus v1.1 升级说明",
            "should_exist": True,
            "name": "UPGRADE_v1.1_独立化.md - 文档存在"
        },
        {
            "file": script_dir / "升级总结_v1.1.md",
            "search": "Mycallyplus v1.1 升级总结",
            "should_exist": True,
            "name": "升级总结_v1.1.md - 文档存在"
        },
    ]
    
    # 执行检查
    for check in checks:
        total_checks += 1
        file_path = check["file"]
        search_text = check["search"]
        should_exist = check["should_exist"]
        name = check["name"]
        
        if not file_path.exists():
            print(f"❌ {name}")
            print(f"   文件不存在: {file_path}")
            continue
        
        result = check_file_content(file_path, search_text, should_exist)
        
        if result:
            print(f"✅ {name}")
            passed_checks += 1
        else:
            print(f"❌ {name}")
            if should_exist:
                print(f"   未找到文本: {search_text[:50]}...")
            else:
                print(f"   不应该包含文本: {search_text[:50]}...")
    
    print()
    print("=" * 70)
    print(f"验证结果: {passed_checks}/{total_checks} 通过")
    print("=" * 70)
    
    if passed_checks == total_checks:
        print()
        print("🎉 所有检查通过！升级成功完成！")
        print()
        print("下一步:")
        print("1. 测试 GUI: python -m mycallyplus")
        print("2. 测试 CLI: python -m mycallyplus generate <file.expand>")
        print("3. 检查输出: ls -la mycallyplus/配置文件/")
        return 0
    else:
        print()
        print("⚠️  部分检查失败，请检查上述错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())
