#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكربت تلقائي لتوليد نسخ من source4.py:
 - ينشئ source1.py, source2.py, source3.py
 - داخل كل نسخة يضيف أو يستبدل vvX إلى vv{index}.json
"""

import os
import re
import shutil
from datetime import datetime

SOURCE_FILE = "source4.py"   # الملف الأصلي
BASE_NAME = "source"         # أسماء النسخ: source1.py, source2.py...
START_INDEX = 1              # رقم البداية
COUNT = 3                    # عدد النسخ
OUT_DIR = "."                # المجلد الناتج

# يبحث عن أي شكل vv1 أو vv1.txt أو vv1.json
VV_PATTERN = re.compile(r"\bvv(\d+)(?:\.\w+)?\b", re.IGNORECASE)

def backup(path):
    if os.path.isfile(path):
        bak = path + ".bak"
        shutil.copy2(path, bak)
        print(f"✅ تم إنشاء نسخة احتياطية: {bak}")
    else:
        raise FileNotFoundError(f"الملف غير موجود: {path}")

def read_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def make_header(original_path):
    return (
        f"# --- Modified by auto-copy script ---\n"
        f"# original file: {os.path.basename(original_path)}\n"
        f"# modified_at: {datetime.utcnow().isoformat()}Z\n"
        f"# ------------------------------------\n\n"
    )

def ensure_vv_definition(content, index):
    """إذا لم يوجد vv أو VV_FILE داخل الملف، نضيف تعريف جديد."""
    if VV_PATTERN.search(content) or "VV_FILE" in content:
        return content
    return f'VV_FILE = "vv{index}.json"\n\n' + content

def create_copies(src_path, base_name, start, count, out_dir):
    orig = read_file(src_path)
    header = make_header(src_path)

    # تعديل الملف الأصلي (يبدأ من start)
    if VV_PATTERN.search(orig):
        mod_orig = VV_PATTERN.sub(f"vv{start}.json", orig)
    else:
        mod_orig = ensure_vv_definition(orig, start)
    write_file(src_path, header + mod_orig)

    print(f"✏️ تم تعديل الملف الأصلي: {src_path}")

    created = []
    for i in range(start, start + count):
        out_name = f"{base_name}{i}.py"
        out_path = os.path.join(out_dir, out_name)
        if VV_PATTERN.search(mod_orig):
            new_content = VV_PATTERN.sub(f"vv{i}.json", mod_orig)
        else:
            new_content = ensure_vv_definition(mod_orig, i)
        new_header = (
            f"# File generated from {os.path.basename(src_path)}\n"
            f"# generated_name: {out_name}\n"
            f"# generated_at: {datetime.utcnow().isoformat()}Z\n\n"
        )
        write_file(out_path, new_header + new_content)
        created.append(out_path)
    return created

def main():
    backup(SOURCE_FILE)
    created = create_copies(SOURCE_FILE, BASE_NAME, START_INDEX, COUNT, OUT_DIR)
    print("✅ تم إنشاء الملفات التالية:")
    for c in created:
        print(" -", c)

if __name__ == "__main__":
    main()
