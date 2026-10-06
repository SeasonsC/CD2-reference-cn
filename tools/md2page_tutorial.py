# -*- coding: utf-8 -*-
"""《新手入门.md》→ CD2-upstream-src/tutorial/index.html

这是**正式工具**（不是临时脚本）：改 md 后运行它，再跑 tools/build.ps1。

只支持这一页用到的 Markdown 子集：
  标题 `#` / `##` / `###`（可用 `{#锚点}` 指定英文锚点）、段落、
  无序 `- ` / 有序 `1. ` 列表、`| 表格 |`、``` 代码块、
  行内 `code` / **粗体** / [文本](链接)

输出保持 MkDocs 页面骨架——extract.py 只认 div[role=main] 里的 div.section。
"""
import io, os, re, html as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, os.pardir, '新手入门.md')
OUT = os.path.join(ROOT, os.pardir, 'CD2-upstream-src', 'tutorial', 'index.html')

SHELL = ('<!DOCTYPE html>\n<html lang="zh-CN">\n<head><meta charset="utf-8">'
         '<title>{title}</title></head>\n<body>\n'
         '<div role="main" class="document" itemscope="itemscope" '
         'itemtype="http://schema.org/Article">'
         '<div class="section" itemprop="articleBody">\n{body}\n</div></div>\n'
         '</body>\n</html>\n')


def esc(t):
    return H.escape(t or '', quote=False)


def inline(t):
    """行内格式：先转义，再套 code / 粗体 / 链接。"""
    t = esc(t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
    return t


def convert(md):
    lines = md.split('\n')
    n, i, out = len(lines), 0, []
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        # 代码块
        if s.startswith('```'):
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1
            cls = f' class="language-{esc(lang)}"' if lang else ''
            out.append(f'<pre><code{cls}>{esc(chr(10).join(buf).strip(chr(10)))}</code></pre>')
            continue
        # 标题
        m = re.match(r'^(#{1,4})\s+(.*)$', s)
        if m:
            lvl, txt = len(m.group(1)), m.group(2).strip()
            m2 = re.search(r'\s*\{#([\w\-]+)\}\s*$', txt)
            aid = ''
            if m2:
                aid, txt = m2.group(1), txt[:m2.start()].strip()
            idattr = f' id="{esc(aid)}"' if aid else ''
            out.append(f'<h{lvl}{idattr}>{inline(txt)}</h{lvl}>')
            i += 1
            continue
        # 表格（分隔行 |---| 判定）
        if s.startswith('|') and i + 1 < n and re.match(r'^\|[\s:\-|]+\|$', lines[i + 1].strip()):
            head = [c.strip() for c in s.strip('|').split('|')]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            buf = ['<table><thead><tr>' +
                   ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr></thead><tbody>']
            for r in rows:
                buf.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
            buf.append('</tbody></table>')
            out.append(''.join(buf))
            continue
        # 有序列表
        if re.match(r'^\d+\.\s', s):
            items = []
            while i < n and re.match(r'^\d+\.\s', lines[i].strip()):
                items.append(inline(re.sub(r'^\d+\.\s+', '', lines[i].strip())))
                i += 1
            out.append('<ol>' + ''.join(f'<li>{x}</li>' for x in items) + '</ol>')
            continue
        # 无序列表
        if s.startswith('- '):
            items = []
            while i < n and lines[i].strip().startswith('- '):
                items.append(inline(lines[i].strip()[2:].strip()))
                i += 1
            out.append('<ul>' + ''.join(f'<li>{x}</li>' for x in items) + '</ul>')
            continue
        # 段落
        buf = []
        while i < n:
            t = lines[i].strip()
            if not t or t.startswith(('#', '|', '- ', '```')) or re.match(r'^\d+\.\s', t):
                break
            buf.append(t)
            i += 1
        out.append('<p>' + inline(' '.join(buf)) + '</p>')
    return '\n'.join(out)


def main():
    md = io.open(MD, encoding='utf-8').read()
    title = next((l[2:].strip() for l in md.split('\n') if l.startswith('# ')),
                 '新手入门')
    body = convert(md)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, 'w', encoding='utf-8', newline='').write(
        SHELL.format(title=esc(title), body=body))
    print('✔ %s' % OUT)
    print('   标题 %s｜h2 %d｜h3 %d｜表格 %d｜代码块 %d｜正文 %d 字符'
          % (title, body.count('<h2'), body.count('<h3'), body.count('<table'),
             body.count('<pre>'), len(body)))


if __name__ == '__main__':
    main()
