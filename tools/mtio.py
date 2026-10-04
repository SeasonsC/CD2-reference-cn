# -*- coding: utf-8 -*-
"""
Mutators「类型栏」结构化：散文 → 新版 HTML
────────────────────────────────────────────────────────────
源数据是散文（`<b>类型</b> — 输入：…、… · 输出：…`），这里解析成
《CD2参考文档-类型栏重设计.md》规定的结构：

    <div class="mt-io">
      <span class="mt-io-label">类型</span>
      <span class="mt-io-item"><span class="mt-io-k">输入</span><code>Initial</code><i>数值</i>、…</span>
      <span class="mt-io-item"><span class="mt-io-k">输出</span><code>float</code></span>
    </div>
"""
import re, html as H

CJK = re.compile(r'[\u4e00-\u9fff]')
PREFIX = re.compile(r'^\s*<b>类型</b>\s*[—\-–]\s*')
TAIL_NOTE = re.compile(r'^(?P<name>.*)（(?P<note>[^（）]*)）$')   # 贪婪：取最后一个括号组
IDENT = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.: /+\-–—]*$')


def _esc(s):
    return H.escape(s or '', quote=True)


def _split_top(s, seps):
    """按 seps 切分，忽略括号内部的分隔符（如 `比较运算符（==、>=、<）`）。"""
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


def _item(name, note):
    """标识符 → <code>；`+` 两侧各自判定；含中文 → 普通文本；注记 → <i>。"""
    n = (name or '').strip()
    if not n:
        return ''
    segs = []
    for p in re.split(r'\s*\+\s*', n):
        p = p.strip()
        if not p:
            continue
        segs.append(f'<code>{_esc(p)}</code>' if IDENT.match(p) and not CJK.search(p)
                    else _esc(p))
    out = ' + '.join(segs)
    if note:
        out += f'<i>{_esc(note)}</i>'
    return out


def _split_note(tok):
    m = TAIL_NOTE.match(tok.strip())
    return (m.group('name').strip(), m.group('note').strip()) if m else (tok.strip(), None)


def parse(text):
    t = PREFIX.sub('', H.unescape(text or '')).strip()
    inp_raw, out_raw = '', t
    if '· 输出：' in t:
        inp_raw, out_raw = t.split('· 输出：', 1)
    inp_raw = re.sub(r'^输入：', '', inp_raw).strip()

    notes, items = [], []
    if inp_raw and inp_raw != '无':
        parts = _split_top(inp_raw, '；')          # `；` 之后是补充说明，不算输入项
        notes = [x for x in parts[1:] if x]
        items = [_split_note(x) for x in _split_top(parts[0], '、') if x]
    outs = [_split_note(x) for x in _split_top(out_raw, '、；') if x]
    return {'input': items, 'output': outs, 'notes': notes}


def to_html(text):
    """散文 → 新版结构 HTML。输入为空（`无`）时省略整段。"""
    d = parse(text)
    parts = ['<span class="mt-io-label">类型</span>']
    if d['input']:
        seg = '<span class="mt-io-k">输入</span>' + \
              '、'.join(_item(n, o) for n, o in d['input'])
        if d['notes']:
            seg += '；' + '；'.join(_esc(x) for x in d['notes'])
        parts.append(f'<span class="mt-io-item">{seg}</span>')
    if d['output']:
        seg = '<span class="mt-io-k">输出</span>' + \
              '、'.join(_item(n, o) for n, o in d['output'])
        parts.append(f'<span class="mt-io-item">{seg}</span>')
    return '<div class="mt-io">' + ''.join(parts) + '</div>'
