# -*- coding: utf-8 -*-
"""
CD2 参考文档 v2 · 资源构建
────────────────────────────────────────────────────────────
把 src/ 下的**带注释手写源码**去注释、压空行后输出到 docs/assets/。
源码留在 src/（可读），发布产物在 docs/（精简）——降低首屏体积与预算压力。
"""
import os, io, re

ROOT = r'E:\learn\github\dsh\CD2\CD2-reference-cn-v2'
SRC = os.path.join(ROOT, 'src')
SITE = os.path.join(ROOT, 'docs')

ITEMS = [
    ('site.css', 'assets/css/site.css', 'css'),
    ('site.js', 'assets/js/site.js', 'js'),
]


def strip_css(s):
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)       # 块注释
    s = re.sub(r'[ \t]+$', '', s, flags=re.M)         # 行尾空白
    s = re.sub(r'\n{2,}', '\n', s)                    # 连续空行
    return s.lstrip('\n').rstrip() + '\n'


def strip_js(s):
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)       # 块注释
    # 行尾 // 注释：仅当 // 前面是空白时才删（避开正则里的 \/ 与 URL 中的 //）
    s = re.sub(r'(?<=\s)//[^\n]*', '', s)
    s = re.sub(r'^//[^\n]*', '', s, flags=re.M)       # 整行注释
    s = re.sub(r'[ \t]+$', '', s, flags=re.M)
    s = re.sub(r'\n{2,}', '\n', s)
    return s.lstrip('\n').rstrip() + '\n'


def main():
    rows = []
    for name, rel, kind in ITEMS:
        sp = os.path.join(SRC, name)
        dp = os.path.join(SITE, rel.replace('/', os.sep))
        if not os.path.exists(sp):
            rows.append((name, 'MISSING', '', ''))
            continue
        raw = io.open(sp, encoding='utf-8').read()
        out = strip_css(raw) if kind == 'css' else strip_js(raw)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        io.open(dp, 'w', encoding='utf-8').write(out)
        b0, b1 = len(raw.encode('utf-8')), len(out.encode('utf-8'))
        rows.append((name, f'{b0:,}', f'{b1:,}', f'-{100 - b1 * 100 // b0}%'))
    for r in rows:
        print('%-10s %9s → %9s  %s' % r)


main()
