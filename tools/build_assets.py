# -*- coding: utf-8 -*-
"""
CD2 参考文档 v2 · 资源构建
────────────────────────────────────────────────────────────
把 src/ 下的**带注释手写源码**去注释、压空行后输出到 docs/assets/。
源码留在 src/（可读），发布产物在 docs/（精简）——降低首屏体积与预算压力。
"""
import os, io, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
SITE = os.path.join(ROOT, 'docs')

IMGDIR = os.path.join(SRC, 'img')
FILEDIR = os.path.join(SRC, 'files')

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


# ── R17 §S8：构建期**保守**空白压缩 ────────────────────────────────────
# 只动空白，不合并/重写任何 token；不引入 terser/esbuild（文档站可读性优先，
# 且 README 写明运行期零依赖、构建期也只依赖 Pillow）。
def _protect_strings(s):
    """把引号串取出占位。content:"▸ " 这类**引号内的尾随空格不能动**。"""
    store = []

    def rep(m):
        store.append(m.group(0))
        return '\x00%d\x00' % (len(store) - 1)

    out = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\'', rep, s)
    return out, store


def _restore_strings(s, store):
    return re.sub(r'\x00(\d+)\x00', lambda m: store[int(m.group(1))], s)


def squeeze_css(s):
    s, store = _protect_strings(s)
    s = re.sub(r'[ \t]*\n[ \t]*', '\n', s)      # 行首/行尾空白
    s = re.sub(r'[ \t]+', ' ', s)               # 行内连续空格
    s = re.sub(r'\s*([{};,])\s*', r'\1', s)     # 结构符号周围空白（含换行）
    s = re.sub(r';}', '}', s)                   # 块内最后一条的分号
    s = re.sub(r'\n{2,}', '\n', s)
    return _restore_strings(s, store).strip() + '\n'


def squeeze_js(s):
    """JS 只删缩进与空行，**保留换行** —— ASI 语义不受影响。"""
    s = re.sub(r'[ \t]*\n[ \t]*', '\n', s)
    s = re.sub(r'\n{2,}', '\n', s)
    return s.strip() + '\n'


def _selectors(s):
    """规则前的选择器序列（归一化空白），用于自检压缩没有粘连/拆开选择器。"""
    s, store = _protect_strings(s)
    return [re.sub(r'\s+', '', m.group(1)) for m in re.finditer(r'([^{}]*)\{', s)]


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
        # R17 §S8：再压一遍空白（CSS 额外自检选择器序列未被改写）
        if kind == 'css':
            squeezed = squeeze_css(out)
            if _selectors(out) != _selectors(squeezed):
                print('!! CSS 压缩会改动选择器序列，已放弃压缩（保留未压缩产物）')
            else:
                out = squeezed
        else:
            out = squeeze_js(out)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        # 统一按 LF 落盘：默认的 open(...,'w') 在 Windows 上会把 '\n' 再翻一次，
        # 与内容里已有的 CRLF 叠成 '\r\r\n'（落单 CR），会让 git 判定成二进制。
        io.open(dp, 'w', encoding='utf-8', newline='').write(
            out.replace('\r\n', '\n').replace('\r', '\n'))
        b0, b1 = len(raw.encode('utf-8')), len(out.encode('utf-8'))
        rows.append((name, f'{b0:,}', f'{b1:,}', f'-{100 - b1 * 100 // b0}%'))
    # 图标等静态图片：原样拷贝（src/img → docs/assets/img）
    dst = os.path.join(SITE, 'assets', 'img')
    if os.path.isdir(IMGDIR):
        os.makedirs(dst, exist_ok=True)
        for f in sorted(os.listdir(IMGDIR)):
            if f.lower().endswith(('.svg', '.png', '.ico', '.webp')):
                data = io.open(os.path.join(IMGDIR, f), 'rb').read()
                io.open(os.path.join(dst, f), 'wb').write(data)
                rows.append((f, f'{len(data):,}', f'{len(data):,}', 'copy'))
    # 可下载文件（难度 JSON 等）
    if os.path.isdir(FILEDIR):
        dd = os.path.join(SITE, 'assets', 'files')
        os.makedirs(dd, exist_ok=True)
        for f in sorted(os.listdir(FILEDIR)):
            data = io.open(os.path.join(FILEDIR, f), 'rb').read()
            io.open(os.path.join(dd, f), 'wb').write(data)
            rows.append((f, f'{len(data):,}', f'{len(data):,}', 'copy'))
    for r in rows:
        print('%-10s %9s → %9s  %s' % r)


main()
