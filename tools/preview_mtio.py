# -*- coding: utf-8 -*-
"""生成「类型栏」新旧对比预览页（不接线到站点）。"""
import os, io, json, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_mtio as P

ROOT = r'E:\learn\github\dsh\CD2\CD2-reference-cn-v2'
OUT = os.path.join(ROOT, '_preview', 'mtio.html')

NEW_CSS = """
/* 新设计（待接线到 src/site.css） */
.mt-io{
  display:flex; flex-wrap:wrap; align-items:baseline; gap:.3rem 1.6rem;
  margin:0 0 1.2em; padding:.5rem .9rem;
  background:var(--surface);
  border:0; border-left:3px solid var(--brand); border-radius:0 4px 4px 0;
  font-size:.85rem; line-height:1.6; color:var(--text);
  font-family:var(--font);
}
.mt-io-label{ font-size:.72rem; font-weight:600; letter-spacing:.08em; color:var(--brand); }
.mt-io-k{ color:var(--muted); margin-right:.45em; }
.mt-io code{
  font-family:var(--mono); font-size:.92em;
  background:none; border:0; padding:0; color:var(--code-fg);
}
.mt-io i{ font-style:normal; color:var(--muted); font-size:.9em; margin-left:.3em; }
/* 旧设计（现状，用于对比） */
p.mt-io.old{
  display:block; background:var(--panel); border:1px solid var(--border-soft);
  border-left:3px solid var(--brand); border-radius:0 6px 6px 0;
  padding:.5rem .8rem; font-size:.86rem; color:var(--muted); font-family:var(--font);
}
p.mt-io.old b{ color:var(--brand); font-weight:650; margin-right:.15em; }
"""

SAMPLES = [1, 4, 20, 18, 54, 2, 3]


def main():
    page = json.load(io.open(os.path.join(P.CONTENT, 'mutators.json'), encoding='utf-8'))
    rows = [b['zh'] for b in page['blocks'] if b['t'] == 'p' and b.get('cls') == 'mt-io']
    # 找到每条所属的 h2 标题，便于对照
    titles, cur = {}, ''
    idx = 0
    for b in page['blocks']:
        if b['t'] == 'h':
            cur = b['text']
        elif b['t'] == 'p' and b.get('cls') == 'mt-io':
            idx += 1
            titles[idx] = cur

    blocks = []
    for n in SAMPLES:
        old = rows[n - 1]
        new = P.to_html(P.parse(old))
        blocks.append(f'''<div class="demo">
  <h3>{n}. {titles.get(n, '')}</h3>
  <div class="lbl">旧</div>
  <p class="mt-io old">{old}</p>
  <div class="lbl">新</div>
  {new}
</div>''')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>类型栏重设计 · 新旧对比</title>
<link rel="stylesheet" href="../docs/assets/css/site.css">
<style>
{NEW_CSS}
body{{ padding:2rem 1.5rem 4rem; }}
.wrap{{ max-width:900px; margin:0 auto; }}
h1{{ font-size:1.6rem; }}
.demo{{ margin:0 0 2.5rem; padding-bottom:1.5rem; border-bottom:1px dashed var(--border); }}
.demo h3{{ font-size:1rem; color:var(--strong); margin:0 0 .8rem; }}
.lbl{{ font-size:.72rem; letter-spacing:.08em; color:var(--muted); margin:.9rem 0 .3rem; }}
.note{{ background:var(--panel); border-left:3px solid var(--link); border-radius:0 6px 6px 0;
  padding:.7rem .9rem; font-size:.86rem; color:var(--muted); }}
</style>
</head>
<body>
<div class="wrap">
<h1>类型栏重设计 · 新旧对比</h1>
<p class="note">下面是 <b>真实数据</b> 经解析器转换后的结果（共 86 条，这里抽 7 条）。
新设计的「类型」标签退成小号、标识符走等宽蓝色、注记走灰色小字，容器去掉全边框。</p>
{''.join(blocks)}
</div>
</body>
</html>'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8').write(html)
    print('written', OUT, len(html), 'bytes')


main()
