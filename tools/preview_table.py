# -*- coding: utf-8 -*-
"""生成「三线表」预览页（不接线到站点）：真实表格 · 现状 vs 三线表对照。"""
import os, io, re, json
from lxml import html as LH

ROOT = r'E:\learn\github\dsh\CD2\CD2-reference-cn-v2'
CONTENT = os.path.join(ROOT, 'build', 'content')
OUT = os.path.join(ROOT, '_preview', 'threeline.html')

# 要展示的真实表格：(页面, 用哪段文本定位)
SAMPLES = [
    ('enemies', 'OnSpawnDelay',        '生成器 · Spawner 表（3 列，你截图那张）'),
    ('modules', 'FlashlightStrength',  '光照控制 · Darkness 表（4 列，带 Comment 长文本）'),
    ('modules', 'MinPoolSize',         '怪池 · Pools 表（2 列，之前被拉得很空）'),
]

TL_CSS = """
/* 三线表（预览用，待接线） */
.tl{
  border-collapse:collapse; width:100%; font-size:.95rem;
  border:0; border-top:1.5px solid var(--strong); border-bottom:1.5px solid var(--strong);
}
.tl thead th{
  border:0; border-bottom:1px solid var(--strong); background:transparent;
  padding:.6rem 1.15rem; text-align:left; color:var(--strong); font-weight:600;
}
.tl td{ border:0; padding:.55rem 1.15rem; vertical-align:top; }
.tl tbody tr{ background:transparent; }
.tl tbody tr:hover{ background:var(--brand-soft); }
.tl .td-zh{ display:block; margin-top:.1em; }
/* 现状对照：用站点现有样式原样渲染 */
.now table{ width:max-content; max-width:100%; }
"""


def find_table(slug, key):
    page = json.load(io.open(os.path.join(CONTENT, slug + '.json'), encoding='utf-8'))
    for b in page['blocks']:
        if b['t'] == 'table' and key in b['html']:
            return b['html']
    return None


def main():
    blocks = []
    for slug, key, label in SAMPLES:
        raw = find_table(slug, key)
        if not raw:
            continue
        # 现状版：套站点的 .table-wrap + table
        now = f'<div class="table-wrap">{raw}</div>'
        # 三线表版：同一份表格内容，套 .tl
        tl = re.sub(r'^<table[^>]*>', '<table class="tl">', raw, count=1)
        blocks.append(f'''<section class="demo">
  <h2>{label}</h2>
  <div class="lbl">现状</div>
  <div class="now">{now}</div>
  <div class="lbl">三线表</div>
  <div class="tlwrap">{tl}</div>
</section>''')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>三线表预览</title>
<link rel="stylesheet" href="../docs/assets/css/site.css">
<style>
{TL_CSS}
body{{ padding:2rem 1.5rem 4rem; font-family:var(--font); }}
.wrap{{ max-width:900px; margin:0 auto; }}
h1{{ font-size:1.6rem; }}
.demo{{ margin:0 0 3rem; padding-bottom:1.5rem; border-bottom:1px dashed var(--border); }}
.demo h2{{ font-size:1rem; color:var(--brand); margin:0 0 1rem; border:0; padding:0; }}
.lbl{{ font-size:.72rem; letter-spacing:.08em; color:var(--muted); margin:1.2rem 0 .5rem; }}
.note{{ background:var(--panel); border-left:3px solid var(--link); border-radius:0 6px 6px 0;
  padding:.7rem .9rem; font-size:.86rem; color:var(--muted); }}
</style>
</head>
<body>
<div class="wrap">
<h1>三线表预览</h1>
<p class="note">三线表 = <b>去掉所有竖线与行间横线</b>，只留三条：顶线、表头下线、底线。
表格改为占满内容列宽（两条侧边栏之间），表头单元格左右内边距加大到 1.15rem。
<b>斑马纹也去掉了</b>——三线表传统上不带底色，如果你要保留斑马纹告诉我。</p>
{''.join(blocks)}
</div>
</body>
</html>'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print('written', OUT, len(html), 'bytes')


main()
