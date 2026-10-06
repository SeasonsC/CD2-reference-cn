# -*- coding: utf-8 -*-
"""把几个待核验的小节从构建产物里抽出来，做成独立预览页。
   表格列宽是百分比，容器宽度一致时渲染结果等价于真实页面。"""
import io, os, re

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_preview', 'r6.html')

WANT = [
    ('modules/index.html', 'salvage', '搜救行动 · Salvage（② 列宽调整）'),
    ('modules/index.html', 'warnings', '禁用任务词条 · Warnings（③ 翻译列移位）'),
    ('mutators/index.html', 'bybiome', '根据生物群系 · ByBiome（⑧ 翻译列移位）'),
]

def section(slug, sid):
    h = io.open(os.path.join(SITE, slug), encoding='utf-8').read()
    i = h.index(f'id="{sid}"')
    i = h.rindex('<h2', 0, i)
    m = re.search(r'<h2', h[i + 4:])
    j = i + 4 + m.start() if m else len(h)
    return h[i:j]

parts = []
for slug, sid, label in WANT:
    parts.append(f'<section><h3 class="lbl">{label}</h3>{section(slug, sid)}</section>')

html = f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>R6 局部预览</title>
<link rel="stylesheet" href="../docs/assets/css/site.css">
<style>
body{{ padding:1.5rem; }}
.lbl{{ color:var(--brand); font-size:.9em; margin:2.5rem 0 .5rem;
       padding-bottom:.4rem; border-bottom:1px dashed var(--border); }}
section{{ max-width:880px; margin:0 auto; }}   /* 最窄内容列，验证最坏情况 */
main, .content{{ max-width:none; padding:0; }}
</style>
</head>
<body>
<div class="content">
{''.join(parts)}
</div>
</body>
</html>'''
io.open(OUT, 'w', encoding='utf-8').write(html)
print('已生成', OUT, len(html), '字节')
for slug, sid, label in WANT:
    print('  ', label, '→', len(section(slug, sid)), '字节')
