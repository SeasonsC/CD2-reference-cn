# -*- coding: utf-8 -*-
"""
Mutators 页「类型栏」重设计 —— 散文 → 结构化解析器（预览用，尚未接线到站点）

源数据现状：86 条 `p.mt-io` 是散文，形如
    <b>类型</b> — 输入：Initial（数值）、Value（数值 / Mutator）、Min、Max（夹取范围） · 输出：float
目标结构（见《CD2参考文档-类型栏重设计.md》）：
    <div class="mt-io"><span class="mt-io-label">类型</span>
      <span class="mt-io-item"><span class="mt-io-k">输入</span><code>Initial</code><i>数值</i>、…</span>
      <span class="mt-io-item"><span class="mt-io-k">输出</span><code>float</code></span></div>
"""
import os, io, re, json, html as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, 'build', 'content')
OUT = os.path.join(ROOT, 'tools', 'mtio_preview.txt')

CJK = re.compile(r'[\u4e00-\u9fff]')
PREFIX = re.compile(r'^\s*<b>类型</b>\s*[—\-–]\s*')
# 尾部括号注记：贪婪匹配，取最后一个括号组当注记
TAIL_NOTE = re.compile(r'^(?P<name>.*)（(?P<note>[^（）]*)）$')
IDENT = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.: /+\-–—]*$')


def esc(s):
    return H.escape(s or '', quote=True)


def split_top(s, seps):
    """按 seps 切分，但忽略括号内部的同名分隔符。"""
    out, buf, depth = [], [], 0
    for ch in s:
        if ch in '（(':
            depth += 1
        elif ch in '）)':
            depth = max(0, depth - 1)
        if depth == 0 and ch in seps:
            out.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append(''.join(buf))
    return [x.strip() for x in out]


def render_item(name, note):
    """标识符用 <code>，含中文的走普通文本；`+` 连接的两侧各自判定；注记用 <i>。"""
    n = (name or '').strip()
    if not n:
        return ''
    segs = []
    for p in re.split(r'\s*\+\s*', n):
        p = p.strip()
        if not p:
            continue
        segs.append(f'<code>{esc(p)}</code>' if IDENT.match(p) and not CJK.search(p)
                    else esc(p))
    html = ' + '.join(segs)
    if note:
        html += f'<i>{esc(note)}</i>'
    return html


def split_note(tok):
    t = tok.strip()
    m = TAIL_NOTE.match(t)
    if m:
        return m.group('name').strip(), m.group('note').strip()
    return t, None


def parse(text):
    """返回 {'input': [items], 'output': [items], 'notes': [散文], 'has_input': bool}"""
    t = PREFIX.sub('', H.unescape(text or '')).strip()
    inp_raw, out_raw = '', t
    if '· 输出：' in t:
        inp_raw, out_raw = t.split('· 输出：', 1)
    inp_raw = re.sub(r'^输入：', '', inp_raw).strip()

    notes, items = [], []
    if inp_raw and inp_raw != '无':
        parts = split_top(inp_raw, '；')      # `；` 之后是补充说明，不算输入项
        head, rest = parts[0], parts[1:]
        notes += [x for x in rest if x]
        items = [split_note(x) for x in split_top(head, '、') if x]

    outs = [split_note(x) for x in split_top(out_raw, '、；') if x]
    return {'input': items, 'output': outs, 'notes': notes, 'has_input': bool(items)}


def to_html(d):
    parts = ['<span class="mt-io-label">类型</span>']
    if d['has_input']:
        seg = '<span class="mt-io-k">输入</span>' + \
              '、'.join(render_item(n, o) for n, o in d['input'])
        if d['notes']:
            seg += '；' + '；'.join(esc(x) for x in d['notes'])
        parts.append(f'<span class="mt-io-item">{seg}</span>')
    if d['output']:
        seg = '<span class="mt-io-k">输出</span>' + \
              '、'.join(render_item(n, o) for n, o in d['output'])
        parts.append(f'<span class="mt-io-item">{seg}</span>')
    return '<div class="mt-io">' + ''.join(parts) + '</div>'


def main():
    page = json.load(io.open(os.path.join(CONTENT, 'mutators.json'), encoding='utf-8'))
    rows = [b['zh'] for b in page['blocks'] if b['t'] == 'p' and b.get('cls') == 'mt-io']
    L = [f'mt-io 结构化预览（共 {len(rows)} 条）', '=' * 100]
    messy = []
    for i, r in enumerate(rows, 1):
        d = parse(r)
        new = to_html(d)
        plain = re.sub(r'<[^>]+>', '', new)
        # 标记可能需要人工过目的：输入项里落了中文、或没有识别出任何 code
        flag = ''
        if not re.search(r'<code>', new):
            flag = '  ← 无标识符'
        elif any(CJK.search(n or '') for n, _ in d['input']):
            flag = '  ← 输入项含中文'
        if flag:
            messy.append(i)
        L.append(f'{i:3d}. 原文: {r}')
        L.append(f'     新版: {new}{flag}')
        L.append(f'     纯文本: {plain}')
        L.append('')
    L.append('=' * 100)
    L.append(f'需要人工过目 {len(messy)} 条：{messy}')
    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(L))
    print(f'共 {len(rows)} 条，需人工过目 {len(messy)} 条 -> {messy}')
    print('report ->', OUT)


main()
