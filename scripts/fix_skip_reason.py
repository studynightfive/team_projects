"""临时修复脚本：给 skip reason 字符串添加引号"""
import os
import re

for root, dirs, files in os.walk("backend/tests"):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            # 修复: reason=xxx) -> reason="xxx")
            content = re.sub(
                r'reason=([a-z][a-z ].*?)\)',
                r'reason="\1")',
                content
            )
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            print(f"Processed: {f}")

print("Done")