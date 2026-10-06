# -*- coding: utf-8 -*-
"""重新生成 Mutator 字段表预览页 —— 直接从构建产物抽取真实小节，保证与站点一致。"""
import io, os, re
from lxml import html as LH

SITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_preview', 'mutator-fields.html')

WANT = [
    ('accumulate', '常规：4 个字段'),
    ('clamp', '字段较少'),
    ('defenseprogress', '无字段 → 无需配置字段'),
    ('bymissiontype', '开放字段（各任务类型键）'),
    ('EnemyHealth', '带默认值与枚举'),
    ('Sequence', '字段很多，且正文已有字段表'),
]

doc = LH.fromstring(io.open(os.path.join(SITE, 'mutators', 'index.html'), 'rb').read())
body = doc.xpath('//main')[0]

def section(sid):
    h = body.xpath(f'.//h2[@id="{sid}"]')
    if not h:
        return None
    h = h[0]
    node = h
    out = [h]
    for _ in range(60):
        node = node.getnext()
        if node is None or node.tag == 'h2':
            break
        out.append(node)
        # 只取到第一个代码块为止，避免整页太长
        if node.tag == 'pre':
            break
    return out

parts = []
for sid, label in WANT:
    nodes = section(sid)
    if not nodes:
        print('  未找到', sid)
        continue
    inner = ''.join(LH.tostring(n, encoding='unicode') for n in nodes)
    parts.append(f'<section class="dm"><div class="dm-lbl">{label}</div>{inner}</section>')

html = f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mutator 字段表 · 预览</title>
<link rel="stylesheet" href="../docs/assets/css/site.css">
<style>
body{{ padding:1.5rem 1.5rem 4rem; }}
.wrap{{ max-width:900px; margin:0 auto; }}
h1{{ font-size:1.5rem; }}
.intro{{ color:var(--muted); font-size:.9em; line-height:1.75; margin-bottom:2rem; }}
.intro code{{ font-size:.9em; }}
.dm{{ margin:0 0 3rem; padding:1rem 0 0; border-top:1px dashed var(--border); }}
.dm-lbl{{ display:inline-block; font-size:.72rem; letter-spacing:.06em;
  color:var(--brand); border:1px solid var(--brand); border-radius:4px;
  padding:.1rem .5rem; margin-bottom:.8rem; }}
.dm .orig{{ display:none; }}
.dm + .dm h2{{ margin-top:0; }}
</style>
</head>
<body>
<div class="wrap">
<h1>Mutator 字段表 · 预览</h1>
<p class="intro">
从构建产物里<b>直接抽取</b>的真实小节（不是另画的示意图），与站点渲染完全一致。<br>
结构：<code>一句话说明 → 字段表 → 返回 → 详细说明 → 示例</code>。<br>
字段的<b>类型/说明</b>逐字取自原文档的类型栏，未做推测；原文没写的显示 <code>—</code>。<br>
为便于浏览，这里隐藏了折叠的英文原文。
</p>
{''.join(parts)}
</div>
</body>
</html>'''
io.open(OUT, 'w', encoding='utf-8').write(html)
print('已生成', OUT, len(html), '字节；样本', len(parts), '个')
