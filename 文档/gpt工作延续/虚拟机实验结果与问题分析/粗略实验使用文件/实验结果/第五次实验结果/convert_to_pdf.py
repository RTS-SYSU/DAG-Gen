import markdown
from weasyprint import HTML, CSS
from pathlib import Path

# 读取Markdown文件
md_file = Path("第五次实验结果汇总.md")
with open(md_file, 'r', encoding='utf-8') as f:
    md_content = f.read()

# 转换为HTML
html_content = markdown.markdown(md_content, extensions=['tables'])

# 添加CSS样式
html_with_style = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ size: A4 landscape; margin: 20mm; }}
        body {{ font-family: "Microsoft YaHei", SimSun, sans-serif; margin: 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 8px; }}
        th, td {{ border: 1px solid #ddd; padding: 4px; text-align: left; word-wrap: break-word; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        h1 {{ color: #333; font-size: 18px; }}
        h2 {{ color: #666; margin-top: 20px; font-size: 14px; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""

# 生成PDF
HTML(string=html_with_style).write_pdf("第五次实验结果汇总.pdf")
print("PDF生成成功！")
