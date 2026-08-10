"""
Mermaid 图表渲染验证脚本
使用 mermaid-cli (mmdc) 验证 docs/member5-architecture.md 中的所有图表
"""
import re
import os
import subprocess
import sys

def main():
    arch_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "member5-architecture.md"
    )

    if not os.path.exists(arch_file):
        print(f"文件不存在: {arch_file}")
        sys.exit(1)

    with open(arch_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取所有 mermaid 代码块
    blocks = re.findall(r"```mermaid\n(.*?)```", content, re.DOTALL)

    if not blocks:
        print("未找到 Mermaid 代码块")
        sys.exit(1)

    print(f"找到 {len(blocks)} 个 Mermaid 图表，开始验证...")
    print("-" * 50)

    passed = 0
    for i, block in enumerate(blocks, 1):
        mmd_path = f"temp_diagram_{i}.mmd"
        png_path = f"temp_diagram_{i}.png"

        # 写入临时 .mmd 文件
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(block.strip())

        # 调用 mmdc 渲染 (Windows下需用完整路径)
        mmdc_path = os.path.join(os.environ.get("APPDATA", ""), "npm", "mmdc.cmd")
        if not os.path.exists(mmdc_path):
            mmdc_path = "mmdc"  # fallback
        result = subprocess.run(
            [mmdc_path, "-i", mmd_path, "-o", png_path],
            capture_output=True, text=True, timeout=60
        )

        # 清理临时文件
        if os.path.exists(mmd_path):
            os.remove(mmd_path)
        if os.path.exists(png_path):
            os.remove(png_path)

        if result.returncode == 0:
            print(f"  [OK] 图{i} 渲染成功")
            passed += 1
        else:
            # 提取关键错误信息
            err = result.stderr.strip()
            # 只取第一行有意义的错误
            lines = [l for l in err.split("\n") if l.strip() and "error" in l.lower()]
            if lines:
                print(f"  [FAIL] 图{i}: {lines[0][:150]}")
            else:
                print(f"  [FAIL] 图{i}: {err[:150]}")

    print("-" * 50)
    print(f"结果: {passed}/{len(blocks)} 通过")

    if passed < len(blocks):
        sys.exit(1)

if __name__ == "__main__":
    main()
